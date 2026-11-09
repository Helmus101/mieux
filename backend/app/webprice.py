"""Approximate shelf price from a Google-grounded Gemini lookup, for products that have no observed price.

Never an observed price: callers must label it ("~", source "web_search") and keep it out of the cheapest / best-value winners. Off unless
GEMINI_API_KEY is set. Results (and misses) are cached per barcode so a product is looked up once, not on every scan."""
import json
import os
import re
import sqlite3
import unicodedata
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional, Tuple

from . import value

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
HIT_TTL = 30 * 86400      # a found price is searched again after 30 days (the old one stays, marked stale, if the new search finds nothing)
MISS_TTL = 1 * 86400      # a search that found nothing is retried after a day (search results vary, so one miss must not stick for long)
CACHE_PATH = os.environ.get("WEBPRICE_CACHE", os.path.join(os.path.dirname(os.environ.get("OP_LOCAL", "/tmp/x")) or ".", "webprice_cache.db"))

PROMPT = (
    "Trouve le prix actuel en euros de ce produit alimentaire dans un supermarché en France (drive ou magasin), "
    "à partir de pages de supermarchés ou de comparateurs. Produit : {name}{brand}. Code-barres : {ean}. Format : {size}.\n"
    "Réponds UNIQUEMENT par un objet JSON : {{\"price_eur\": nombre, \"pack_size\": \"ex. 500 g\", \"store\": \"enseigne\", \"found\": true}}. "
    "Si tu n'es pas sûr que le prix concerne exactement ce produit et ce format, réponds {{\"found\": false}}. N'invente rien."
)

last_error: Optional[str] = None


def _set_error(e: Exception) -> None:
    global last_error
    last_error = (str(getattr(e, "code", "")) + " " + type(e).__name__)[:80]


Transport = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def _post(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


BRAVE = "https://api.search.brave.com/res/v1/web/search"
_PRICE = re.compile(r"(\d{1,3}(?:[ .]\d{3})*[,.]\d{2}|\d{1,3})\s?(?:€|eur\b|euros?\b)", re.I)


Http = Callable[[str, str, Dict[str, str], Optional[Dict[str, Any]]], Dict[str, Any]]


def _http(method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    for attempt in range(3):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
        time.sleep(1.5 * (attempt + 1))
    return {}


BRAVE = "https://api.search.brave.com/res/v1/web/search"
LANGSEARCH = "https://api.langsearch.com/v1/web-search"
PARALLEL = "https://api.parallel.ai/v1/search"
_PRICE = re.compile(r"(\d{1,3}(?:[ .]\d{3})*[,.]\d{2})\s?(?:€|eur\b|euros?\b)", re.I)


def providers() -> list:
    """Gemini (Google-grounded search) first, then Parallel, then LangSearch; each only when its key is set."""
    return [n for n, k in (("gemini", "GEMINI_API_KEY"), ("parallel", "PARALLEL_API_KEY"), ("langsearch", "LANGSEARCH_API_KEY")) if os.environ.get(k)]


def provider() -> Optional[str]:
    ps = providers()
    return ps[0] if ps else None


def enabled() -> bool:
    return provider() is not None


def _size_regex(q: Optional[Dict[str, Any]]) -> Optional[re.Pattern]:
    """The pack size as it is usually printed ('400 g', '1,5 l', '0,75 l'), so a snippet is only used when it talks about this size."""
    if not q:
        return None
    amt, unit = q["amount"], q["unit"]
    forms = {f"{amt:g}"}
    if unit == "g" and amt >= 1000:
        forms.add(f"{amt / 1000:g}")
    if unit == "ml" and amt >= 100:
        forms.add(f"{amt / 10:g}")
        forms.add(f"{amt / 1000:g}")
    units = r"(?:g|gr|grammes?|kg)" if unit == "g" and amt >= 1000 else {"g": r"(?:g|gr|grammes?)", "ml": r"(?:ml|cl|l|litres?)"}[unit]
    nums = "|".join(re.escape(f).replace(r"\.", "[,.]") for f in forms)
    return re.compile(rf"(?<![\d,.])(?:{nums})\s?{units}\b", re.I)


def _query(product: Dict[str, Any], variant: int = 0) -> str:
    q = product.get("quantity") or {}
    tail = ("prix", "prix en ligne supermarché drive")[variant]
    return f"{product.get('brand') or ''} {product.get('name') or ''} {q.get('amount', 0):g} {q.get('unit', '')} {tail}".strip()


def _fetch_results(name: str, product: Dict[str, Any], http: Http, variant: int = 0) -> list:
    """[(url, text)] from one search provider."""
    query = _query(product, variant)
    if name == "brave":
        data = http("GET", BRAVE + "?" + urllib.parse.urlencode({"q": query, "country": "fr", "search_lang": "fr", "count": 10}),
                    {"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"}, None)
        return [(r.get("url") or "", " ".join([r.get("title") or "", r.get("description") or ""] + list(r.get("extra_snippets") or [])))
                for r in (data.get("web") or {}).get("results", [])]
    if name == "langsearch":
        data = http("POST", LANGSEARCH, {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["LANGSEARCH_API_KEY"]},
                    {"query": f"{query} supermarché France", "freshness": "oneMonth", "summary": True, "count": 10})
        pages = ((data.get("data") or data).get("webPages") or {}).get("value", [])
        return [(r.get("url") or "", " ".join([r.get("name") or "", r.get("snippet") or "", r.get("summary") or ""])) for r in pages]
    data = http("POST", PARALLEL, {"Content-Type": "application/json", "x-api-key": os.environ["PARALLEL_API_KEY"]},
                {"objective": f"Prix actuel en euros en supermarché en France de : {query}. Donne les pages de supermarchés ou comparateurs qui indiquent ce prix.", "search_queries": [query]})
    return [(r.get("url") or "", " ".join([r.get("title") or ""] + list(r.get("excerpts") or []))) for r in data.get("results", [])]


_PER_UNIT_AFTER = re.compile(r"^\s*(?:/|par\b|le\b|au\b|\bl[e']?\s)\s*(?:kg|kilo|litre|l\b)", re.I)


def _words(text: str) -> set:
    """Lower-case words of 3+ letters, accents removed ('séchée' = 'sechee') so a typo in the accents never breaks a match."""
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return set(re.findall(r"[a-z0-9]{3,}", "".join(c for c in t if not unicodedata.combining(c))))


def _pack_price(text: str, size_units: float) -> Optional[float]:
    """The pack price in a text: ignores prices labelled per kilo / per litre, and a price that is just another price scaled to a kilo."""
    cands = []
    for m in _PRICE.finditer(text):
        v = float(m.group(1).replace(" ", "").replace(",", "."))
        if not (0.2 <= v <= 400) or _PER_UNIT_AFTER.match(text[m.end():m.end() + 14]):
            continue
        cands.append(v)
    if size_units > 0:
        per_unit = {b for a_ in cands for b in cands if a_ != b and abs(a_ / size_units - b) / b < 0.06}
        cands = [v for v in cands if v not in per_unit]
    cands = [v for v in cands if v <= 200]
    return cands[0] if cands else None


def _price_from(product: Dict[str, Any], results: list) -> Optional[Dict[str, Any]]:
    """A price only when two different sites talk about this product (brand and name words) and this pack size, and agree within 25 %."""
    q = product.get("quantity")
    size_re = _size_regex(q)
    if not q or not size_re:
        return None
    brand_w = _words(str(product.get("brand") or "").split(",")[0])
    name_w = {w for w in _words(product.get("name")) if len(w) > 3} - brand_w
    size_units = q["amount"] / 1000.0
    by_host: Dict[str, Tuple[float, str]] = {}
    for url, text in results:
        if not size_re.search(text):
            continue
        tw = _words(text)
        if (brand_w and not (brand_w & tw)) or (name_w and not (name_w & tw)):
            continue
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        v = _pack_price(text, size_units)
        if v:
            by_host.setdefault(host, (v, url))
    if len(by_host) == 1:
        # One site states this exact size and price. A second site that names the same product (every word of the name and the brand) but does not print the size
        # confirms it when one of its prices equals that price (within 3 %).
        (h0, (v0, u0)), = by_host.items()
        for url, text in results:
            host = urllib.parse.urlparse(url).netloc.replace("www.", "")
            if host == h0 or host in by_host:
                continue
            tw = _words(text)
            if (brand_w and not (brand_w & tw)) or not name_w or not name_w <= tw:
                continue
            if any(abs(float(m.group(1).replace(" ", "").replace(",", ".")) - v0) / v0 <= 0.03 for m in _PRICE.finditer(text)):
                by_host[host] = (v0, url)
                break
    from . import chains as ch0
    if len(by_host) == 1:
        # Still a single source: accepted when it is a supermarket's own page (a chain's site that states this exact size and a price), not a random page.
        (h1, (v1, u1)), = by_host.items()
        if ch0.canon(h1.replace(".", " ")):
            by_host[h1 + "#"] = (v1, u1)        # counts as its own confirmation
    vals = sorted(v for v, _ in by_host.values())
    if len(vals) < 2:
        return None
    med = vals[len(vals) // 2]
    agree = [(h, v, u) for h, (v, u) in by_host.items() if abs(v - med) / med <= 0.25]
    if len(agree) < 2:
        return None
    price_c = round(med * 100)
    from . import chains as ch, retail
    stores = []
    for h, _, _ in agree:
        name = ch.canon(h.rstrip("#").replace(".", " "))          # courses.monoprix.fr -> Monoprix
        if name and name not in stores:
            stores.append(name)
    return {"per100_cents": round(price_c / q["amount"] * 100, 1), "pack_cents": price_c, "store": stores[0] if stores else None, "stores": stores,
            "chains": [retail.ID_OF[n] for n in stores if n in retail.ID_OF], "source_urls": [u for _, _, u in agree][:3],
            "date": time.strftime("%Y-%m-%d"), "source": "web_search", "approximate": True}


_gemini: Dict[str, Any] = {"down_until": 0.0, "error": None}
DAILY_CAP = int(os.environ.get("WEBPRICE_DAILY_CAP", "1500"))     # searches per day (cost guard); stored prices are always served
_day = {"d": "", "n": 0}


def _budget_left() -> bool:
    today = time.strftime("%Y-%m-%d")
    if _day["d"] != today:
        _day.update(d=today, n=0)
    if _day["n"] >= DAILY_CAP:
        return False
    _day["n"] += 1
    return True


def _gemini_lookup(product: Dict[str, Any], transport: Transport) -> Optional[Dict[str, Any]]:
    """One Google-grounded Gemini lookup: a price only when it cites at least one page, for a known size in the same unit. Failures set last_error and return None."""
    global last_error
    key = os.environ["GEMINI_API_KEY"]
    barcode = str(product.get("barcode") or "")
    q = product.get("quantity")
    size = f"{q['amount']:g} {q['unit']}" if q else (product.get("quantityText") or "inconnu")
    body = {"contents": [{"parts": [{"text": PROMPT.format(name=product.get("name") or "", brand=f" ({product['brand']})" if product.get("brand") else "", ean=barcode, size=size)}]}],
            "tools": [{"google_search": {}}], "generationConfig": {"temperature": 0}}
    try:
        resp = transport(ENDPOINT.format(model=MODEL) + "?key=" + key, body)
    except Exception as e:       # network, quota, bad key, retired model: no price, and do not cache the failure
        last_error = (str(getattr(e, "code", "")) + " " + type(e).__name__)[:80]
        return None
    cand = (resp.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
    got = _parse(text)
    out = None
    if got:
        price_c = round(float(got["price_eur"]) * 100)
        qty = value.parse_quantity(str(got.get("pack_size") or "")) or ((q["amount"], q["unit"]) if q else None)
        sources = [c["web"]["uri"] for c in (cand.get("groundingMetadata") or {}).get("groundingChunks", []) if c.get("web", {}).get("uri")][:3]
        # Accept only a plausible price for a known size, backed by at least one cited page, in the same unit family as the product
        if qty and 20 <= price_c <= 20000 and sources and (not q or qty[1] == q["unit"]):
            out = {"per100_cents": round(price_c / qty[0] * 100, 1), "pack_cents": price_c, "store": got.get("store"), "source_urls": sources,
                   "date": time.strftime("%Y-%m-%d"), "source": "web_search", "approximate": True}
    return out


def _search_lookup(product: Dict[str, Any], http: Http, transport: Transport = _post) -> Optional[Dict[str, Any]]:
    """Parallel search; no price when the sites it returns do not agree on this pack size."""
    global last_error
    last_error = None
    if not _budget_left():
        last_error = "daily cap reached"
        return None
    for variant in (0, 1):                  # the second wording is only tried when the first finds nothing (search results vary from one call to the next)
        for name in providers():
            if variant and not _budget_left():
                return None
            if name == "gemini":
                if variant:
                    continue                # Gemini is asked once; the second wording goes to the other providers
                if time.time() < _gemini["down_until"]:
                    continue                # Gemini just failed (quota, bad model): skip it for a few minutes instead of paying a failing call each time
                out = _gemini_lookup(product, transport)
                if out:
                    out["provider"] = name
                    return out
                if last_error:              # a Gemini failure must not stop a genuine "nothing found" from being cached for the other providers
                    _gemini.update(down_until=time.time() + 600, error=last_error)
                    last_error = None
                continue
            try:
                out = _price_from(product, _fetch_results(name, product, http, variant))
            except Exception as e:
                _set_error(e)
                continue
            if out:
                out["provider"] = name
                return out
        if not product.get("brand"):
            break                           # an unbranded product is rarely found by a second try: do not pay for it
    return None


_conn: Dict[str, Any] = {"path": None, "db": None}
_lock = threading.Lock()


def _db() -> sqlite3.Connection:
    """One shared connection (opened once, not per call), used under a lock."""
    if _conn["db"] is None or _conn["path"] != CACHE_PATH:
        if _conn["db"] is not None:
            try:
                _conn["db"].close()
            except sqlite3.Error:
                pass
        db = sqlite3.connect(CACHE_PATH, check_same_thread=False, timeout=10)
        db.execute("pragma journal_mode=wal")
        db.execute("create table if not exists webprice (barcode text primary key, at real, data text)")
        _conn.update(path=CACHE_PATH, db=db)
    return _conn["db"]


def _cached(barcode: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    try:
        with _lock:
            row = _db().execute("select at, data from webprice where barcode=?", (barcode,)).fetchone()
    except sqlite3.Error:
        return False, None
    if not row:
        return False, None
    data = json.loads(row[1]) if row[1] else None
    ttl = HIT_TTL if data else MISS_TTL
    return (time.time() - row[0] < ttl), data


def _store(barcode: str, data: Optional[Dict[str, Any]]) -> None:
    try:
      with _lock:
        db = _db()
        if not data and db.execute("select data from webprice where barcode=? and data is not null", (barcode,)).fetchone():
            return                       # never overwrite a stored price with a miss
        db.execute("insert or replace into webprice values (?,?,?)", (barcode, time.time(), json.dumps(data) if data else None))
        db.commit()
    except sqlite3.Error:
        pass


def _parse(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    return d if d.get("found") is not False and isinstance(d.get("price_eur"), (int, float)) else None


def cached_only(product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The stored web price (fresh or older, marked stale) with no network call, so a request never waits on a search."""
    fresh, data = _cached(str(product.get("barcode") or ""))
    return data if (data and fresh) else ({**data, "stale": True} if data else None)


def lookup(product: Dict[str, Any], transport: Transport = _post, use_cache: bool = True, http: Optional[Http] = None) -> Optional[Dict[str, Any]]:
    """{per100_cents, pack_cents, store, source_urls, date, source:'web_search', approximate:True} or None."""
    global last_error
    key = os.environ.get("GEMINI_API_KEY")
    barcode = str(product.get("barcode") or "")
    if not barcode or provider() is None:
        return None
    old = None
    if use_cache:
        fresh, data = _cached(barcode)
        if fresh:
            return data
        old = data                       # an expired price we found earlier: kept, never thrown away
    if provider():
        out = _search_lookup(product, http or _http, transport)
        if use_cache and out:
            _store(barcode, out)
        elif use_cache and last_error is None and not old:
            _store(barcode, None)        # a genuine "nothing found" is remembered for a few days
        if not out and old:
            return {**old, "stale": True}   # the re-search found nothing: keep showing the stored price, marked as older
        return out
    return None
