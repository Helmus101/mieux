"""Approximate shelf price from a Google-grounded Gemini lookup, for products that have no observed price.

Never an observed price: callers must label it ("~", source "web_search") and keep it out of the cheapest / best-value winners. Off unless
GEMINI_API_KEY is set. Results (and misses) are cached per barcode so a product is looked up once, not on every scan."""
import json
import os
import re
import sqlite3
import time
import urllib.request
from typing import Any, Callable, Dict, Optional, Tuple

from . import value

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
HIT_TTL = 14 * 86400
MISS_TTL = 3 * 86400
CACHE_PATH = os.environ.get("WEBPRICE_CACHE", os.path.join(os.path.dirname(os.environ.get("OP_LOCAL", "/tmp/x")) or ".", "webprice_cache.db"))

PROMPT = (
    "Trouve le prix actuel en euros de ce produit alimentaire dans un supermarché en France (drive ou magasin), "
    "à partir de pages de supermarchés ou de comparateurs. Produit : {name}{brand}. Code-barres : {ean}. Format : {size}.\n"
    "Réponds UNIQUEMENT par un objet JSON : {{\"price_eur\": nombre, \"pack_size\": \"ex. 500 g\", \"store\": \"enseigne\", \"found\": true}}. "
    "Si tu n'es pas sûr que le prix concerne exactement ce produit et ce format, réponds {{\"found\": false}}. N'invente rien."
)

Transport = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def _post(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(CACHE_PATH)
    db.execute("create table if not exists webprice (barcode text primary key, at real, data text)")
    return db


def _cached(barcode: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    try:
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
        db = _db()
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


def lookup(product: Dict[str, Any], transport: Transport = _post, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """{per100_cents, pack_cents, store, source_urls, date, source:'web_search', approximate:True} or None."""
    key = os.environ.get("GEMINI_API_KEY")
    barcode = str(product.get("barcode") or "")
    if not key or not barcode:
        return None
    if use_cache:
        fresh, data = _cached(barcode)
        if fresh:
            return data
    q = product.get("quantity")
    size = f"{q['amount']:g} {q['unit']}" if q else (product.get("quantityText") or "inconnu")
    body = {"contents": [{"parts": [{"text": PROMPT.format(name=product.get("name") or "", brand=f" ({product['brand']})" if product.get("brand") else "", ean=barcode, size=size)}]}],
            "tools": [{"google_search": {}}], "generationConfig": {"temperature": 0}}
    try:
        resp = transport(ENDPOINT.format(model=MODEL) + "?key=" + key, body)
    except Exception:       # network, quota, bad key: no price, and do not cache the failure
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
    if use_cache:
        _store(barcode, out)
    return out
