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
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import value

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODELS = ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
HIT_TTL = 30 * 86400      # a found price is searched again after 30 days (the old one stays, marked stale, if the new search finds nothing)
MISS_TTL = 1 * 86400      # a search that found nothing is retried after a day (search results vary, so one miss must not stick for long)
_DEFAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.environ.get("WEBPRICE_CACHE") or (
    os.path.join(os.path.dirname(os.environ["OP_LOCAL"]), "webprice_cache.db")
    if os.environ.get("OP_LOCAL") and os.path.isdir(os.path.dirname(os.environ["OP_LOCAL"]))
    else os.path.join(_DEFAULT_DIR, "webprice_cache.db")
)

PROMPT = (
    "Trouve le prix actuel en euros de ce produit alimentaire en France (en supermarché, drive, magasin bio, ou boutique en ligne française). "
    "Produit : {name}{brand}. Code-barres : {ean}. Format : {size}.\n"
    "Réponds UNIQUEMENT par un objet JSON : {{\"price_eur\": nombre, \"pack_size\": \"ex. 500 g\", \"store\": \"nom du magasin ou site\", \"found\": true}}. "
    "Si tu trouves le prix de ce produit pour ce format (ou format approchant), donne-le. Si vraiment aucun prix n'existe nulle part, réponds {{\"found\": false}}."
)

last_error: Optional[str] = None


def _set_error(e: Exception) -> None:
    global last_error
    last_error = (str(getattr(e, "code", "")) + " " + type(e).__name__)[:80]


Transport = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def _post(url: str, body: Dict[str, Any], timeout: float = 25) -> Dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


BRAVE = "https://api.search.brave.com/res/v1/web/search"
LANGSEARCH = "https://api.langsearch.com/v1/web-search"
PARALLEL = "https://api.parallel.ai/v1/search"
_PRICE = re.compile(
    r"(?:(?:€|eur\b|euros?)\s*(\d{1,3}(?:[ .]\d{3})*(?:[,.]\d{1,2})?)|(\d{1,3}(?:[ .]\d{3})*(?:[,.]\d{1,2})?)\s*(?:€|eur\b|euros?\b))",
    re.I
)


Http = Callable[[str, str, Dict[str, str], Optional[Dict[str, Any]]], Dict[str, Any]]


def _http(method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    for attempt in range(3):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (500, 502, 503) or attempt == 2:
                raise                       # 429 (quota) does not clear in a second: fail at once instead of burning the time limit
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
        time.sleep(1.5 * (attempt + 1))
    return {}


def providers() -> list:
    """Gemini's Google-grounded search only: one authoritative, cited lookup per product, not several search APIs reconciled
    against each other. WEBPRICE_PROVIDERS (comma list) overrides this, for tests and for deliberately re-enabling the others."""
    forced = os.environ.get("WEBPRICE_PROVIDERS")
    if forced:
        return [n for n in forced.split(",") if n]
    return ["gemini"] if os.environ.get("GEMINI_API_KEY") else []


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
    if unit == "g" and amt >= 200:
        forms.add(f"{amt / 1000:g}")
    if unit == "ml" and amt >= 100:
        forms.add(f"{amt / 10:g}")
        forms.add(f"{amt / 1000:g}")
    units = r"(?:g|gr|grammes?|kg|kilo)" if (unit == "g" and amt >= 200) else {"g": r"(?:g|gr|grammes?)", "ml": r"(?:ml|cl|l|litres?)"}[unit]
    nums = "|".join(re.escape(f).replace(r"\.", "[,.]") for f in forms)
    return re.compile(rf"(?<![\d,.])(?:{nums})\s?{units}\b", re.I)


def _query(product: Dict[str, Any], variant: int = 0) -> str:
    """First wording: brand, name, size and 'prix €' (snippets that print a price). Second: the barcode with the brand, which brings up the shops' own pages for this exact pack."""
    q = product.get("quantity") or {}
    brand = str(product.get("brand") or "").split(",")[0]
    code = str(product.get("barcode") or "")
    if variant and len(code) >= 12:
        return " ".join(x for x in (code, brand, "prix") if x)
    tail = ("prix €", "prix supermarché drive")[variant]
    size = f"{q['amount']:g} {q['unit']}" if q.get("amount") else ""
    return " ".join(x for x in (brand, str(product.get("name") or ""), size, tail) if x).strip()


def _fetch_results(name: str, product: Dict[str, Any], http: Http, variant: int = 0) -> list:
    """[(url, text)] from one search provider."""
    query = _query(product, variant)
    if name == "brave":
        data = http("GET", BRAVE + "?" + urllib.parse.urlencode({"q": query, "country": "fr", "search_lang": "fr", "count": 10}),
                    {"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"}, None)
        return [(r.get("url") or "", " ".join([r.get("title") or "", r.get("description") or ""] + list(r.get("extra_snippets") or [])))
                for r in (data.get("web") or {}).get("results", [])]
    if name == "serper":
        data = http("POST", "https://google.serper.dev/search", {"X-API-KEY": os.environ["SERPER_API_KEY"], "Content-Type": "application/json"}, {"q": query, "gl": "fr", "hl": "fr", "num": 10})
        return [(r.get("link") or "", " ".join([r.get("title") or "", r.get("snippet") or ""] + [str(v) for v in (r.get("attributes") or {}).values()])) for r in data.get("organic", [])]
    if name == "langsearch":
        data = http("POST", LANGSEARCH, {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["LANGSEARCH_API_KEY"]},
                    {"query": f"{query} supermarché France", "freshness": "oneMonth", "summary": True, "count": 10})
        pages = ((data.get("data") or data).get("webPages") or {}).get("value", [])
        return [(r.get("url") or "", " ".join([r.get("name") or "", r.get("snippet") or "", r.get("summary") or ""])) for r in pages]
    data = http("POST", PARALLEL, {"Content-Type": "application/json", "x-api-key": os.environ["PARALLEL_API_KEY"]},
                {"objective": f"Prix actuel en euros en supermarché en France de : {query}. Donne les pages de supermarchés ou comparateurs qui indiquent ce prix.", "search_queries": [query]})
    return [(r.get("url") or "", " ".join([r.get("title") or ""] + list(r.get("excerpts") or []))) for r in data.get("results", [])]


def _name_words(product: Dict[str, Any], brand_w: set) -> set:
    """The words that identify a product by its name: 4+ letters, not the brand, not a pack size written into the name ("190g", "6x25g")."""
    return {w for w in _words(product.get("name")) if len(w) > 3 and not re.fullmatch(r"\d+(?:x\d+)?(?:g|gr|kg|ml|cl|l)", w)} - brand_w


_MANGLED = re.compile(r"(?<![\d,.])(\d{1,3})\.?\s?,\s?(\d{2})\.?\s?€")


def _clean(text: str) -> str:
    """Search snippets sometimes break a price into pieces ("4. ,59. €"): put it back together. A page rendered to Markdown
    (the 'parallel' provider) escapes punctuation ("5\\.65€") and puts each fragment of a price on its own line ("5\\n\\n,65\\n\\n€"):
    both leave a bare "65" or "61" right before the "€", which used to be read as the whole price."""
    t = (text or "").replace("\\.", ".").replace("\\-", "-")
    t = re.sub(r"(\d)\s+([,.]\d{1,2})\b", r"\1\2", t)      # "5\n\n,65" -> "5,65": a decimal fraction split onto its own line
    return _MANGLED.sub(r"\1,\2 €", t)


_PER_UNIT_AFTER = re.compile(r"^\s*(?:/|par\b|le\b|au\b|\bl[e']?\s)\s*(?:kg|kilo|litre|l\b)", re.I)


def _words(text: str) -> set:
    """Lower-case words of 3+ letters, accents removed ('séchée' = 'sechee') so a typo in the accents never breaks a match."""
    t = unicodedata.normalize("NFKD", (text or "").lower())
    ws = re.findall(r"[a-z0-9]{3,}", "".join(c for c in t if not unicodedata.combining(c)))
    return {w[:-1] if len(w) > 4 and w.endswith(("s", "x")) else w for w in ws}      # "aubergine" = "aubergines", "gateau" = "gateaux"


def _pack_price(text: str, size_units: float, size: Optional[Tuple[int, str]] = None) -> Optional[float]:
    """The pack price in a text: ignores prices labelled per kilo / per litre, and a price that is just another price scaled to a kilo."""
    cands, per_kilo = [], []
    for m in _PRICE.finditer(text):
        raw = m.group(1) or m.group(2)
        v = float(raw.replace(" ", "").replace(",", "."))
        if not (0.2 <= v <= 400):
            continue
        if size:
            near = _sizes_in(text[max(0, m.start() - 40):m.start()])
            if near and near[-1] != size:
                continue                          # "180 g env. 16,99 €/kg": that price belongs to another pack size
        if _PER_UNIT_AFTER.match(text[m.end():m.end() + 14]):
            per_kilo.append(v)                # "10,53 €/kg": no pack price, but the pack price follows from the size
            continue
        if re.search(r"(?:min|minimum|panier|livraison|gratuite?s?|offert|offerte?s?|d[eè]s|[aà]\s?[-.]?\s?p(?:artir)?\.?\s?d[e']?|des|frais|au\s?-\s?dessus)\W{0,6}$",
                     text[max(0, m.start() - 40):m.start()], re.I):
            continue                          # "Min 60,00 €", "Livraison gratuite àpd 39€": a shop's own conditions, not the product's price
        cands.append(v)
    if size_units > 0:
        per_unit = {b for a_ in cands for b in cands if a_ != b and abs(a_ / size_units - b) / b < 0.06}
        cands = [v for v in cands if v not in per_unit]
    cands = [v for v in cands if v <= 200]
    if cands and per_kilo and size_units > 0:
        expect = per_kilo[0] * size_units          # the pack price that goes with the page's own price per kilo
        near = [v for v in cands if abs(v - expect) / expect <= 0.04]
        if near:
            return near[0]
    if cands:
        return cands[0]
    if per_kilo and size_units > 0:           # only a per-kilo / per-litre price on the page: the individual price is that price times the pack size
        pack = round(per_kilo[0] * size_units, 2)
        return pack if 0.2 <= pack <= 200 else None
    return None


_LISTING = re.compile(r"[?&](?:q|s|search|query|k)=|/search|/recherche|/categor|/rayon|/cat/|/r/|/c/|/liste|/collection|/brand|/marque", re.I)


def _price_from(product: Dict[str, Any], results: list) -> Optional[Dict[str, Any]]:
    """A price only when two different sites talk about this product (brand and name words) and this pack size, and agree within 25 %."""
    q = product.get("quantity")
    size_re = _size_regex(q)
    if not q or not size_re:
        return None
    brand_w = _words(str(product.get("brand") or "").split(",")[0])
    name_w = _name_words(product, brand_w)
    size_units = q["amount"] / 1000.0
    by_host: Dict[str, Tuple[float, str]] = {}
    solid: set = set()                                     # hosts whose page is this exact product's own page (address names every word of it)
    size_t = (round(q["amount"]), q["unit"])
    code = str(product.get("barcode") or "")
    results = [(u, _clean(t)) for u, t in results]
    for url, text in results:
        if "openfoodfacts" in url:
            continue                                       # the product database itself, never a shop
        slug = _words(urllib.parse.unquote(urllib.parse.urlparse(url).path).replace("-", " ").replace("/", " "))
        tw = _words(text)
        exact = len(code) >= 8 and (code in url or code in text)      # the barcode names this exact pack: no need to check the name or the size
        if _LISTING.search(url):
            continue                                       # search and category pages mix many products, even when they mention this barcode among others
        if not exact:
            full_text = text + " " + urllib.parse.unquote(url)
            if not (size_re.search(text) or size_re.search(full_text)):
                continue
            if len(slug) >= 3 and name_w and not (name_w <= slug):
                continue                                   # a product page whose address names another variant (orange vs noisette): not this product
            if (brand_w and not (brand_w & tw)) or (name_w and not (name_w & tw)):
                continue
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        v = _pack_price(text, size_units, size_t)
        if v:
            by_host.setdefault(host, (v, url))
            if exact or (name_w and (name_w <= slug or len(name_w & slug) >= min(2, len(name_w))) and (brand_w & (slug | tw) or not brand_w)):
                solid.add(host)
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
            if any(abs(float((m.group(1) or m.group(2)).replace(" ", "").replace(",", ".")) - v0) / v0 <= 0.03 for m in _PRICE.finditer(text)):
                by_host[host] = (v0, url)
                break
    from . import chains as ch0
    if len(by_host) == 1:
        # Still a single source: accepted when it is a supermarket's own page (a chain's site that states this exact size and a price), not a random page.
        (h1, (v1, u1)), = by_host.items()
        if ch0.canon(h1.replace(".", " ")) or h1 in solid:
            by_host[h1 + "#"] = (v1, u1)        # a supermarket's page, or the product's own page on a shop site: counts as its own confirmation
    vals = sorted(v for v, _ in by_host.values())
    if len(vals) < 2:
        return None
    med = vals[len(vals) // 2]
    agree = [(h, v, u) for h, (v, u) in by_host.items() if abs(v - med) / med <= 0.25]
    if len(agree) < 2:
        return None
    price_c = round(med * 100)
    from . import chains as ch, retail, market
    stores = []
    for h, _, _ in agree:
        name = ch.canon(h.rstrip("#").replace(".", " "))          # courses.monoprix.fr -> Monoprix
        cid = retail.ID_OF.get(name) if name else None
        if cid and not retail.in_market(cid, market.current()):
            continue                                               # a chain from another country is never this market's own
        if name and name not in stores:
            stores.append(name)
    return {"per100_cents": round(price_c / q["amount"] * 100, 1), "pack_cents": price_c, "store": stores[0] if stores else None, "stores": stores,
            "chains": [retail.ID_OF[n] for n in stores if n in retail.ID_OF], "source_urls": [u for _, _, u in agree][:3],
            "date": time.strftime("%Y-%m-%d"), "source": "web_search", "approximate": True}


_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_PAGE_PRICE = re.compile(
    r'"price"\s*:\s*"?(\d{1,3}(?:[.,]\d{1,2})?)"?'
    r'|itemprop="price"[^>]*content="(\d+(?:[.,]\d{1,2})?)"'
    r'|(?:product|og):price:amount"[^>]*content="(\d+(?:[.,]\d{1,2})?)"'
    r'|data-price="(\d+(?:[.,]\d{1,2})?)"'
    r'|"lowPrice"\s*:\s*"?(\d+(?:[.,]\d{1,2})?)"?'
    r'|<span[^>]*class="[^"]*(?:price|prix)[^"]*"[^>]*>[\s\n]*(\d{1,3}(?:[.,]\d{2})?)\s*€',
    re.I
)


def _get_html(url: str, timeout: float = 6.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept-Language": "fr-FR,fr;q=0.9", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(500000).decode("utf-8", "replace")


def _candidate_pages(product: Dict[str, Any], results: list, limit: int = 3) -> list:
    """Shop pages that are this exact product's own page (the address names every word of it) but whose search snippet carries no price."""
    brand_w = _words(str(product.get("brand") or "").split(",")[0])
    name_w = _name_words(product, brand_w)
    out, hosts = [], set()
    code = str(product.get("barcode") or "")
    if not name_w and len(code) < 8:
        return out
    for url, text in results:
        if _LISTING.search(url):
            continue
        slug = _words(urllib.parse.unquote(urllib.parse.urlparse(url).path).replace("-", " ").replace("/", " "))
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        exact = len(code) >= 8 and code in url
        if host in hosts or not (exact or (name_w <= slug and (not brand_w or brand_w & (slug | _words(text))))):
            continue
        hosts.add(host)
        out.append(url)
        if len(out) >= limit:
            break
    return out


def _get_html(url: str, timeout: float = 6.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept-Language": "fr-FR,fr;q=0.9", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(500000).decode("utf-8", "replace")


def _candidate_pages(product: Dict[str, Any], results: list, limit: int = 3) -> list:
    """Shop pages that are this exact product's own page (the address names every word of it) but whose search snippet carries no price."""
    brand_w = _words(str(product.get("brand") or "").split(",")[0])
    name_w = _name_words(product, brand_w)
    out, hosts = [], set()
    code = str(product.get("barcode") or "")
    if not name_w and len(code) < 8:
        return out
    for url, text in results:
        if _LISTING.search(url):
            continue
        slug = _words(urllib.parse.unquote(urllib.parse.urlparse(url).path).replace("-", " ").replace("/", " "))
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        exact = len(code) >= 8 and code in url
        if host in hosts or not (exact or (name_w <= slug and (not brand_w or brand_w & (slug | _words(text))))):
            continue
        hosts.add(host)
        out.append(url)
        if len(out) >= limit:
            break
    return out


def _page_prices(product: Dict[str, Any], results: list, deadline: Optional[float], fetch: Callable[[str], str] = None) -> list:
    """Read the price off those product pages (structured data in the page). Returns [(url, text)] in the form the matcher reads, with the pack size the page itself states."""
    fetch = fetch or _get_html
    q = product.get("quantity") or {}
    size_re = _size_regex(q)
    pages = _candidate_pages(product, results)
    if not pages or not size_re or not q:
        return []
    from concurrent.futures import ThreadPoolExecutor
    left = max(1.0, min(6.0, (deadline - time.time()) - 1)) if deadline else 6.0
    if deadline and deadline - time.time() < 2:
        return []

    def one(u):
        try:
            html = fetch(u, left) if fetch is _get_html else fetch(u)
        except Exception:
            return None
        if not size_re.search(html):
            return None                        # the page does not state this pack size: its price may be for another one
        m = _PAGE_PRICE.search(html)
        if not m:
            return None
        v = float(next(g for g in m.groups() if g).replace(",", "."))
        return (u, f"{q['amount']:g} {q['unit']} {v:.2f} €") if 0.2 <= v <= 400 else None
    with ThreadPoolExecutor(max_workers=len(pages)) as ex:
        return [x for x in ex.map(one, pages) if x]


_gemini: Dict[str, Any] = {"down_until": 0.0, "error": None}
_down: Dict[str, float] = {}          # search provider -> time until which it is skipped (quota used up)
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


def _bounded(wall_cap: Optional[float], fn, *args, **kwargs):
    """Run fn with a hard wall-clock cap (`wall_cap`, seconds). A socket timeout only limits a single read; a server that trickles
    bytes slowly (seen from the 'parallel' provider) can otherwise keep a call alive, and so the whole search, for minutes past its
    deadline. The thread is abandoned rather than joined on a timeout, so this call itself never waits past `wall_cap`."""
    if not wall_cap or wall_cap <= 0:
        return fn(*args, **kwargs)
    ex = ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn, *args, **kwargs)
    try:
        return fut.result(timeout=wall_cap)
    finally:
        ex.shutdown(wait=False)


def _gemini_lookup(product: Dict[str, Any], transport: Transport, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """One Google-grounded Gemini lookup: a price only when it cites at least one page, for a known size in the same unit. Failures set last_error and return None."""
    global last_error, MODEL
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    barcode = str(product.get("barcode") or "")
    q = product.get("quantity")
    size = f"{q['amount']:g} {q['unit']}" if q else (product.get("quantityText") or "inconnu")
    body = {"contents": [{"parts": [{"text": PROMPT.format(name=product.get("name") or "", brand=f" ({product['brand']})" if product.get("brand") else "", ean=barcode, size=size)}]}],
            "tools": [{"google_search": {}}], "generationConfig": {"temperature": 0}}
    resp = None
    models_to_try = [MODEL] + [m for m in FALLBACK_MODELS if m != MODEL]
    for m in models_to_try:
        try:
            url = ENDPOINT.format(model=m) + "?key=" + key
            resp = transport(url, body, timeout=timeout) if (timeout and transport is _post) else transport(url, body)
            if resp:
                MODEL = m
                break
        except Exception as e:       # network, quota, bad key, retired model: no price, and do not cache the failure
            last_error = (str(getattr(e, "code", "")) + " " + type(e).__name__)[:80]
            if getattr(e, "code", None) == 404:
                continue
            return None
    if not resp:
        return None
    cand = (resp.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
    got = _parse(text)
    out = None
    if got:
        price_c = round(float(got["price_eur"]) * 100)
        qty = value.parse_quantity(str(got.get("pack_size") or "")) or ((q["amount"], q["unit"]) if q else None)
        gm = cand.get("groundingMetadata") or {}
        sources = [c["web"]["uri"] for c in gm.get("groundingChunks", []) if c.get("web", {}).get("uri")][:3]
        if not sources and gm.get("webSearchQueries"):
            sources = [f"https://www.google.com/search?q={urllib.parse.quote(q_)}" for q_ in gm.get("webSearchQueries", [])][:3]
        if not sources and barcode:
            sources = [f"https://www.google.com/search?q={barcode}"]
        # Accept only a plausible price for a known size, backed by at least one cited page, in the same unit family as the product
        if qty and 20 <= price_c <= 20000 and sources and (not q or qty[1] == q["unit"]):
            from . import chains as ch, retail, market
            st_name = ch.canon(str(got.get("store") or "").replace(".", " "))
            st_cid = retail.ID_OF.get(st_name) if st_name else None
            if st_cid and not retail.in_market(st_cid, market.current()):
                st_name, st_cid = None, None       # a store from another country is never this market's own
            elif not st_name:
                st_name = got.get("store")         # an unrecognised name (no known chain, so no market check applies): kept as free text, no logo
            out = {"per100_cents": round(price_c / qty[0] * 100, 1), "pack_cents": price_c, "store": st_name, "stores": [st_name] if st_name else [],
                   "chains": [st_cid] if st_cid else [],
                   "source_urls": sources,
                   "date": time.strftime("%Y-%m-%d"), "source": "web_search", "approximate": True, "size_found": {"amount": float(qty[0]), "unit": qty[1]}}
    return out


_SIZE = re.compile(r"(?<![\d,.])(\d{1,4}(?:[,.]\d{1,2})?)\s?(kg|g|gr|cl|ml|l)\b", re.I)


def _sizes_in(text: str) -> list:
    out = []
    for m in _SIZE.finditer(text or ""):
        v, u = float(m.group(1).replace(",", ".")), m.group(2).lower()
        if u == "kg": v, u = v * 1000, "g"
        elif u == "gr": u = "g"
        elif u == "cl": v, u = v * 10, "ml"
        elif u == "l": v, u = v * 1000, "ml"
        if 5 <= v <= 5000:
            out.append((round(v), u))
    return out


def _guess_size(product: Dict[str, Any], http: Http) -> Optional[Dict[str, Any]]:
    """The pack size of a product that has none in the database, read from product pages of this exact product (brand and every word of the name in the page address).
    Only when those pages agree on one size; otherwise None (no price is better than a price for the wrong pack)."""
    brand_w = _words(str(product.get("brand") or "").split(",")[0])
    name_w = _name_words(product, brand_w)
    if not name_w or not _budget_left():
        return None
    for prov in providers():
        if prov == "gemini":
            continue
        try:
            results = _fetch_results(prov, product, http, 0)
        except Exception as e:
            _set_error(e)
            continue
        sizes = []
        for url, text in results:
            slug = _words(urllib.parse.unquote(urllib.parse.urlparse(url).path).replace("-", " ").replace("/", " "))      # the page path, not the site name
            need = len(name_w) if len(name_w) <= 2 else max(2, -(-len(name_w) * 3 // 5))      # most of the name, not every word: "au citron et épices" is often shortened in a page address
            if (brand_w and not (brand_w & (slug | _words(text)))) or len(name_w & slug) < need:
                continue
            found = _sizes_in(text)
            if found:
                sizes.append(max(set(found), key=found.count))        # the size this page repeats most
        if sizes:
            amount, unit = max(sorted(set(sizes)), key=lambda z: (sizes.count(z), -z[0]))           # the pages disagree: take the size most pages give (the price stays marked approximate)
            return {"amount": float(amount), "unit": unit}
    return None


def _extract_grocers(product: Dict[str, Any], results: list) -> Tuple[List[str], List[str]]:
    """Grocery chains of the current market where this product is present. Returns (store_names, chain_ids)."""
    from . import chains as ch, retail, market
    brand_w = _words(str(product.get("brand") or "").split(",")[0])
    name_w = _name_words(product, brand_w)
    code = str(product.get("barcode") or "")
    stores, chains = [], []

    for url, text in results:
        if "openfoodfacts" in url:
            continue
        slug = _words(urllib.parse.unquote(urllib.parse.urlparse(url).path).replace("-", " ").replace("/", " "))
        tw = _words(text)
        exact = len(code) >= 8 and (code in url or code in text)
        has_name = exact or (name_w and len(name_w & (slug | tw)) >= max(1, min(2, len(name_w))))
        has_brand = not brand_w or bool(brand_w & (slug | tw))
        if not (has_name and has_brand):
            continue

        # A recognised supermarket chain only: never invent one from an arbitrary site name (a price comparator, a blog, a video site
        # mentioning the product is not evidence that a shop sells it). Stocking evidence must never be guessed (see retail.discover).
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        cname = ch.canon(host.replace(".", " ")) or next((n for n, rx in ch.CHAINS.items() if re.search(rx, host, re.I)), None)

        if cname and cname not in stores:
            cid = retail.ID_OF.get(cname)
            if cid and not retail.in_market(cid, market.current()):
                continue                 # a chain from another country never counts here ("Target" showing up in a French search)
            stores.append(cname)
            if cid and cid not in chains:
                chains.append(cid)

    return stores, chains


def _search_lookup(product: Dict[str, Any], http: Http, transport: Transport = _post, deadline: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Parallel search; no price when the sites it returns do not agree on this pack size. `deadline` (epoch seconds) stops trying further providers once passed;
    that is a timeout, not a miss, so it is never cached as "nothing found"."""
    global last_error
    last_error = None
    all_results = []
    if not _budget_left():
        last_error = "daily cap reached"
        return None
    assumed = None
    if not (product.get("quantity") or {}).get("amount"):
        assumed = _guess_size(product, http)
        if not assumed:
            # No size in the database and none found on product pages: Gemini's grounded search states the pack size with the price, and cites its pages.
            if "gemini" in providers() and time.time() >= _gemini["down_until"] and (not deadline or deadline - time.time() >= 4) and _budget_left():
                out = _gemini_lookup(product, transport, timeout=(deadline - time.time()) if deadline else None)
                if out:
                    out["provider"] = "gemini"
                    out["size_assumed"] = out.pop("size_found", None)
                return out
            return None
        product = {**product, "quantity": assumed}
    for variant in (0, 1):                  # the second wording is only tried when the first finds nothing (search results vary from one call to the next)
        # Quick providers (Serper, LangSearch) go first — about a second each. Gemini's grounded search can take 10–15 s so
        # it runs last on each variant pass, but it IS tried on both passes: the barcode-based query (variant 1) often
        # yields the most reliable result for French supermarket pages that JS-render their prices.
        order = [n for n in providers() if n != "gemini"] + [n for n in providers() if n == "gemini"]
        for name in order:
            if deadline and time.time() > deadline:
                last_error = "deadline"
                return None
            if variant and not _budget_left():
                return None
            if name == "gemini":
                if time.time() < _gemini["down_until"]:
                    continue                # Gemini just failed (quota, bad model): skip it for a few minutes instead of paying a failing call each time
                left = (deadline - time.time()) if deadline else None
                if left is not None and left < 4:
                    last_error = "deadline"
                    return None
                try:
                    out = _bounded(min(left, 20) if left else 20, _gemini_lookup, product, transport, timeout=left)
                except FuturesTimeoutError:
                    out, last_error = None, "deadline"      # a reply that trickled in slowly past our own budget: not a real miss
                if out:
                    out.pop("size_found", None)
                    out["provider"] = name
                    if assumed:
                        out["size_assumed"] = assumed
                    disc_stores, disc_chains = _extract_grocers(product, all_results)
                    out["stores"] = list(dict.fromkeys((out.get("stores") or []) + disc_stores))
                    out["chains"] = list(dict.fromkeys((out.get("chains") or []) + disc_chains))
                    return out
                if last_error:              # a Gemini failure must not stop a genuine "nothing found" from being cached for the other providers
                    if "Timeout" not in last_error and last_error != "deadline":
                        _gemini.update(down_until=time.time() + 600, error=last_error)
                    last_error = "deadline" if (deadline and time.time() > deadline) or last_error == "deadline" else None
                continue
            if time.time() < _down.get(name, 0):
                continue                    # this provider just said "quota used up": skip it for a few minutes
            try:
                left = (deadline - time.time()) if deadline else None
                cap = min(left, 12) if left else 12          # a hard wall-clock cap: a slow provider must never outrun the budget
                found = _bounded(cap, _fetch_results, name, product, http, variant)
                all_results.extend(found)
                out = _price_from(product, found)
                if not out:
                    page_left = (deadline - time.time()) if deadline else None
                    extra = _bounded(min(page_left, 8) if page_left else 8, _page_prices, product, found, deadline)       # right product page found, but its snippet shows no price: read the page
                    if extra:
                        all_results.extend(extra)
                        out = _price_from(product, found + extra)
            except FuturesTimeoutError:
                last_error = "deadline"
                continue
            except Exception as e:
                _set_error(e)
                if getattr(e, "code", None) == 429:
                    _down[name] = time.time() + 600
                continue
            if out:
                out["provider"] = name
                if assumed:
                    out["size_assumed"] = assumed
                disc_stores, disc_chains = _extract_grocers(product, all_results)
                out["stores"] = list(dict.fromkeys((out.get("stores") or []) + disc_stores))
                out["chains"] = list(dict.fromkeys((out.get("chains") or []) + disc_chains))
                return out
        if not product.get("brand"):
            break                           # an unbranded product is rarely found by a second try: do not pay for it
    disc_stores, disc_chains = _extract_grocers(product, all_results)
    if disc_chains or disc_stores:
        return {
            "per100_cents": None,
            "pack_cents": None,
            "store": disc_stores[0] if disc_stores else None,
            "stores": disc_stores,
            "chains": disc_chains,
            "source_urls": [u for u, _ in all_results if any(c in u.lower() for c in disc_chains)][:3],
            "date": time.strftime("%Y-%m-%d"),
            "source": "web_search",
            "approximate": True,
            "no_price": True,
        }
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


def lookup(product: Dict[str, Any], transport: Transport = _post, use_cache: bool = True, http: Optional[Http] = None, deadline: Optional[float] = None, force: bool = False) -> Optional[Dict[str, Any]]:
    """{per100_cents, pack_cents, store, source_urls, date, source:'web_search', approximate:True} or None.

    force=True: bypass a cached miss and retry the search (but still serve a cached hit, since a found price is reliable).
    Use this on explicit user-facing lookups where a timed-out background search may have left a stale miss.
    """
    global last_error
    barcode = str(product.get("barcode") or "")
    if not barcode or provider() is None:
        return None
    old = None
    if use_cache:
        fresh, data = _cached(barcode)
        if fresh:
            if data is not None:
                return data             # a real price found earlier: serve it
            if not force:
                return None             # cached miss, no force: respect the TTL
            # force=True + cached miss: fall through and retry the search now
        old = data                       # an expired price we found earlier: kept, never thrown away
    if provider():
        out = _search_lookup(product, http or _http, transport, deadline)
        if use_cache and out:
            _store(barcode, out)
        elif use_cache and not old:
            # Cache a genuine miss (last_error is None = search completed fully, nothing found).
            # Never cache a timeout/deadline: the search was cut short and may succeed next time.
            # This applies whether force=True or not: a thorough search that found nothing is worth remembering.
            if last_error is None:
                _store(barcode, None)
            # last_error == "deadline": don't cache; the next explicit call will retry with a full budget.
        if not out and old:
            return {**old, "stale": True}   # the re-search found nothing: keep showing the stored price, marked as older
        return out
    return None
