"""Beta: identify a packaged food product from a photo, then find its barcode in the Open Food Facts copy.
Step 1 asks Claude to read what is printed on the pack (brand, name, size, and a barcode only if it is legible).
Step 2 matches that text against the product name index. A barcode is never invented: it always comes from the database,
or from digits that pass the GS1 checksum and exist in the database."""
import json
import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mieux.vision")

MODEL = os.environ.get("VISION_MODEL", "claude-opus-5-5")
MAX_BYTES = 5_000_000
MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "identified": {"type": "boolean"},
        "brand": {"type": "string"},
        "product_name": {"type": "string"},
        "variant": {"type": "string"},
        "size": {"type": "string"},
        "barcode_digits": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["identified", "brand", "product_name", "variant", "size", "barcode_digits", "confidence"],
    "additionalProperties": False,
}
PROMPT = (
    "This photo was taken by a shopper in a supermarket. Identify the packaged food or drink product in it, using only what is printed on the pack. "
    "brand: the brand as printed (empty string if none is visible). product_name: the product's name as printed, in the pack's own language, without the brand. "
    "variant: flavour, type or label such as bio or zéro, if printed (else empty). size: the net quantity as printed, for example '200 g' or '1 L' (else empty). "
    "barcode_digits: the digits of the barcode only if you can read every digit clearly, otherwise an empty string. Never guess or complete digits. "
    "If the photo does not show a packaged food or drink product, set identified to false and leave the other text fields empty. "
    "confidence reflects how sure you are of the brand and product name."
)
NOT_IDENTIFIED = {"identified": False, "brand": "", "product_name": "", "variant": "", "size": "", "barcode_digits": "", "confidence": "low"}


def identify(image: bytes, media_type: str) -> Dict[str, Any]:
    """Ask Claude to read the pack. Raises RuntimeError when no API key is configured."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    import base64
    import anthropic  # imported here so the rest of the API starts without the package

    client = anthropic.Anthropic(timeout=45.0, max_retries=1)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,  # thinking tokens count against this, even at low effort
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": base64.standard_b64encode(image).decode("ascii")}},
            {"type": "text", "text": PROMPT},
        ]}],
    )
    if resp.stop_reason == "refusal":
        logger.info({"event": "vision_refusal"})
        return dict(NOT_IDENTIFIED)
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        out = json.loads(text)
    except ValueError:
        logger.warning({"event": "vision_bad_json", "stop_reason": resp.stop_reason})
        return dict(NOT_IDENTIFIED)
    return {**NOT_IDENTIFIED, **{k: out.get(k, NOT_IDENTIFIED[k]) for k in NOT_IDENTIFIED}}


def valid_barcode(code: str) -> bool:
    """EAN-8, UPC-A (12) or EAN-13 with a correct GS1 check digit."""
    if not re.fullmatch(r"\d{8}|\d{12}|\d{13}", code or ""):
        return False
    digits = [int(c) for c in code]
    body, check = digits[:-1], digits[-1]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def _plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", (s or "").lower()) if not unicodedata.combining(c))


def _tokens(s: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _plain(s)) if len(t) > 1 or t.isdigit()]


def _grams(size: str) -> Optional[float]:
    """'200 g' -> 200, '1,5 L' -> 1500 (ml and g share a scale: only used to compare pack sizes)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|l|cl|ml)\b", _plain(size))
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return v * {"kg": 1000, "g": 1, "l": 1000, "cl": 10, "ml": 1}[m.group(2)]


def _score(ident: Dict[str, Any], p: Dict[str, Any]) -> float:
    brand_t, name_t = set(_tokens(ident["brand"])), set(_tokens(f"{ident['product_name']} {ident['variant']}"))
    cand_name = _plain(p.get("product_name") or "")
    cand_all = f"{cand_name} {_plain(p.get('brands') or '')}"
    name_hit = sum(t in cand_name or t in cand_all for t in name_t) / len(name_t) if name_t else 0.0
    brand_hit = (sum(t in cand_all for t in brand_t) / len(brand_t)) if brand_t else 0.5  # no brand printed: neither a plus nor a minus
    want, have = _grams(ident["size"]), _grams(p.get("quantity") or "")
    size = 0.5 if not want or not have else (1.0 if abs(want - have) / max(want, have) < 0.06 else 0.0)
    return round(0.5 * name_hit + 0.35 * brand_hit + 0.15 * size, 3)


def _queries(ident: Dict[str, Any]) -> List[str]:
    brand, name, variant = ident["brand"].strip(), ident["product_name"].strip(), ident["variant"].strip()
    name_t = _tokens(f"{name} {variant}")
    qs = [f"{brand} {name} {variant}", f"{brand} {name}", f"{brand} {' '.join(name_t[:2])}", f"{name} {variant}", name]
    seen, out = set(), []
    for q in qs:
        q = " ".join(q.split())
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


def match(off, ident: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Candidates from the product database, best first: {barcode, name, brand, quantity, image, match}."""
    found: Dict[str, Dict[str, Any]] = {}
    code = re.sub(r"\D", "", ident.get("barcode_digits") or "")
    if valid_barcode(code):  # printed digits that pass the checksum and exist in the database: an exact hit
        try:
            p = off.get_product(code)
        except Exception:  # database or network trouble: fall through to the name search
            p = None
        if p and p.get("product_name"):
            found[code] = {**p, "code": code, "_exact": True}
    if ident["identified"] and (ident["product_name"] or ident["brand"]):
        for q in _queries(ident):
            try:
                rows = off.search_name(q)
            except Exception:
                rows = []
            for r in rows:
                c = r.get("code")
                if c and r.get("product_name") and c not in found:
                    found[c] = r
            if len(found) >= 10:
                break
    ranked = []
    for c, p in found.items():
        s = 1.0 if p.get("_exact") else _score(ident, p)
        if s >= 0.4:
            ranked.append({"barcode": c, "name": p.get("product_name"), "brand": (p.get("brands") or "").split(",")[0].strip() or None,
                           "quantity": p.get("quantity") or None, "image": p.get("image_front_small_url") or None, "match": s, "exact": bool(p.get("_exact"))})
    ranked.sort(key=lambda r: (-r["match"], r["name"] or ""))
    return ranked[:limit]
