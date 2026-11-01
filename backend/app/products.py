"""Normalisation of Open Food Facts records into Mieux's Product shape. Unknown nutrients stay None, never 0."""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .value import parse_quantity
from .score import quality
from .taxonomy import classify

SCHEMA_VERSION = 25  # bump when normalize() output changes so cached rows are refreshed
CORE = ["energyKcal100g", "fat100g", "saturatedFat100g", "carbohydrates100g", "sugars100g", "protein100g", "salt100g"]
NS_RANK = {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}


def _num(nm: Dict[str, Any], key: str) -> Optional[float]:
    v = nm.get(key + "_100g")
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# (OFF key, label key, display unit, grams->unit factor, EU nutrient reference value in that unit)
MICRO = [
    ("vitamin-a", "vit_a", "µg", 1e6, 800), ("vitamin-d", "vit_d", "µg", 1e6, 5), ("vitamin-e", "vit_e", "mg", 1e3, 12), ("vitamin-k", "vit_k", "µg", 1e6, 75),
    ("vitamin-c", "vit_c", "mg", 1e3, 80), ("vitamin-b1", "vit_b1", "mg", 1e3, 1.1), ("vitamin-b2", "vit_b2", "mg", 1e3, 1.4), ("vitamin-pp", "vit_b3", "mg", 1e3, 16),
    ("vitamin-b6", "vit_b6", "mg", 1e3, 1.4), ("vitamin-b9", "vit_b9", "µg", 1e6, 200), ("vitamin-b12", "vit_b12", "µg", 1e6, 2.5),
    ("calcium", "calcium", "mg", 1e3, 800), ("iron", "iron", "mg", 1e3, 14), ("magnesium", "magnesium", "mg", 1e3, 375), ("potassium", "potassium", "mg", 1e3, 2000), ("zinc", "zinc", "mg", 1e3, 10),
]


ULTRA = re.compile(r"(ar[oô]me|flavou?r|[eé]mulsifi|sirop de (glucose|fructose|ma[iï]s)|glucose|fructose|dextrose|maltodextrin|hydrogen|hydrog[eé]n|isolat|concentr[eé] de prot|colorant|colou?r|[eé]dulcorant|sweeten|exhausteur|enhancer|amidon modifi|modified starch|gomme|gum |lactosérum|whey|huile de palme|palm oil|épaississant|thicken|stabilis|conservateur|preservative|e\d{3})", re.I)
CULINARY = ("oils", "butters", "sugars", "salts", "flours", "honeys", "vinegars", "margarines", "creams")
ULTRA_CATS = ("sodas", "snacks", "biscuits", "cookies", "chips", "confectioner", "candies", "chocolate-spreads", "sweet-spreads", "ready-meals", "instant", "cereal-bars", "energy-drinks", "nuggets", "frozen-pizzas")


def estimate_nova(ing: Optional[str], additives: List[str], cats: List[str]):
    """NOVA group 1-4 from the ingredient list, additives and category when the database has none. Always flagged as an estimate."""
    joined = " ".join(cats).lower()
    parts = [x for x in re.split(r"[,;]", ing or "") if x.strip()]
    if any(c in joined for c in ULTRA_CATS) or len(additives) >= 2 or (ing and ULTRA.search(ing)):
        return 4
    if any(c in joined for c in CULINARY) and len(parts) <= 2:
        return 2
    if ing and len(parts) <= 1 and not additives:
        return 1
    if ing and len(parts) > 8:
        return 4
    if ing:
        return 3
    return None  # nothing to go on


def _serving(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def micronutrients(nm: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Vitamins and minerals per 100 g, only those the database actually has (absent is never shown as zero). OFF stores grams."""
    out = []
    for key, label, unit, factor, nrv in MICRO:
        v = _num(nm, key)
        if v is None:
            continue
        amt = v * factor
        out.append({"key": label, "amount": round(amt, 2), "unit": unit, "nrv_pct": round(amt / nrv * 100)})
    return out


def _nova(raw, ing, cats):
    g = str(raw.get("nova_group") or "")
    if g.isdigit() and 1 <= int(g) <= 4:
        return int(g), False
    est = estimate_nova(ing, [a.replace("en:", "") for a in raw.get("additives_tags") or []], cats)
    return est, est is not None


def _sold_in_france(raw):
    """True when Open Food Facts lists France among the countries of sale. How solid that is: 'gs1_fr' (French GS1 barcode prefix, strong),
    'off_tag' (tag only: to be confirmed); a French shop price in Open Prices upgrades it to 'open_prices' at request time."""
    tags = raw.get("countries_tags") or []
    if not tags:
        return None
    return "en:france" in tags


def _fr_evidence(raw):
    code = str(raw.get("code") or "")
    if "en:france" not in (raw.get("countries_tags") or []):
        return None
    return "gs1_fr" if (code[:3].isdigit() and 300 <= int(code[:3]) <= 379) or len(code) < 8 else "off_tag"


def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    out = _normalize(raw)
    nm = raw.get("nutriments") or {}
    out["taxonomy"] = classify(out)
    out["organic"] = any(l in ("en:organic", "en:eu-organic", "fr:ab-agriculture-biologique") for l in raw.get("labels_tags") or [])
    fvn = _num(nm, "fruits-vegetables-legumes-estimate-from-ingredients")
    inputs = {"trans": _num(nm, "trans-fat"), "added": _num(nm, "added-sugars"), "fvn": fvn if fvn is not None else _num(nm, "fruits-vegetables-nuts-estimate-from-ingredients")}
    out["scoreInputs"] = inputs  # kept so the score can be recomputed (strict additives, user data) without refetching
    out["score"] = quality(out, False, inputs)
    return out


def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    nm = raw.get("nutriments") or {}
    kcal = _num(nm, "energy-kcal")
    if kcal is None and _num(nm, "energy-kj") is not None:
        kcal = _num(nm, "energy-kj") / 4.184
    salt = _num(nm, "salt")
    if salt is None and _num(nm, "sodium") is not None:
        salt = _num(nm, "sodium") * 2.5
    nutriments = {
        "energyKcal100g": kcal, "fat100g": _num(nm, "fat"), "saturatedFat100g": _num(nm, "saturated-fat"),
        "carbohydrates100g": _num(nm, "carbohydrates"), "sugars100g": _num(nm, "sugars"),
        "protein100g": _num(nm, "proteins"), "fiber100g": _num(nm, "fiber"), "salt100g": salt,
    }
    cats = [c for c in raw.get("categories_tags") or [] if c.startswith("en:") and c == c.lower()]
    grade = (raw.get("nutriscore_grade") or "").lower()
    ts = raw.get("last_modified_t")
    updated = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else None
    ing = raw.get("ingredients_text") or None
    missing = [k for k in CORE if nutriments[k] is None]
    return {
        "_v": SCHEMA_VERSION, "id": str(raw.get("code")), "barcode": str(raw.get("code")), "name": raw.get("product_name") or "Unnamed product",
        "brand": raw.get("brands") or None, "category": cats[-1] if cats else None, "categories": cats,
        "imageUrl": raw.get("image_front_small_url") or None, "quantityText": raw.get("quantity") or None,
        "quantity": (lambda q: {"amount": q[0], "unit": q[1]} if q else None)(parse_quantity(raw.get("quantity"), raw.get("product_quantity"), raw.get("product_quantity_unit"))),
        "nutriments": nutriments, "micronutrients": micronutrients(nm), "novaGroup": _nova(raw, ing, cats)[0], "novaEstimated": _nova(raw, ing, cats)[1],
        "servingG": (lambda v: v if v and v > 0 else None)(_serving(raw.get("serving_quantity"))),
        "countries": [c.replace("en:", "") for c in raw.get("countries_tags") or []],
        "soldInFrance": _sold_in_france(raw), "frEvidence": _fr_evidence(raw),
        "ingredientsText": ing,
        "allergens": [a.replace("en:", "") for a in raw.get("allergens_tags") or []],
        "traces": [a.replace("en:", "") for a in raw.get("traces_tags") or []],
        "additives": [a.replace("en:", "") for a in raw.get("additives_tags") or []],
        "analysis": list(raw.get("ingredients_analysis_tags") or []),
        "nutriScore": grade if grade in NS_RANK else None, "nutriScoreVersion": raw.get("nutriscore_version") or None,
        "dataQuality": {"nutritionComplete": not missing, "missingNutrients": missing, "ingredientsAvailable": bool(ing),
                        "allergensAvailable": bool(ing), "productImageAvailable": bool(raw.get("image_front_small_url")),
                        "nutriScoreAvailable": grade in NS_RANK, "source": "Open Food Facts", "lastUpdatedAt": updated},
    }
