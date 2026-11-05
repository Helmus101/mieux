"""Mieux Quality Score v3. Three separate outputs: nutritional quality (anchored on Nutri-Score 2023 points, so positives cannot mask negatives),
ingredient quality (additives A-D + ingredient composition) and processing (NOVA, shown apart). The overall score combines the first two with safeguards.
Nine visible dimensions, category profiles, independent warnings, data confidence.
Weights and anchors are initial product-design values (not scientific standards); thresholds follow the UK FSA / EU front-of-pack bands
(low / high per 100 g or 100 ml) and are interpolated piecewise-linearly. Everything here is deterministic and explainable."""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .additives_db import T as ADDITIVES, USE as ADDITIVE_USE

VERSION = "3.0"

# ---------------------------------------------------------------- category profiles
# weight 0 = the dimension is irrelevant for the category (dropped, weight redistributed). Relevant but missing data = incomplete, not irrelevant.
NOT_ON_LABELS = ("micro", "plant")  # vitamins/minerals and plant share are almost never printed: their absence must not flag every product
DIMS = ["fat", "sugar", "salt", "energy", "protein", "fibre", "plant", "micro", "additives", "ingredients"]
PLANT_PROFILES = {"nuts_seeds", "fruits_veg", "legumes", "sauces", "ready_meals", "frozen", "grains_cereals", "default", "snacks_confectionery"}  # where the share of vegetables / fruit / legumes / nuts says something
BASE = {"fat": .15, "sugar": .15, "salt": .10, "energy": .10, "protein": .15, "fibre": .15, "micro": .10, "additives": .10, "ingredients": .10}
PROFILES: Dict[str, Dict[str, float]] = {
    "default": BASE,
    "plain_yogurt": {"fat": .15, "sugar": .15, "salt": .05, "protein": .25, "fibre": 0, "micro": .10, "additives": .15, "ingredients": .15},
    "dairy": {"fat": .20, "sugar": .15, "salt": .10, "protein": .20, "fibre": 0, "micro": .10, "additives": .10, "ingredients": .15},
    "meat_fish": {"fat": .20, "sugar": .05, "salt": .20, "protein": .20, "fibre": 0, "micro": .10, "additives": .15, "ingredients": .10},
    "eggs": {"fat": .20, "sugar": 0, "salt": .05, "protein": .30, "fibre": 0, "micro": .20, "additives": .10, "ingredients": .15},
    "fruits_veg": {"fat": .05, "sugar": .20, "salt": .10, "protein": 0, "fibre": .25, "micro": .25, "additives": .05, "ingredients": .10},
    "grains_cereals": {"fat": .10, "sugar": .20, "salt": .10, "protein": .10, "fibre": .25, "micro": .05, "additives": .10, "ingredients": .10},
    "bread_bakery": {"fat": .10, "sugar": .15, "salt": .15, "protein": .10, "fibre": .25, "micro": 0, "additives": .15, "ingredients": .10},
    "legumes": {"fat": .05, "sugar": .05, "salt": .10, "protein": .25, "fibre": .25, "micro": .15, "additives": .05, "ingredients": .10},
    "snacks_confectionery": {"fat": .25, "sugar": .25, "salt": .10, "protein": .05, "fibre": .10, "micro": 0, "additives": .15, "ingredients": .10},
    "drinks": {"fat": .05, "sugar": .40, "salt": .05, "protein": 0, "fibre": 0, "micro": .05, "additives": .30, "ingredients": .15},
    "plant_drinks": {"fat": .10, "sugar": .30, "salt": .05, "protein": .15, "fibre": 0, "micro": .10, "additives": .20, "ingredients": .10},
    "nuts_seeds": {"fat": .20, "sugar": .10, "salt": .10, "protein": .15, "fibre": .15, "micro": .10, "additives": .10, "ingredients": .10},
    "oils_fats": {"fat": .70, "sugar": 0, "salt": .05, "protein": 0, "fibre": 0, "micro": 0, "additives": .10, "ingredients": .15},
    "frozen": BASE,
    "ready_meals": {"fat": .15, "sugar": .10, "salt": .20, "protein": .15, "fibre": .10, "micro": 0, "additives": .15, "ingredients": .15},
    "sauces": {"fat": .15, "sugar": .20, "salt": .25, "protein": .05, "fibre": .05, "micro": 0, "additives": .20, "ingredients": .20},
}
for _p in PROFILES.values():
    _p.setdefault("energy", .10)
PROFILES["oils_fats"]["energy"] = 0
# first match wins (more specific first)
RULES: List[Tuple[str, str]] = [
    ("plain_yogurt", r"yogurts|yoghurts|yaourts|fromages-blancs|skyr"), ("plant_drinks", r"plant-based-(milk|beverages)|milk-substitutes|rice-based-drinks|oat-based-drinks|soy-milks"),
    ("oils_fats", r"vegetable-oils|olive-oils|fats|oils|butters|margarines"), ("dairy", r"dairies|cheeses|milks|creams|butters"),
    ("meat_fish", r"meats|fishes|seafood|poultry|sausages|hams|charcuterie|fish"), ("eggs", r"\beggs\b"),
    ("sauces", r"tomato-sauces|pasta-sauces|\bsauces\b|condiments|dressings|mayonnaises|ketchups|mustards|vinegars"),
    ("legumes", r"legumes|pulses|lentils|chickpeas|beans"), ("fruits_veg", r"fruits|vegetables|fresh-plant|legumes-and-their-products|compotes"),
    ("bread_bakery", r"breads|biscottes|rusks|pastries|viennoiseries|crackers|buns"), ("grains_cereals", r"cereals|pasta|rice|flours|breakfast-cereals|grains|mueslis"),
    ("nuts_seeds", r"(?:^|\s)en:(?:nuts|almonds|cashew-nuts|peanuts|pistachios|walnuts|hazelnuts|pecan-nuts|brazil-nuts|seeds|sunflower-seeds|pumpkin-seeds|sesame-seeds|chia-seeds|flax-seeds|mixed-nuts|dried-nuts|roasted-nuts|shelled-nuts)\b"),
    ("snacks_confectionery", r"snacks|confectioneries|chocolates|candies|biscuits|cakes|spreads|sweet-spreads|desserts|ice-creams|chips|cookies"),
    ("drinks", r"(?:^|\s)en:(?:beverages|[a-z-]*(?:drinks|juices|sodas|waters|nectars|teas|coffees))\b"),
    ("frozen", r"frozen"), ("ready_meals", r"meals|pizzas|sandwiches|soups|quiches|prepared"), ("sauces", r"sauces|condiments|dressings|mayonnaises|ketchups|mustards|vinegars"),
]

# ---------------------------------------------------------------- piecewise-linear scoring
def interp(x: float, anchors: List[Tuple[float, float]]) -> float:
    """anchors = [(value, score)] sorted by value. Linear between anchors, flat beyond the ends."""
    if x <= anchors[0][0]:
        return anchors[0][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y1
    return anchors[-1][1]


def banded(low: float, high: float) -> List[Tuple[float, float]]:
    """Lower is better. At the low threshold the score is 75, at the high threshold 30, at twice the high threshold 0."""
    return [(0, 100), (low, 75), (high, 30), (high * 2, 0)]


# (low, high) per 100 g or 100 ml, UK FSA / EU front-of-pack bands
BANDS = {"solid": {"sat": (1.5, 5.0), "sugar": (5.0, 22.5), "salt": (0.3, 1.5), "fat": (3.0, 17.5)},
         "liquid": {"sat": (0.75, 2.5), "sugar": (2.5, 11.25), "salt": (0.3, 0.75), "fat": (1.5, 8.75)}}
PROTEIN = [(0, 25), (3, 50), (8, 75), (15, 92), (25, 100)]
FIBRE = [(0, 25), (2, 50), (4, 70), (7, 90), (10, 100)]

# ---------------------------------------------------------------- additives A-D (evidence-based, simplified; unknown additive = B, low evidence)
ADD_PENALTY = {"A": 0, "B": 6, "C": 22, "D": 50}  # balanced reading
ADD_PENALTY_STRICT = {"A": 0, "B": 20, "C": 50, "D": 100}  # Yuka: -6 / -15 / -30 points out of the 30 for limited / moderate / high risk
ADD_NOTE = {"A": "Pas de préoccupation identifiée dans ce contexte", "B": "Préoccupation limitée ou selon le contexte", "C": "Préoccupation selon les conditions d'usage", "D": "Préoccupation documentée plus forte ou usage restreint"}


def additive_level(code: str, strict: bool = False) -> Tuple[str, bool]:
    """A-D from the evidence table (additives_db). strict = the precautionary, Yuka-like reading. Unknown additives are B and flagged as not verified."""
    row = ADDITIVES.get(code.lower().replace("en:", ""))
    if not row:
        return "B", False
    return (row[2] if strict else row[1]), True


def additive_info(code: str) -> Dict[str, Any]:
    row = ADDITIVES.get(code.lower().replace("en:", ""))
    if not row:
        return {"name": None, "why": None, "use": None, "found": None}
    use = ADDITIVE_USE.get(code.lower().replace("en:", ""))
    return {"name": row[0], "why": row[3], "use": use[0] if use else None, "found": use[1] if use else None}


# ---------------------------------------------------------------- sugar origin (ingredients based)
NATURAL_SOURCES = re.compile(r"\b(lait|lactose|fruits?|pomme|poire|banane|orange|raisin|datte|figue|mangue|fraise|framboise|myrtille|cerise|abricot|p[êe]che|carotte|betterave|tomate|jus de|pur[ée]e|milk|apple|banana|grape|date|juice)\b", re.I)
ADDED_SUGAR = re.compile(r"\b(sucre|sirop|glucose|fructose|saccharose|dextrose|miel|maltodextrine|cassonade|sugar|syrup|honey|molasses|m[ée]lasse|jus concentr|concentrated)\b", re.I)


def sugar_profile(ing, total):
    if total is None:
        return None
    if not ing:
        return {"total": total, "kind": "unknown", "added": [], "natural": []}
    added = sorted({m.group(0).lower() for m in ADDED_SUGAR.finditer(ing)})
    natural = sorted({m.group(0).lower() for m in NATURAL_SOURCES.finditer(ing)})
    kind = "none" if total < 0.5 else "mixed" if added and natural else "added" if added else "natural"
    return {"total": round(total, 1), "kind": kind, "added": added, "natural": natural}


# ---------------------------------------------------------------- helpers
def profile_of(cats: List[str]) -> str:
    text = " ".join(cats)
    for pid, rx in RULES:
        if re.search(rx, text):
            return pid
    return "default"


PLAIN_INFUSION = re.compile(r"(?:^|\s)en:(?:herbal-teas|herbal-infusions|infusions|tisanes|teas|black-teas|green-teas|white-teas|tea-bags|herbal-tea-bags|coffees|ground-coffees|coffee-beans|waters|spring-waters|mineral-waters)\b")
DRINK_TAGS = re.compile(r"(?:^|\s)en:(?:beverages|plant-based-beverages|waters|spring-waters|mineral-waters|milks|fruit-juices|fruit-nectars|juices|sodas|colas|carbonated-drinks|energy-drinks|sweetened-beverages|teas|iced-teas|coffees|plant-milks|plant-based-milk-alternatives|rice-based-drinks|oat-based-drinks|soy-milks|almond-milks|hazelnut-based-drinks|alcoholic-beverages|wines|beers|spirits)\b")


def is_liquid(cats: List[str], p: Dict[str, Any]) -> bool:
    q = p.get("quantity")
    if q:
        return q.get("unit") == "ml"
    return bool(DRINK_TAGS.search(" ".join(cats)))


def _band(total: int) -> Dict[str, str]:
    return ({"key": "excellent", "tone": "g"} if total >= 75 else {"key": "good", "tone": "g2"} if total >= 50
            else {"key": "poor", "tone": "w"} if total >= 25 else {"key": "bad", "tone": "b"})


def _tone(score: float) -> str:
    return "g" if score >= 75 else "g2" if score >= 50 else "w" if score >= 25 else "b"


# ---------------------------------------------------------------- Nutri-Score 2023 points (official thresholds) per 100 g / 100 ml
def _pts(v: Optional[float], thresholds: List[float]) -> int:
    return 0 if v is None else sum(1 for t in thresholds if v > t)


ASSUMED_POINTS = {"energy": 3, "sugars": 3, "sat": 2, "salt": 2}  # typical packaged food, used only for a nutrient that is missing


def nutri_points(n, drink: bool, natural_sugar: bool, use_protein: bool, use_fibre: bool, fvn: Optional[float] = None, cheese: bool = False) -> Optional[Dict[str, Any]]:
    kcal, sug, sat, salt = n.get("energyKcal100g"), n.get("sugars100g"), n.get("saturatedFat100g"), n.get("salt100g")
    assumed = [k for k, v in (("energy", kcal), ("sugars", sug), ("sat", sat), ("salt", salt)) if v is None]
    if len(assumed) == 4:
        return None  # no nutrition figure at all: nothing honest to score
    # A missing figure is never treated as zero: it counts as a typical middling value (ASSUMED_POINTS), so incomplete data cannot flatter a product.
    # The dimension stays "missing" and the score is flagged incomplete with lower confidence.
    if kcal is not None:
        kj = kcal * 4.184
        energy = _pts(kj, [30 * i for i in range(1, 10)]) if drink else _pts(kj, [335 * i for i in range(1, 11)])
    else:
        energy = ASSUMED_POINTS["energy"]
    if sug is not None:
        sugars = _pts(sug, [0.5, 2, 3.5, 5, 6, 7, 8, 9, 10, 11]) if drink else _pts(sug, [3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51])
        if natural_sugar:
            sugars //= 2  # sugars that come from milk / whole fruit (no added sugar in the ingredients) weigh half
    else:
        sugars = ASSUMED_POINTS["sugars"]
    satp = _pts(sat, [float(i) for i in range(1, 11)]) if sat is not None else ASSUMED_POINTS["sat"]
    saltp = _pts(salt, [0.2 * i for i in range(1, 21)]) if salt is not None else ASSUMED_POINTS["salt"]
    neg = energy + sugars + satp + saltp
    fibre = _pts(n.get("fiber100g"), [3.0, 4.1, 5.2, 6.3, 7.4, 8.5]) if use_fibre else 0
    # fruit / vegetable / legume / nut content (% of the product): > 40 % = 1, > 60 % = 2, > 80 % = 5 points
    fv = 0 if fvn is None else (5 if fvn > 80 else 2 if fvn > 60 else 1 if fvn > 40 else 0)
    # Nutri-Score rule kept: when the negative points are high (>= 11) protein only counts if the fruit/veg/nut share is above 80 %
    prot = _pts(n.get("protein100g"), [2.4, 4.8, 7.2, 9.6, 12, 14, 17]) if (use_protein and (neg < 11 or fv == 5 or cheese)) else 0  # cheese: protein always counts (official rule)
    return {"fvn": fv, "fvn_pct": fvn, "energy": energy, "sugars": sugars, "sat": satp, "salt": saltp, "fibre": fibre, "protein": prot, "negative": neg, "positive": fibre + prot + fv, "points": neg - fibre - prot - fv, "assumed": assumed}


# ---- fats, oils, nuts and seeds (Nutri-Score 2023 has its own negative components: energy from saturates and the saturated share of the fat)
GOOD_OILS = re.compile(r"olive-oils|rapeseed-oils|walnut-oils|canola|colza|huile d.olive|huile de colza|huile de noix", re.I)


def nutri_points_fats(n, fvn: Optional[float], use_protein: bool = False) -> Optional[Dict[str, Any]]:
    sat, fat, sug, salt = n.get("saturatedFat100g"), n.get("fat100g"), n.get("sugars100g"), n.get("salt100g")
    if sat is None or fat is None or fat <= 0:
        return None
    e_sat = _pts(sat * 37.0, [120.0 * i for i in range(1, 11)])  # kJ from saturated fat per 100 g
    ratio = _pts(sat / fat * 100.0, [10, 16, 22, 28, 34, 40, 46, 52, 58, 64])
    sugars = _pts(sug, [3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51])
    saltp = _pts(salt, [0.2 * i for i in range(1, 21)])
    fibre = _pts(n.get("fiber100g"), [3.0, 4.1, 5.2, 6.3, 7.4, 8.5])
    fv = 0 if fvn is None else (5 if fvn > 80 else 2 if fvn > 60 else 1 if fvn > 40 else 0)
    neg = e_sat + ratio + sugars + saltp
    prot = _pts(n.get("protein100g"), [2.4, 4.8, 7.2, 9.6, 12, 14, 17]) if (use_protein and (neg < 11 or fv == 5)) else 0
    return {"energy": e_sat, "sugars": sugars, "sat": ratio, "salt": saltp, "fibre": fibre, "protein": prot, "fvn": fv, "fvn_pct": fvn, "negative": neg, "positive": fibre + fv + prot, "points": neg - fibre - fv - prot,
            "sat_ratio": round(sat / fat * 100.0, 1)}


_NQ_FATS = [(-15, 100), (-6, 92), (0, 70), (5, 48), (10, 30), (20, 10), (30, 0)]  # an oil judged on its own scale: olive oil lands around 70, a butter-like fat far lower

def ns_letter(points: int) -> str:
    """Nutri-Score 2023 letter from the points of the general food algorithm (A <= 0, B 1-2, C 3-10, D 11-18, E >= 19)."""
    return "A" if points <= 0 else "B" if points <= 2 else "C" if points <= 10 else "D" if points <= 18 else "E"


# Nutri-Score points -> nutritional quality /100. Deliberately demanding: B ends near 76, C near 48, D near 20, E collapses.
_NQ = [(-15, 100), (0, 92), (2, 76), (10, 48), (18, 20), (30, 4), (40, 0)]


MILK_OR_PLANT = re.compile(r"(?:^|\s)en:(?:milks|plant-based-beverages|plant-milks|dairy-drinks|milk-substitutes|soy-milks|oat-drinks|almond-drinks|rice-drinks)\b")
# Drinks (Nutri-Score 2023 is stricter for them: only water is an A, 1 point is a B, 2-5 a C, 6-9 a D, 10+ an E)
_NQ_DRINK = [(-15, 100), (0, 90), (1, 72), (2, 58), (5, 46), (9, 24), (12, 8), (18, 0)]


def nq_from_points(points: float, drink: bool = False) -> float:
    return interp(points, _NQ_DRINK if drink else _NQ)


FVN_WORDS = re.compile(r"^(noix|noisette|amande|cacahu[eè]te|pistache|coco|noix de coco|fruits?|l[ée]gumes?|pomme|poire|banane|tomate|carotte|lentille|pois chiche|haricot|dattes?|raisin|abricot|figue|nuts?|almonds?|hazelnuts?|coconut|peanuts?|lentils?|chickpeas?|beans?)\b", re.I)


# typical vegetable / fruit content of a category, used only when neither the database nor the ingredient list says (always shown as an estimate)
WHOLE_FRUIT = re.compile(r"(?:^|\s)en:(?:dried-fruits|dates|raisins|prunes|dried-apricots|dried-figs|dried-bananas|fresh-fruits|dried-cranberries|dried-mangoes)\b")  # whole fruit, dried or fresh: its sugar is the fruit's own
FVN_PRIOR = [(WHOLE_FRUIT, 80.0), (re.compile(r"(?:^|\s)en:(?:pulses|legume-seeds|dried-legumes|dried-beans|lentils|chickpeas|dried-peas|split-peas|dried-flageolet-green-beans)\b"), 100.0), (re.compile(r"tomato-sauces|pasta-sauces|tomatoes-and-their-products"), 70.0), (re.compile(r"vegetable-soups|veloutes"), 45.0), (re.compile(r"compotes|fruit-purees"), 80.0)]


def fvn_estimate(cats: List[str]) -> Optional[float]:
    t = " ".join(cats)
    return next((v for rx, v in FVN_PRIOR if rx.search(t)), None)


def fvn_share(raw, ing) -> Optional[float]:
    """% of fruit / vegetable / legume / nut: the database estimate when present, else 100 for a single-ingredient fruit / vegetable / nut / legume product."""
    v = (raw or {}).get("fvn")
    if v is not None:
        return v
    parts = [x.strip() for x in re.split(r"[,;.]", re.sub(r"\([^)]*\)", "", ing or "")) if x.strip()]
    return 100.0 if len(parts) == 1 and FVN_WORDS.search(parts[0]) else None


# ---------------------------------------------------------------- dimensions (display scores are derived from the same points, so what you see explains the total)
def strict(pts: int, mx: int, frac: float = .6) -> float:
    """A negative nutrient's score from its points: 0 points = 100, frac*max points = 0."""
    return max(0.0, 100.0 - 100.0 * pts / (mx * frac))


def d_fat(n, pts, raw, pid):
    sat, fat, trans = n.get("saturatedFat100g"), n.get("fat100g"), raw.get("trans")
    if sat is None:
        return None, {"missing": "saturatedFat"}
    parts = [(.5, strict(pts["sat"], 10), "sat")]
    if trans is not None:
        parts.append((.3, interp(trans, [(0, 100), (0.1, 90), (0.5, 40), (1.0, 0)]), "trans"))
    if fat is not None and pid != "oils_fats":  # total fat is contextual: an oil is not penalised for being fat
        parts.append((.1, interp(fat, banded(3.0, 17.5)), "total"))
    if fat is not None and fat >= 3:
        parts.append((.1, max(0.0, min(100.0, (fat - sat) / fat * 100.0)), "unsat"))
    w = sum(x[0] for x in parts)
    return sum(x[0] * x[1] for x in parts) / w, {"sat": sat, "total": fat, "trans": trans, "parts": [{"k": k, "score": round(sc)} for _, sc, k in parts]}


def d_sugar(n, pts, ing, raw):
    total = n.get("sugars100g")
    if total is None:
        return None, {"missing": "sugars"}
    prof = sugar_profile(ing, total)
    mx = 10 if pts.get("drink") else 15
    base = strict(pts["sugars"], mx)
    added = raw.get("added")
    if added is not None:
        score, basis = .6 * strict(_pts(added, [3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51]), 15) + .4 * base, "added_known"
    elif prof["kind"] == "none":
        score, basis = 100.0, "none"
    else:
        score, basis = base, {"natural": "natural", "added": "added_inferred", "mixed": "added_inferred"}.get(prof["kind"], "unknown")
    return score, {"total": round(total, 1), "sugar": prof, "basis": basis}


def d_salt(n, pts):
    v = n.get("salt100g")
    return (None, {"missing": "salt"}) if v is None else (strict(pts["salt"], 20, .6), {"value": round(v, 2)})


def d_energy(n, pts, drink):
    v = n.get("energyKcal100g")
    return (None, {"missing": "energy"}) if v is None else (strict(pts["energy"], 9 if drink else 10, .8), {"kcal": round(v)})


def d_protein(n):
    v = n.get("protein100g")
    return (None, {"missing": "protein"}) if v is None else (interp(v, PROTEIN), {"value": round(v, 1)})


def d_fibre(n):
    v = n.get("fiber100g")
    return (None, {"missing": "fibre"}) if v is None else (interp(v, FIBRE), {"value": round(v, 1)})


def d_plant(v: Optional[float], estimated: bool):
    if v is None:
        return None, {"missing": "plant"}
    return interp(v, [(0, 20), (40, 50), (60, 75), (80, 100)]), {"value": round(v), "estimated": estimated}


def d_micro(micro):
    if not micro:
        return None, {"missing": "micronutrients"}
    rich = [m for m in micro if m.get("nrv_pct", 0) >= 30]
    src = [m for m in micro if 15 <= m.get("nrv_pct", 0) < 30]
    return min(100.0, 30 + 20 * len(rich) + 10 * len(src)), {"rich": [m["key"] for m in rich], "source": [m["key"] for m in src]}


def d_additives(adds: List[str], strict: bool = False):
    items, pen = [], 0
    pens = ADD_PENALTY_STRICT if strict else ADD_PENALTY
    for a in adds:
        lvl, known = additive_level(a, strict)
        info = additive_info(a)
        items.append({"code": a.lower().replace("en:", ""), "level": lvl, "balanced": additive_level(a, False)[0], "known": known, "name": info["name"], "note": info["why"] or ADD_NOTE[lvl], "use": info["use"], "found": info["found"]})
        pen += pens[lvl]
    return max(0.0, 100.0 - pen), {"items": items, "count": len(items)}


def d_ingredients(ing, adds):
    if not ing:
        return None, {"missing": "ingredients"}
    low = ing.lower()
    parts = [x for x in re.split(r"[,;]", re.sub(r"\([^)]*\)", "", low)) if x.strip()]
    n = len(parts)
    score = 65.0 - min(30, max(0, n - 8) * 2) + (10 if n <= 5 else 0)
    notes = []
    if re.search(r"complet|wholegrain|whole grain|intégral|integral", low):
        score += 15; notes.append("wholegrain")
    if re.search(r"huile de palme|palm", low):
        score -= 12; notes.append("palm_oil")
    if re.search(r"hydrog[eé]n", low):
        score -= 18; notes.append("hydrogenated")
    if re.search(r"ar[oô]mes?\b|flavou?rings?", low):
        score -= 8; notes.append("flavourings")
    if re.search(r"sirop de glucose|glucose-fructose|glucose syrup|sirop de fructose", low):
        score -= 12; notes.append("glucose_syrup")
    if re.search(r"\b(sucre|sugar|saccharose)\b", low.split(",")[0]):
        score -= 10; notes.append("sugar_first")  # sugar is the first (largest) ingredient
    return max(0.0, min(100.0, score)), {"count": n, "notes": notes}


# ---------------------------------------------------------------- scales: the real amount placed on labelled zones (what is excellent, what is too much)
TIERS = [("excellent", "g"), ("good", "g2"), ("average", "y"), ("poor", "w"), ("bad", "b")]
# less-is-better cut points (upper bound of excellent, good, average, poor; above = bad) per 100 g / 100 ml, aligned on Nutri-Score point thresholds
LESS = {"sat": ((1, 3, 5, 7), 10, "g"), "salt": ((0.2, 0.6, 1.2, 2.0), 3, "g"),
        "sugar_solid": ((3.4, 10, 17, 27), 45, "g"), "sugar_liquid": ((0.5, 3.5, 7, 10), 15, "g"),
        "energy_solid": ((80, 200, 350, 500), 800, "kcal"), "energy_liquid": ((10, 25, 45, 65), 100, "kcal")}
# more-is-better: lower bounds of average, good, excellent
MORE = {"fibre": ((0.9, 3.0, 8.5), 12, "g"), "protein": ((0.8, 3.0, 8.0), 20, "g"), "plant": ((20.0, 40.0, 80.0), 100, "%")}
LESS["satratio"] = ((10.0, 16.0, 28.0, 46.0), 80, "%")


def scale_of(key: str, value: Optional[float], drink: bool, better: str, relax: float = 1.0) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if better == "less":
        cuts, mx, unit = LESS[key]
        cuts, mx = tuple(c * relax for c in cuts), mx * relax
        edges = [0.0] + list(cuts) + [mx]
        zones = [{"from": edges[i], "to": edges[i + 1], "tier": TIERS[i][0], "tone": TIERS[i][1]} for i in range(5)]
        zone = next((z for z in zones if value <= z["to"]), zones[-1]) if value <= cuts[-1] else zones[-1]
    else:
        cuts, mx, unit = MORE[key]
        edges = [0.0] + list(cuts) + [mx]
        names = [("poor", "w"), ("average", "y"), ("good", "g2"), ("excellent", "g")]
        zones = [{"from": edges[i], "to": edges[i + 1], "tier": names[i][0], "tone": names[i][1]} for i in range(4)]
        zone = zones[0] if value < cuts[0] else zones[1] if value < cuts[1] else zones[2] if value < cuts[2] else zones[3]
    return {"value": round(value, 1), "unit": unit, "max": mx, "better": better, "zones": zones, "tier": zone["tier"], "tone": zone["tone"]}


# ---------------------------------------------------------------- warnings (never averaged away)
def flags_of(n, liquid, sugar_detail, raw, adds, nova, strict: bool = False) -> List[Dict[str, str]]:
    b = BANDS["liquid" if liquid else "solid"]
    out: List[Dict[str, str]] = []
    if (n.get("salt100g") or 0) > b["salt"][1]:
        out.append({"key": "high_salt", "level": "bad"})
    kind = (sugar_detail or {}).get("sugar", {}).get("kind")
    sug = n.get("sugars100g") or 0
    if sug > b["sugar"][1] and kind in ("added", "mixed", "unknown"):
        out.append({"key": "high_added_sugar" if kind != "unknown" else "high_sugar", "level": "bad"})
    elif sug > b["sugar"][1]:
        out.append({"key": "high_sugar_natural", "level": "warn"})
    elif kind in ("added", "mixed") and sug > b["sugar"][0] * 2:
        out.append({"key": "added_sugar", "level": "warn"})
    if (n.get("saturatedFat100g") or 0) > b["sat"][1]:
        out.append({"key": "high_sat_fat", "level": "bad"})
    if (raw.get("trans") or 0) >= 0.5:
        out.append({"key": "trans_fat", "level": "bad"})
    if (n.get("energyKcal100g") or 0) > (40 if liquid else 400):
        out.append({"key": "high_energy", "level": "warn"})
    if any(additive_level(a, strict)[0] == "D" for a in adds):
        out.append({"key": "additive_d", "level": "bad"})
    if nova == 4:
        out.append({"key": "ultra_processed", "level": "warn"})
    return out


# ---------------------------------------------------------------- main
def quality(p: Dict[str, Any], organic: bool = False, raw: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    n = p["nutriments"]
    cats = p.get("categories") or []
    pid = profile_of(cats)
    drink = is_liquid(cats, p)
    extra = raw or {}
    strict = bool(extra.get("strict"))
    organic = bool(organic or p.get("organic"))
    ing = p.get("ingredientsText")
    adds = p.get("additives") or []
    weights = PROFILES[pid]
    whole_fruit = bool(WHOLE_FRUIT.search(" ".join(cats))) and not drink
    ing_s = ing or ("fruits" if whole_fruit else None)  # no ingredient list on a whole-fruit product (dates, raisins...): its sugar is the fruit's own, not added
    natural = bool(ing_s) and not ADDED_SUGAR.search(ing_s) and (n.get("sugars100g") or 0) > 0
    # protein / fibre count only where they mean something for the category (weight 0 = irrelevant)
    fvn = fvn_share(extra, ing)
    fvn_est = False
    if fvn is None and pid in PLANT_PROFILES:
        fvn = fvn_estimate(cats)
        fvn_est = fvn is not None
    fats_path = pid in ("oils_fats", "nuts_seeds") and n.get("fat100g")
    if fats_path and pid == "oils_fats" and (GOOD_OILS.search(" ".join(cats)) or GOOD_OILS.search(ing or "")):
        fvn, fvn_est = 100.0, False  # olive / rapeseed / walnut oil counts as a favourable plant component
    pts = (nutri_points_fats(n, fvn, weights["protein"] > 0) if fats_path else None) or nutri_points(n, drink, natural, weights["protein"] > 0, weights["fibre"] > 0, fvn)
    if pts is None and PLAIN_INFUSION.search(" ".join(cats)) and not (ing and ADDED_SUGAR.search(ing)):
        # Plain tea, herbal infusion, coffee or water: open data often has no nutrition table because there is nothing in the cup. Dry herbs
        # prepared as a drink are taken as zero for every nutrient (flagged as assumed), so the score rests on ingredients and additives.
        n = {**n, **{k: (n.get(k) or 0) for k in ("energyKcal100g", "sugars100g", "saturatedFat100g", "salt100g")}}
        drink = True
        pts = nutri_points(n, True, False, weights["protein"] > 0, weights["fibre"] > 0, fvn)
        if pts:
            pts["assumed"] = ["energy", "sugars", "sat", "salt"]
    if pts is None:
        return None  # not enough nutrition data for an honest score
    pts["drink"] = drink
    dscore = {"fat": d_fat(n, pts, extra, pid), "sugar": d_sugar(n, pts, ing_s, extra), "salt": d_salt(n, pts), "energy": d_energy(n, pts, drink),
              "protein": d_protein(n), "fibre": d_fibre(n), "plant": d_plant(fvn, fvn_est), "micro": d_micro(p.get("micronutrients")), "additives": d_additives(adds, strict), "ingredients": d_ingredients(ing, adds)}
    # 1. nutritional quality: Nutri-Score points (negatives minus the positives that are relevant here), then safeguards
    nq = interp(pts["points"], _NQ_FATS) if "sat_ratio" in pts else nq_from_points(pts["points"], drink and not MILK_OR_PLANT.search(" ".join(cats)))
    if drink and "sat_ratio" not in pts and (n.get("sugars100g") or 0) <= .5 and (n.get("energyKcal100g") or 0) <= 4 and (n.get("saturatedFat100g") or 0) <= .1 and (n.get("salt100g") or 0) <= .1:
        nq = 100.0  # water, plain tea, coffee: nothing to penalise, so the full nutrition mark
    # 2. ingredient quality: additives + ingredient composition (profile weights, renormalised)
    iw = {k: weights[k] for k in ("additives", "ingredients") if weights[k] > 0 and dscore[k][0] is not None}
    iq = sum(weights[k] * dscore[k][0] for k in iw) / sum(iw.values()) if iw else None
    sugar_detail = dscore["sugar"][1]
    flags = flags_of(n, drink, sugar_detail, extra, adds, p.get("novaGroup"), strict)
    if "sat_ratio" in pts:
        flags = [f for f in flags if f["key"] not in ("high_sat_fat", "high_energy")] + ([{"key": "high_sat_ratio", "level": "warn"}] if pts["sat_ratio"] > 46 else [])
    if whole_fruit:
        flags = [f for f in flags if f["key"] != "high_energy"]
    bad = [f for f in flags if f["level"] == "bad"]
    # 3. overall = 80 % nutritional + 20 % ingredient, with safeguards: good ingredients cannot lift the total far above the nutrition,
    #    and serious weaknesses cap it whatever else the product does well
    total = nq if iq is None else .8 * nq + .2 * iq
    if strict:  # Yuka-like: 60 % nutrition + 30 % additives + 10 % organic (a flagged additive pulls its 30 points down; no ingredient-quality term)
        total = .6 * nq + .3 * dscore["additives"][0] + (10 if organic else 0)
    caps = []
    total2 = total if strict else min(total, nq + 8)
    if total2 < total:
        caps.append("ingredients_cannot_mask_nutrition")
    if any(f["key"] == "additive_d" for f in flags):
        total2 = min(total2, 49); caps.append("additive_d")
    if strict and not drink and "sat_ratio" not in pts and ns_letter(pts["points"]) in ("D", "E"):
        total2 = min(total2, 49); caps.append("nutriscore_d_e")  # Yuka: a product rated D or E cannot exceed 49/100
    if len(bad) >= 2:
        total2 = min(total2, 45); caps.append("two_serious_weaknesses")
    elif len(bad) == 1:
        total2 = min(total2, 64); caps.append("serious_weakness")
    total = round(max(0.0, total2))
    if strict:
        parts = [{"key": "nutrition", "got": round(.6 * nq, 1), "of": 60}, {"key": "additives", "got": round(.3 * dscore["additives"][0], 1), "of": 30}, {"key": "organic", "got": 10 if organic else 0, "of": 10}]
    else:
        parts = [{"key": "nutrition", "got": round(.8 * nq, 1), "of": 80}, {"key": "ingredients", "got": round(.2 * (iq if iq is not None else nq), 1), "of": 20}]
    uncapped = round(sum(x["got"] for x in parts))
    # dimension rows
    rel = {k: w for k, w in weights.items() if w > 0}
    dims = []
    for k in DIMS:
        sc, det = dscore[k]
        relevant = (weights.get(k, 0) > 0) or k == "energy" or (k == "plant" and pid in PLANT_PROFILES)
        if k == "energy" and pid == "oils_fats":
            relevant = False
        if k == "micro" and sc is None:
            relevant = False  # vitamin/mineral data is almost never on the label: its absence says nothing about this product
        sc_map = {"fat": ("sat", n.get("saturatedFat100g"), "less"), "sugar": ("sugar_liquid" if drink else "sugar_solid", n.get("sugars100g"), "less"),
                  "salt": ("salt", n.get("salt100g"), "less"), "energy": ("energy_liquid" if drink else "energy_solid", n.get("energyKcal100g"), "less"),
                  "protein": ("protein", n.get("protein100g"), "more"), "fibre": ("fibre", n.get("fiber100g"), "more"), "plant": ("plant", fvn, "more")}
        relax = (1.7 if k == "energy" else 2.4 if k == "sugar" else 1.0) if whole_fruit else 1.0  # whole fruit: calories and natural sugar weigh less (Yuka: low impact)
        scale = scale_of(sc_map[k][0], sc_map[k][1], drink, sc_map[k][2], relax) if k in sc_map else None
        if k == "fat" and "sat_ratio" in pts:
            scale = scale_of("satratio", pts["sat_ratio"], drink, "less")
        if not relevant:
            scale = None
        if scale and k == "plant":
            scale["estimated"] = fvn_est
        dims.append({"key": k, "scale": scale, "group": "ingredients" if k in ("additives", "ingredients") else "nutrition", "score": None if sc is None else round(sc), "tone": None if sc is None else _tone(sc),
                     "relevant": relevant, "missing": relevant and sc is None, "detail": det,
                     "points": pts.get(k if k != "sat" else "sat") if k in ("energy", "sugar", "salt", "protein", "fibre") else None})
    missing = [d["key"] for d in dims if d["missing"]]
    have_w = sum(w for k, w in rel.items() if dscore[k][0] is not None)
    conf = 100 * have_w / sum(rel.values()) if rel else 0
    doubts = []
    if not p.get("dataQuality", {}).get("nutritionComplete", True):
        conf -= 10; doubts.append("nutrition_incomplete")
    if not ing:
        conf -= 15; doubts.append("no_ingredients")
    elif len([x for x in re.split(r"[,;]", ing) if x.strip()]) <= 2 and pid in ("snacks_confectionery", "ready_meals", "bread_bakery", "sauces", "grains_cereals"):
        conf -= 10; doubts.append("ingredients_incomplete")
    if p.get("novaEstimated"):
        conf -= 5; doubts.append("nova_estimated")
    if fvn_est:
        conf -= 5; doubts.append("plant_estimated")
    if sugar_detail.get("basis") in ("added_inferred", "unknown", "natural"):
        conf -= 5; doubts.append("added_sugar_inferred")
    if any(not i["known"] for i in dscore["additives"][1]["items"]):
        conf -= 5; doubts.append("additive_unknown")
    conf = max(10, min(100, round(conf)))
    band = _band(total)
    return {"version": VERSION, "mode": "strict" if strict else "balanced", "organic": organic, "profile": pid, "liquid": drink, "total": total, "band": band["key"], "tone": band["tone"],
            "nutritional": {"score": round(nq), "tone": _tone(nq), "points": pts["points"], "negative": pts["negative"], "positive": pts["positive"]},
            "ingredient": None if iq is None else {"score": round(iq), "tone": _tone(iq)},
            "processing": {"nova": p.get("novaGroup"), "estimated": bool(p.get("novaEstimated"))},
            "caps": caps, "parts": parts, "uncapped": uncapped, "dimensions": dims, "flags": flags,
            "confidence": {"pct": conf, "level": "high" if conf >= 80 else "medium" if conf >= 55 else "low", "missing": missing, "doubts": doubts},
            "incomplete": any(k not in NOT_ON_LABELS and (k not in ("fibre", "protein") or weights.get(k, 0) >= .2) for k in missing) or bool(pts.get("assumed")), "nova": {"group": p.get("novaGroup"), "estimated": bool(p.get("novaEstimated"))},
            "sugar": sugar_detail.get("sugar"), "additives": {"score": round(dscore["additives"][0]), "items": dscore["additives"][1]["items"], "count": dscore["additives"][1]["count"]},
            "calculatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}
