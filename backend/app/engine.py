"""Choice Engine: deterministic, explainable. Candidates -> hard restrictions -> completeness -> rank by priority order -> explain."""
import math
from typing import Any, Dict, List, Optional, Tuple

from . import value_index, taxonomy
from .i18n import tr
from .products import NS_RANK

# key -> (nutriment field, direction (+1 more is better), tolerance in g, "matches" threshold, "partly" threshold, label)
PRIORITIES = {
    "protein": ("protein100g", 1, 1.0, 10.0, 5.0, "More protein"),
    "sugars": ("sugars100g", -1, 1.0, 5.0, 10.0, "Less total sugars"),
    "fibre": ("fiber100g", 1, 0.5, 6.0, 3.0, "More fibre"),
    "salt": ("salt100g", -1, 0.1, 0.3, 1.0, "Less salt"),
    "saturated_fat": ("saturatedFat100g", -1, 0.5, 1.5, 5.0, "Less saturated fat"),
    "overall": (None, 1, 0.0, 0, 0, "Better Nutri-Score"),
    "value": (None, 1, 0.5, 0, 0, "Best nutrition-price value"),  # tolerance: g of protein/fibre per euro, or cents per 100 g
    "budget": (None, -1, 5.0, 0, 0, "Save money"),          # tolerance: cents per 100 g
    "additives": (None, -1, 0.5, 0, 0, "Fewer additives"),  # count of listed additives
}
DIFF_KEY = {"protein": "protein_difference_per_100g", "sugars": "sugars_difference_per_100g", "fibre": "fibre_difference_per_100g",
            "salt": "salt_difference_per_100g", "saturated_fat": "saturated_fat_difference_per_100g", "overall": "nutri_score_steps",
            "budget": "price_difference_cents_per_100g", "value": "value_difference", "additives": "additives_difference"}


import re

_STOP = {"the", "and", "les", "des", "aux", "avec", "sans", "bio", "pot", "pots", "pack", "lot"}


def _tok(name: str, brand: Optional[str] = None) -> set:
    b = {w for w in re.split(r"[^a-zà-ÿ0-9]+", (brand or "").lower()) if w}
    return {w for w in re.split(r"[^a-zà-ÿ]+", (name or "").lower()) if len(w) > 2 and w not in _STOP and w not in b}


def deep_similarity(o: Dict[str, Any], c: Dict[str, Any]) -> float:
    """0..1 'is this really the same kind of product?'. Category path (specific tags weigh more), name words, macro profile, pack size."""
    ot, ct = o["categories"], c["categories"]
    w = {t: 1 + i / max(1, len(set(ot) | set(ct))) for i, t in enumerate(dict.fromkeys(ot + ct))}
    inter, union = sum(w[t] for t in set(ot) & set(ct)), sum(w[t] for t in set(ot) | set(ct))
    cat = inter / union if union else 0.0
    a, b = _tok(o["name"], o["brand"]), _tok(c["name"], c["brand"])
    name = len(a & b) / len(a | b) if (a | b) else 0.0
    dists = []
    for f, scale in (("energyKcal100g", 400.0), ("fat100g", 30.0), ("carbohydrates100g", 60.0), ("protein100g", 25.0)):
        x, y = o["nutriments"].get(f), c["nutriments"].get(f)
        if x is not None and y is not None:
            dists.append(min(1.0, abs(x - y) / scale))
    nutr = 1 - sum(dists) / len(dists) if dists else 0.5
    oq, cq = o.get("quantity"), c.get("quantity")
    size = min(oq["amount"], cq["amount"]) / max(oq["amount"], cq["amount"]) if (oq and cq and oq["unit"] == cq["unit"]) else 0.5
    return round(0.45 * cat + 0.20 * name + 0.25 * nutr + 0.10 * size, 3)


def type_filter(orig: Dict[str, Any], peers: List[Dict[str, Any]], min_same: int = 4, parent_floor: float = 0.6) -> List[Dict[str, Any]]:
    """Keep products of the same TYPE. The most specific category of the scanned product (breadsticks, not 'breads') decides: candidates that carry it come first and,
    when there are enough of them, are the only ones. Otherwise products that share only the parent category are admitted, but only if they are very similar overall,
    so breadsticks never suggest burger buns or sliced bread."""
    tags = orig.get("categories") or []
    if len(tags) < 2:
        return peers
    leaf, parent = tags[-1], tags[-2]
    same = [c for c in peers if leaf in (c.get("categories") or [])]
    if len(same) >= min_same:
        return same
    near = [c for c in peers if c not in same and parent in (c.get("categories") or []) and deep_similarity(orig, c) >= parent_floor]
    return same + near


def variant_key(p: Dict[str, Any]) -> str:
    """Same product in another pack size shares this key."""
    return (p.get("brand") or "").lower().split(",")[0].strip() + "|" + " ".join(sorted(_tok(p["name"], p.get("brand"))))


def dominated(items: List[Dict[str, Any]], keys, min_common: int = 2) -> List[bool]:
    """True for items that another item beats or ties on every key (larger is better) and strictly beats on one.
    Only keys known for both items are compared, and at least `min_common` of them: missing data never makes an item look dominated."""
    vec = [[k(i) for k in keys] for i in items]

    def beats(b, a):
        common = [j for j in range(len(a)) if a[j] is not None and b[j] is not None]
        return len(common) >= min_common and all(b[j] >= a[j] for j in common) and any(b[j] > a[j] for j in common)
    return [any(beats(b, a) for b in vec if b is not a) for a in vec]


def restriction_status(p: Dict[str, Any], allergens: List[str], diet: Optional[str]) -> str:
    """'ok' | 'conflict' | 'unverified'. Missing data is never treated as safe."""
    for a in allergens:
        if a in p["allergens"] or a in p["traces"]:
            return "conflict"
        if not p["ingredientsText"]:
            return "unverified"
    an = p["analysis"]
    if diet == "vegan":
        if "en:non-vegan" in an:
            return "conflict"
        if "en:vegan" not in an:
            return "unverified"
    if diet == "vegetarian":
        if "en:non-vegetarian" in an:
            return "conflict"
        if "en:vegetarian" not in an and "en:vegan" not in an:
            return "unverified"
    return "ok"


NAME_KEY = {"protein": "n_protein", "sugars": "n_sugars", "fibre": "n_fibre", "salt": "n_salt", "saturated_fat": "n_sat"}


def fit(p: Dict[str, Any], priorities: List[str], allergens: List[str], diet: Optional[str], lang: str = "fr") -> List[Dict[str, str]]:
    out = []
    for k in priorities:
        if k not in PRIORITIES or PRIORITIES[k][0] is None:
            continue
        field, d, _, match, part, label = PRIORITIES[k]
        v = p["nutriments"].get(field)
        if v is None:
            out.append({"priority": k, "status": "unknown", "text": tr(lang, "no_value")})
            continue
        good = v >= match if d > 0 else v <= match
        partly = v >= part if d > 0 else v <= part
        out.append({"priority": k, "status": "match" if good else "partial" if partly else "no_match", "text": tr(lang, "per100", v=f"{v:.1f}")})
    for a in allergens:
        if a in p["allergens"]:
            out.append({"priority": "allergen:" + a, "status": "conflict", "text": tr(lang, "allergen_declared")})
        elif a in p["traces"]:
            out.append({"priority": "allergen:" + a, "status": "conflict", "text": tr(lang, "allergen_traces")})
        elif not p["ingredientsText"]:
            out.append({"priority": "allergen:" + a, "status": "unknown", "text": tr(lang, "allergen_unknown")})
        else:
            out.append({"priority": "allergen:" + a, "status": "match", "text": tr(lang, "allergen_ok")})
    if diet in ("vegan", "vegetarian"):
        an = p["analysis"]
        bad = ("en:non-vegan" in an) if diet == "vegan" else ("en:non-vegetarian" in an)
        ok = ("en:vegan" in an) if diet == "vegan" else ("en:vegetarian" in an or "en:vegan" in an)
        out.append({"priority": "diet:" + diet, "status": "conflict" if bad else "match" if ok else "unknown", "text": tr(lang, "diet_conflict" if bad else "diet_ok" if ok else "diet_unknown")})
    return out


def per_euro(nutrients: Dict[str, Any], field: str, price100: Optional[float]) -> Optional[float]:
    """Grams of a nutrient per euro spent (price100 = cents per 100 g). None if either is unknown."""
    v = nutrients.get(field)
    return None if v is None or not price100 or price100 <= 0 else v / (price100 / 100.0)


def value_basis(priorities: List[str]) -> str:
    """Transparent definition of 'best nutrition-price value' for the user's chosen priorities."""
    if "fibre" in priorities and "protein" not in priorities:
        return "fibre"
    if "protein" in priorities or not any(p in priorities for p in ("sugars", "overall", "additives", "salt", "saturated_fat")):
        return "protein"
    return "floor"  # cheapest among products that are not worse on the chosen priorities and not worse on Nutri-Score


def _diff(orig, cand, k, prices=None, orig_price=None, priorities=None) -> Optional[float]:
    """Positive = the candidate is better on priority k. None = cannot be compared (data missing)."""
    if k == "overall":
        a, b = orig["nutriScore"], cand["nutriScore"]
        return None if not a or not b else float(NS_RANK[b] - NS_RANK[a])
    if k == "value":
        p = (prices or {}).get(cand["barcode"])
        if p is None or orig_price is None:
            return None
        basis = value_basis(priorities or [])
        if basis in ("protein", "fibre"):
            f = "protein100g" if basis == "protein" else "fiber100g"
            a, b = per_euro(orig["nutriments"], f, orig_price), per_euro(cand["nutriments"], f, p)
            return None if a is None or b is None else b - a
        # floor: price saving, but only if nutritionally not worse
        for other in (priorities or []):
            if other in ("value", "budget"):
                continue
            od = _diff(orig, cand, other, prices, orig_price, None)
            if od is not None and od < 0:
                return -1.0
        a, b = orig["nutriScore"], cand["nutriScore"]
        if a and b and NS_RANK[b] < NS_RANK[a]:
            return -1.0
        return (orig_price - p) / 100.0
    if k == "budget":
        p = (prices or {}).get(cand["barcode"])
        return None if p is None or orig_price is None else orig_price - p
    if k == "additives":
        if not orig["ingredientsText"] or not cand["ingredientsText"]:
            return None
        return float(len(orig["additives"]) - len(cand["additives"]))
    field, d = PRIORITIES[k][0], PRIORITIES[k][1]
    x, y = orig["nutriments"].get(field), cand["nutriments"].get(field)
    return None if x is None or y is None else (y - x) * d


def value_card(orig, cand, orig_price, price) -> Optional[Dict[str, Any]]:
    """Plain numbers behind 'value': price per 100 g and grams of protein / fibre per euro, for both products."""
    if price is None:
        return None
    return {"orig_price_per_100_cents": orig_price, "price_per_100_cents": price,
            "saving_per_100_cents": None if orig_price is None else round(orig_price - price, 1),
            "protein_g_per_euro": {"orig": None if orig_price is None else per_euro(orig["nutriments"], "protein100g", orig_price), "alt": per_euro(cand["nutriments"], "protein100g", price)},
            "fibre_g_per_euro": {"orig": None if orig_price is None else per_euro(orig["nutriments"], "fiber100g", orig_price), "alt": per_euro(cand["nutriments"], "fiber100g", price)}}


def _tradeoffs(o, c, sim, lang="fr", price_unknown=False) -> List[str]:
    a, b, T = o["nutriments"], c["nutriments"], []
    def more(f, thr, key):
        if a.get(f) is not None and b.get(f) is not None and b[f] - a[f] >= thr: T.append(tr(lang, key, d=f"{b[f]-a[f]:.1f}"))
    def less(f, thr, key):
        if a.get(f) is not None and b.get(f) is not None and a[f] - b[f] >= thr: T.append(tr(lang, key, d=f"{a[f]-b[f]:.1f}"))
    more("sugars100g", 3, "tr_more_sugars"); more("saturatedFat100g", 1.5, "tr_more_sat"); more("salt100g", 0.3, "tr_more_salt")
    less("protein100g", 2, "tr_less_prot"); less("fiber100g", 1.5, "tr_less_fibre")
    if a["energyKcal100g"] is not None and b["energyKcal100g"] is not None and b["energyKcal100g"] - a["energyKcal100g"] >= 50:
        T.append(tr(lang, "tr_more_kcal", d=f"{b['energyKcal100g']-a['energyKcal100g']:.0f}"))
    on, cn = o.get("novaGroup"), c.get("novaGroup")
    if on and cn and cn > on:
        T.append(tr(lang, "tr_nova", a=on, b=cn))
    if price_unknown:
        T.append(tr(lang, "tr_price_unknown"))
    vd = (c.get("substitution") or {}).get("variant_diff")
    if vd:
        T.append(tr(lang, "tr_variant", a=tr(lang, "var_" + vd[0]), b=tr(lang, "var_" + vd[1])))
    if sim < 0.8 and ((c.get("substitution") or {}).get("level") or 1) > 2:
        T.append(tr(lang, "tr_diff_type"))
    return T


def choose(orig: Dict[str, Any], peers: List[Dict[str, Any]], priorities: List[str], allergens: List[str], diet: Optional[str],
           mode: str = "similar", limit: int = 5, prices: Optional[Dict[str, float]] = None,
           orig_price: Optional[float] = None, lang: str = "fr") -> Dict[str, Any]:
    ex = {"conflict": 0, "unverified": 0, "incomplete": 0, "not_better": 0, "dissimilar": 0, "not_in_france": 0, "france_unknown": 0, "not_substitute": 0, "low_confidence": 0, "level_3_4_rejected": 0}
    funnel = {"raw_candidates_retrieved": len(peers), "usable_product_data": 0, "confirmed_sold_in_france": 0,
              "france_unknown": 0, "passing_allergens": 0, "passing_compatibility": 0, "with_sufficient_nutrition": 0,
              "with_verified_prices": 0, "by_substitution_level": {str(level): 0 for level in range(1, 5)}}
    found = []
    for c in peers:
        if c["barcode"] == orig["barcode"]:
            continue
        if {"nutrition_implausible", "sugars_exceed_carbohydrates"} & set(data_issues(c)):   # the same hard rule as prefilter(): no path may recommend impossible data
            continue
        funnel["usable_product_data"] += 1
        if c.get("soldInFrance") is not True:  # recommend only what can be bought in France; unknown availability is not assumed
            ex["not_in_france"] += 1
            if c.get("soldInFrance") is None:
                ex["france_unknown"] += 1   # of those, how many only lack country data (as opposed to being listed as sold elsewhere)
            continue
        funnel["confirmed_sold_in_france"] += 1
        st = restriction_status(c, allergens, diet)
        if st != "ok":
            ex[st] += 1
            continue
        funnel["passing_allergens"] += 1
        substitution = c.get("substitution") or taxonomy.substitution(orig, c)
        if substitution is None:
            ex["not_substitute"] += 1
            continue
        c = {**c, "substitution": substitution}
        funnel["passing_compatibility"] += 1
        level = substitution.get("level")
        confidence = substitution.get("confidence", "none")

        # HARD GATE: Reject low-confidence classifications from strict rankings
        if confidence in ("none", "low") and mode != "similar":
            ex["low_confidence"] += 1
            continue

        # HARD GATE: Level 3/4 products only enter closest tab, not price/quality/value rankings
        if level and level >= 3 and mode != "similar":
            ex["level_3_4_rejected"] += 1
            continue

        if level in funnel["by_substitution_level"]:
            funnel["by_substitution_level"][str(level)] += 1
        d = {k: _diff(orig, c, k, prices, orig_price, priorities) for k in priorities}
        for k in priorities[1:]:
            if k in ("budget", "value") and d[k] is None:
                d[k] = 0.0  # price unknown for a secondary priority: keep the product, say so in the trade-offs
        if any(v is None for v in d.values()):
            # Closest alternatives are discovery results, not improvement
            # results. Keep a compatible product with incomplete nutrition and
            # expose unknown comparisons; quality/value modes still require the
            # data needed by their ranking.
            if mode != "similar":
                ex["incomplete"] += 1
                continue
            ex["incomplete"] += 1
        else:
            funnel["with_sufficient_nutrition"] += 1
        if prices and c.get("barcode") in prices:
            funnel["with_verified_prices"] += 1
        # Discovery is independent from improvement. A closest substitute remains useful
        # even when it does not beat the scanned product on the user's first priority.
        first = priorities[0] if priorities else None
        if first and mode != "similar" and not d[first] > PRIORITIES[first][2]:
            ex["not_better"] += 1
            continue
        sim = deep_similarity(orig, c)
        if mode == "similar" and sim < 0.45 and (substitution.get("level") or 4) > 2:   # a confirmed same-type product is not dropped for having different words, nutrition or pack size
            ex["dissimilar"] += 1
            continue
        rank = [round((d[k] or 0) / (PRIORITIES[k][2] or 1)) for k in priorities]
        found.append((rank, sim, c, d))
    found.sort(key=lambda x: ((x[2].get("substitution") or {}).get("level") or 4, tuple(-r for r in x[0]), -((x[2].get("score") or {}).get("total") or 0), -x[1]))   # closest kind of product first, then your priorities  # your priorities first, then overall quality score, then similarity
    seen, uniq, nvar = set(), [], {}
    for it in found:  # the same product in several pack sizes is one recommendation (best ranked kept)
        k = variant_key(it[2])
        nvar[k] = nvar.get(k, 0) + 1
        if k not in seen:
            seen.add(k); uniq.append(it)
    found = uniq
    # Prefer cross-brand discovery without making diversity a hard eligibility rule.
    # Keep at most two products from one brand in the first five when alternatives exist.
    if len(found) > 1:
        selected, deferred, brand_counts = [], [], {}
        for item in found:
            brand = (item[2].get("brand") or "__unknown__").split(",")[0].strip().lower()
            if len(selected) < min(limit, 5) and brand_counts.get(brand, 0) >= 2:
                deferred.append(item)
                continue
            selected.append(item)
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        found = selected + deferred
    alts = []
    for rank, sim, c, d in found[:limit]:
        imp = []
        for k in priorities:
            if k == "overall":
                if d[k] is not None and d[k] > 0: imp.append(tr(lang, "imp_nutriscore", a=(orig.get("nutriScore") or "?").upper(), b=(c.get("nutriScore") or "?").upper()))
            elif k == "value":
                if d[k] is not None and d[k] > PRIORITIES[k][2]:
                    b = value_basis(priorities)
                    if b == "floor":
                        imp.append(tr(lang, "imp_value_floor", d=f"{d[k]:.2f}"))
                    else:
                        f = "protein100g" if b == "protein" else "fiber100g"
                        imp.append(tr(lang, "imp_value", what=tr(lang, "n_" + b), a=f"{per_euro(orig['nutriments'], f, orig_price):.1f}", b=f"{per_euro(c['nutriments'], f, prices[c['barcode']]):.1f}"))
            elif k == "budget":
                if d[k] is not None and d[k] > PRIORITIES[k][2]: imp.append(tr(lang, "imp_price", d=f"{d[k]/100:.2f}", a=f"{orig_price/100:.2f}", b=f"{prices[c['barcode']]/100:.2f}"))
            elif k == "additives":
                if d[k] is not None and d[k] > 0: imp.append(tr(lang, "imp_additives", n=int(d[k]), a=len(orig["additives"]), b=len(c["additives"])))
            elif d[k] is not None and d[k] > PRIORITIES[k][2]:
                f = PRIORITIES[k][0]
                imp.append(tr(lang, "imp_more" if PRIORITIES[k][1] > 0 else "imp_less", d=f"{abs(d[k]):.1f}", what=tr(lang, NAME_KEY[k]), a=f"{orig['nutriments'][f]:.1f}", b=f"{c['nutriments'][f]:.1f}"))
        alts.append({"product_id": c["id"], "product": c, "comparison": {DIFF_KEY[k]: (d[k] if k == "overall" or d[k] is None else round(d[k] * PRIORITIES[k][1], 2)) for k in priorities},
                     "price_per_100_cents": (prices or {}).get(c["barcode"]),
                     "value": value_card(orig, c, orig_price, (prices or {}).get(c["barcode"])),
                     "improvements": imp, "tradeoffs": _tradeoffs(orig, c, sim, lang, bool({"budget", "value"} & set(priorities)) and (prices or {}).get(c["barcode"]) is None), "similarity": round(sim, 2), "other_sizes": nvar[variant_key(c)] - 1,
                     "data_quality": "complete" if c.get("dataQuality", {}).get("nutritionComplete") else "partial"})
    return {"alternatives": alts, "excluded": ex,
            "diagnostics": funnel,
            "candidates_considered": len(peers),
            "no_recommendation_reason": None if alts else tr(lang, "no_alt")}

def compare(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    fields = ["energyKcal100g", "protein100g", "sugars100g", "saturatedFat100g", "salt100g", "fiber100g"]
    best = {"protein100g": 1, "fiber100g": 1, "sugars100g": -1, "saturatedFat100g": -1, "salt100g": -1}
    rows = []
    for f in fields:
        vals = [p["nutriments"].get(f) for p in products]
        known = [v for v in vals if v is not None]
        b = None
        if f in best and len(set(known)) > 1:
            b = max(known) if best[f] > 0 else min(known)
        rows.append({"field": f, "values": vals, "favourable": [v == b if v is not None and b is not None else False for v in vals]})
    micro_keys = [k for k in dict.fromkeys(m["key"] for p in products for m in p.get("micronutrients", []))]
    micro = []
    for k in micro_keys:
        vals = [next((m for m in p.get("micronutrients", []) if m["key"] == k), None) for p in products]
        pcts = [None if v is None else v["nrv_pct"] for v in vals]
        known = [x for x in pcts if x is not None]
        top = max(known) if len(set(known)) > 1 else None
        micro.append({"key": k, "unit": next(v["unit"] for v in vals if v), "values": [None if v is None else v["amount"] for v in vals], "nrv_pct": pcts, "favourable": [x is not None and x == top for x in pcts]})
    return {"basis": "per 100 g / 100 ml", "rows": rows, "nova": [p.get("novaGroup") for p in products], "micro": micro, "note": "Highlights are per-nutrient only; no product is declared the overall winner."}


def data_issues(p: Dict[str, Any]) -> List[str]:
    """Problems in a product's own data that make a comparison unreliable (empty list = usable). Checked before a product can be recommended."""
    n = p.get("nutriments") or {}
    issues = []
    macro = sum(n.get(k) or 0 for k in ("fat100g", "carbohydrates100g", "protein100g", "fiber100g", "salt100g"))
    if macro > 115:                                              # more than 100 g of nutrients in 100 g of product: a unit or typing error
        issues.append("nutrition_implausible")
    if (n.get("sugars100g") or 0) > 100 or (n.get("salt100g") or 0) > 100 or (n.get("saturatedFat100g") or 0) > 100:
        issues.append("nutrition_implausible")
    if n.get("sugars100g") is not None and n.get("carbohydrates100g") is not None and n["sugars100g"] > n["carbohydrates100g"] + 1:
        issues.append("sugars_exceed_carbohydrates")
    if (p.get("score") or {}).get("total") is None:
        issues.append("no_score")
    return sorted(set(issues))


def prefilter(orig: Dict[str, Any], peers: List[Dict[str, Any]], allergens: List[str], diet: Optional[str], mode: str,
              n: Optional[int] = None, priorities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Candidates that pass hard restrictions and compatibility, kept for price enrichment and ranking.
    Full indexed retrieval: replaces the destructive top-N cutoff so that cheaper, equally good products
    are not dropped before their prices are checked.
    """
    out = []
    for c in peers:
        if c["barcode"] == orig["barcode"] or c.get("soldInFrance") is False or restriction_status(c, allergens, diet) != "ok":
            continue
        if {"nutrition_implausible", "sugars_exceed_carbohydrates"} & set(data_issues(c)):   # a typing/unit error in the data must not turn into a recommendation
            continue
        sub = c.get("substitution") or taxonomy.substitution(orig, c)
        if sub is None:
            continue
        c = {**c, "substitution": sub}
        sim = deep_similarity(orig, c)
        if mode == "similar" and sim < 0.45 and (sub.get("level") or 4) > 2:
            continue
        out.append((sim, c))
    out.sort(key=lambda x: (((x[1].get("substitution") or {}).get("level") or 4), -x[0]))
    if n is not None and len(out) > n:
        return [c for _, c in out[:n]]
    return [c for _, c in out]


def indicators(p: Dict[str, Any], price100: Optional[float]) -> Optional[Dict[str, Any]]:
    """Nutritional value per euro, several separate indicators (no single invented score). price100 = cents per 100 g/ml."""
    if price100 is None or price100 <= 0:
        return None
    n, eur100 = p["nutriments"], price100 / 100.0
    def cost10(field):
        v = n.get(field)
        return None if not v else round(eur100 * 10.0 / v, 3)  # euros for 10 g of the nutrient
    serv = p.get("servingG")
    return {"price_per_kg_eur": round(eur100 * 10, 2), "price_per_serving_eur": None if not serv else round(eur100 * serv / 100.0, 2),
            "cost_per_10g_protein_eur": cost10("protein100g"), "cost_per_10g_fibre_eur": cost10("fiber100g"),
            "protein_g_per_euro": per_euro(n, "protein100g", price100), "fibre_g_per_euro": per_euro(n, "fiber100g", price100),
            "kcal_per_euro": per_euro(n, "energyKcal100g", price100)}


def _gap(a, b, thr):
    """True when candidate value b exceeds original a by more than thr (both known)."""
    return a is not None and b is not None and b - a > thr


def is_liquid(p) -> bool:
    """A drink / liquid: pack size in ml, or (size unknown) a beverage / sauce-like category."""
    q = p.get("quantity")
    if q:
        return q.get("unit") == "ml"
    from .score import DRINK_TAGS
    return bool(DRINK_TAGS.search(" ".join(p.get("categories") or [])))


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def price_position(price100, ref):
    """Price Score /100 against a reference price (the typical price of comparable products): same as the reference = 50, half the price = 80, a third = 100,
    2.5 x the reference = 0. Logarithmic, so 'a bit cheaper' and 'much cheaper' differ, and one outlier price cannot distort everyone else's score."""
    if not price100 or not ref or price100 <= 0 or ref <= 0:
        return None
    return max(0.0, min(100.0, 50.0 - 50.0 * math.log2(price100 / ref) / math.log2(2.5)))


def reference_price(prices, orig_price=None):
    """The price a score is measured against. With a known price for the scanned product, that is the reference: a candidate's score then depends only on its own
    price and quality and on the scanned product, never on which other candidates were returned. Without it, the median of the comparable products (needs a pool)."""
    if orig_price:
        return orig_price
    return _median([p for p in prices if p])


def value_scores(items, orig_price=None):
    """Quality-price score /100 for items = [(key, quality_total, price100)].
    Weighted geometric mean of quality (65 %) and price position (35 %): both must be decent, so cheap junk (low quality) and overpriced premium both score below a solid,
    fairly priced product. The reference price is the median of the comparable products. None when the quality or the price is unknown."""
    ref = reference_price([p for _, _, p in items], orig_price)
    out = {}
    for k, q, p in items:
        ps = price_position(p, ref)
        out[k] = None if (q is None or ps is None or q <= 0) else round(math.exp(0.65 * math.log(max(q, 1.0)) + 0.35 * math.log(max(ps, 1.0))))
    return out


def price_scores(prices, orig_price=None):
    """Price Score /100 of each normalised price (per kg / L) against the median price of the comparable products (see price_position)."""
    ref = reference_price(list(prices.values()), orig_price)
    return {k: (None if not p or price_position(p, ref) is None else round(price_position(p, ref))) for k, p in prices.items()}


def qp(c, price100):
    """Quality per euro: quality score (0-100) for each euro spent per kg/L. Higher = more quality for the money."""
    sc = (c.get("score") or {}).get("total")
    return None if sc is None or not price100 or price100 <= 0 else round(sc / (price100 / 100.0 * 10), 2)  # price100 = cents per 100 g -> euros per kg


def pe_of(r, field):
    return per_euro(r["product"]["nutriments"], field, r["price_per_100_cents"])


# Largest quality-score drop (out of 100) a 'cheaper' or 'best value' pick may have against the scanned product.
MAX_SHOWN = 20     # most alternatives returned per tab
QUALITY_FLOOR = 5
# Smallest quality gain (out of 100) that counts as a genuine improvement: one point is noise, not a better product.
QUALITY_IMPROVEMENT = 5


def _older_than(date: Optional[str], days: int) -> bool:
    """True when an ISO date is more than `days` days old (an unknown date counts as old)."""
    from datetime import date as _d
    try:
        return (_d.today() - _d.fromisoformat(str(date)[:10])).days > days
    except (TypeError, ValueError):
        return True


def _verified_price(price100: Optional[float], point: Optional[Dict[str, Any]], supplied: bool, max_age_days: int) -> bool:
    """Only an observed, dated price for this exact barcode may win Cheapest or Best value.
    Inferred pack-size prices (copied from a sibling pack) and estimates never qualify: they are indicative, not verified.
    When no provenance was supplied at all (a pure ranking call), the price is taken at face value.
    """
    if not supplied:
        return True
    if (point or {}).get("derived"):
        return False
    from . import value as value_mod
    return value_mod.is_ranking_eligible_price(point, price100, max_age_days)


POPULAR_SCANS = 5          # scanned at least this often on Open Food Facts counts as known to shoppers


def is_popular(c: Dict[str, Any], prices: Optional[Dict[str, float]] = None) -> bool:
    """Known to shoppers: scanned often, sold in at least one known chain, or seen with an observed price (so it is on a shelf somewhere)."""
    pop = c.get("popularity") or {}
    return (pop.get("scans") or 0) >= POPULAR_SCANS or (pop.get("chains") or 0) >= 1 or bool(c.get("chains")) or ((prices or {}).get(c.get("barcode")) is not None)


def close_only(items, level_of, min_close: int = 3):
    """Substitutes for the money and quality tabs: only the closest kinds of product (level 1-2).
    Level 3 or 4 must never appear in a price or value comparison.
    """
    return [x for x in items if (level_of(x) or 3) <= 2]


def brand_variety(items, brand_of, first: int = 5, per: int = 2):
    """Keeps the order but, within the first `first` places, lets one brand take at most `per` while other brands remain; the rest follow in order."""
    head, rest, count = [], [], {}
    for it in items:
        b = (brand_of(it) or "").split(",")[0].strip().lower()
        if len(head) < first and count.get(b, 0) < per:
            head.append(it)
            count[b] = count.get(b, 0) + 1
        else:
            rest.append(it)
    return head + rest


# Largest rise (g per 100 g/ml) in sugars / salt a cheaper or better-value pick may have, by kind of product. None = not judged on that nutrient
# (naturally sweet whole foods; fats and oils). The overall quality score stays the main safeguard.
_SUGAR_LIMIT = {"drinks": 2.5, "dairy": 4.0, "dairy_alt": 4.0, "cereals_bakery": 4.0, "produce": None, "fats_oils": None}
_SALT_LIMIT = {"cereals_bakery": 0.4, "meat_fish": 0.8, "condiments": 0.8, "meals": 0.8, "fats_oils": None}


def nutrient_limits(orig):
    """(sugar rise, salt rise) tolerated for this kind of product; defaults 5 g and 0.5 g."""
    fam = taxonomy.classify(orig).get("family")
    return _SUGAR_LIMIT.get(fam, 5.0), _SALT_LIMIT.get(fam, 0.5)


def percentile_value_scores(items: List[Tuple[Any, Optional[float], Optional[float]]]) -> Dict[Any, Optional[Dict[str, Any]]]:
    """Constrained, percentile-based quality-price index across cohort:
    items = [(key, quality_total, price100)].
    For items with known quality and price > 0:
    Quality percentile Q_pct = rank position in cohort quality distribution (higher score -> higher percentile).
    Affordability percentile A_pct = rank position in cohort price distribution (lower price -> higher percentile).
    Value Index = round(100 * sqrt(Q_pct * A_pct))
    Returns dict mapping key -> {
        "value_score": int,
        "quality_percentile": float,
        "affordability_percentile": float,
    } or None.
    """
    usable = [(k, float(q), float(p)) for k, q, p in items if q is not None and p is not None and q > 0 and p > 0]
    out: Dict[Any, Optional[Dict[str, Any]]] = {k: None for k, _, _ in items}
    if not usable:
        return out
    n = len(usable)
    scores = [q for _, q, _ in usable]
    prices = [p for _, _, p in usable]
    for k, q, p in usable:
        q_less = sum(1 for s in scores if s < q)
        q_eq = sum(1 for s in scores if s == q)
        q_pct = max(0.01, min(1.0, (q_less + 0.5 * q_eq) / n))

        p_more = sum(1 for pr in prices if pr > p)
        p_eq = sum(1 for pr in prices if pr == p)
        a_pct = max(0.01, min(1.0, (p_more + 0.5 * p_eq) / n))

        val = round(100.0 * math.sqrt(q_pct * a_pct))
        out[k] = {
            "value_score": max(1, min(100, val)),
            "quality_percentile": round(q_pct * 100, 1),
            "affordability_percentile": round(a_pct * 100, 1),
        }
    return out


def rank_cheapest(orig: Dict[str, Any], pool: List[Dict[str, Any]], prices: Dict[str, float],
                  orig_price: Optional[float] = None, points: Optional[Dict[str, Any]] = None,
                  estimated: frozenset = frozenset(), orig_estimated: bool = False,
                  lang: str = "fr", max_age_days: int = 90) -> Dict[str, Any]:
    """Lowest verified unit price among genuinely close substitutes (level 1-2) that meet the quality floor.
    No fillers: only products that are genuinely cheaper and qualify are returned.
    """
    on = orig.get("nutriments") or {}
    sug_lim, salt_lim = nutrient_limits(orig)
    o_sc0 = (orig.get("score") or {}).get("total")
    no_baseline = bool(orig_price is None or orig_estimated)
    
    rows = []
    for c in pool:
        bc = c.get("barcode")
        if bc == orig.get("barcode") or bc in estimated:
            continue
        p = prices.get(bc)
        if p is None or p < 3:
            continue
        pt = (points or {}).get(bc) or {}
        if not _verified_price(p, pt, points is not None, max_age_days):
            continue
        
        # Hard substitution level requirement: level 1 or 2 ONLY
        sub = c.get("substitution") or taxonomy.substitution(orig, c)
        if sub is None or sub.get("level") not in (1, 2):
            continue
        c = {**c, "substitution": sub}
        
        # Market relevance: must not be explicitly not in market
        if c.get("soldInFrance") is False:
            continue
        
        n = c.get("nutriments") or {}
        big_penalty = (sug_lim is not None and _gap(on.get("sugars100g"), n.get("sugars100g"), sug_lim)) or \
                      (salt_lim is not None and _gap(on.get("salt100g"), n.get("salt100g"), salt_lim))
        if big_penalty:
            continue
        
        # Quality floor: candidate score >= orig score - 5
        c_sc = (c.get("score") or {}).get("total")
        if c_sc is not None and o_sc0 is not None:
            min_ok = c_sc >= o_sc0 - QUALITY_FLOOR
        else:
            min_ok = (not _gap(on.get("sugars100g"), n.get("sugars100g"), 3) and not _gap(on.get("salt100g"), n.get("salt100g"), 0.3)
                      and not (on.get("protein100g") and n.get("protein100g") is not None and n["protein100g"] < 0.8 * on["protein100g"])
                      and not (on.get("fiber100g") and n.get("fiber100g") is not None and n["fiber100g"] < 0.8 * on["fiber100g"]))
        if not min_ok:
            continue
        
        # If original price is known, candidate must actually be cheaper
        if not no_baseline and orig_price is not None:
            if p >= orig_price * 0.98:
                continue
        
        sim = deep_similarity(orig, c)
        conf = pt.get("confidence") or "medium"
        conf_rank = 2 if conf == "high" else 1 if conf == "medium" else 0
        
        diff_cents = (orig_price - p) if (orig_price is not None and not no_baseline) else None
        why = tr(lang, "rk_budget", d=f"{diff_cents/100:.2f}") if diff_cents is not None else tr(lang, "rk_known", p=f"{p/100:.2f}")
        
        rows.append({
            "product": c,
            "price_per_100_cents": round(p, 1),
            "similarity": round(sim, 2),
            "indicators": indicators(c, p),
            "tradeoffs": _tradeoffs(orig, c, sim, lang),
            "why": why,
            "conf_rank": conf_rank,
            "price_source": pt if pt else None,
            "price_stale": _older_than(pt.get("date"), 90),
            "quality_score": c_sc,
        })
    
    # Sort: lowest unit price first, higher price confidence, higher quality score
    rows.sort(key=lambda r: (r["price_per_100_cents"], -r["conf_rank"], -(r["quality_score"] or 0)))
    result = rows[:MAX_SHOWN]  # strict order: brand variety must never move a cheaper or better product down
    return {"items": result, "no_baseline": no_baseline}


def rank_quality(orig: Dict[str, Any], pool: List[Dict[str, Any]], prices: Optional[Dict[str, float]] = None,
                 points: Optional[Dict[str, Any]] = None, lang: str = "fr") -> List[Dict[str, Any]]:
    """The best-quality close substitutes (level 1-2), strictly by Mieux nutrition score. Price never affects the order.

    Every scored close substitute is listed, each labelled better / not better than the scanned product (so a list is never empty just
    because the scanned product is already good). Ties are broken by what a careful shopper would check next: complete nutrition data,
    fewer risky additives, less processing (NOVA), then closeness. The same product in another pack size is listed once."""
    o_sc = (orig.get("score") or {}).get("total")
    rows = []
    for c in pool:
        bc = c.get("barcode")
        if bc == orig.get("barcode"):
            continue
        sub = c.get("substitution") or taxonomy.substitution(orig, c)
        if sub is None or sub.get("level") not in (1, 2):
            continue
        c = {**c, "substitution": sub}
        c_sc = (c.get("score") or {}).get("total")
        if c_sc is None:
            continue
        # Missing nutrition data is never a quality pick, however good the partial score looks
        if not (c.get("dataQuality") or {}).get("nutritionComplete"):
            continue
        sim = deep_similarity(orig, c)
        p = (prices or {}).get(bc)
        pt = (points or {}).get(bc) or {}
        comp = 1
        risky = sum(1 for x in ((c.get("score") or {}).get("additives") or {}).get("items", []) if x.get("level") in ("C", "D"))
        nova = c.get("novaGroup") or 4
        delta = None if o_sc is None else c_sc - o_sc
        rows.append({
            "product": c,
            "quality_score": c_sc,
            "quality_delta": delta,
            "price_per_100_cents": round(p, 1) if p is not None else None,
            "similarity": round(sim, 2),
            "indicators": indicators(c, p) if p else None,
            "tradeoffs": _tradeoffs(orig, c, sim, lang),
            "why": tr(lang, "quality_note", s=c_sc, o=o_sc if o_sc is not None else "?"),
            "better": bool(delta is not None and delta >= QUALITY_IMPROVEMENT),
            "price_source": pt if pt else None,
            "completeness": comp,
            "quality_detail": {"additives_at_risk": risky, "nova": nova, "nutrition_complete": bool(comp)},
            "estimated": False,
            "_k": (-c_sc, -comp, risky, nova, -sim, 0 if is_popular(c, prices) else 1),
        })
    rows.sort(key=lambda r: r["_k"])
    out, seen = [], set()
    for r in rows:
        vk = variant_key(r["product"])
        if vk in seen:
            continue                      # another pack size of a product already listed
        seen.add(vk)
        r.pop("_k", None)
        out.append(r)
        if len(out) >= MAX_SHOWN:
            break
    return out


def rank_best_value(orig: Dict[str, Any], pool: List[Dict[str, Any]], prices: Dict[str, float],
                    orig_price: Optional[float] = None, points: Optional[Dict[str, Any]] = None,
                    estimated: frozenset = frozenset(), orig_estimated: bool = False,
                    lang: str = "fr", max_age_days: int = 90) -> Dict[str, Any]:
    """Constrained, percentile-based quality-price index across the comparable cohort.
    No floor against the scanned product's own score: a cheaper, slightly-lower-quality product can still be a
    genuinely better value, and a list that only shows "better than yours" is empty exactly when the scanned
    product is already decent. The value_score itself already weighs nutrition and damps weak products (see
    value_index.py) - that is the safeguard, not a floor here.
    Dominated items on Pareto frontier (quality vs price) are deprioritized.
    No fillers: only genuinely eligible candidates are returned.
    """
    on = orig.get("nutriments") or {}
    sug_lim, salt_lim = nutrient_limits(orig)
    o_sc0 = (orig.get("score") or {}).get("total")
    no_baseline = bool(orig_price is None or orig_estimated)
    
    candidates = []
    for c in pool:
        bc = c.get("barcode")
        if bc == orig.get("barcode") or bc in estimated:
            continue
        p = prices.get(bc)
        if p is None or p < 3:
            continue
        pt = (points or {}).get(bc) or {}
        # Any observed price up to a year old counts here (the score below discounts older ones); estimates, prices
        # copied from another pack size, and a web search's own approximate finding never do - it was never seen on
        # a receipt or an Open Prices observation, so using it to decide a ranking would make "verified" meaningless.
        if points is not None:
            if pt.get("source") == "estimate" or pt.get("stale") or pt.get("derived") or pt.get("approximate"):
                continue      # estimates, derived prices and web-search approximates never rank
            from .value import age_days
            ag = age_days(pt.get("date")) if pt.get("date") else None
            if ag is None or ag > 365:
                continue
        
        # Substitution level 1 or 2 only
        sub = c.get("substitution") or taxonomy.substitution(orig, c)
        if sub is None or sub.get("level") not in (1, 2):
            continue
        c = {**c, "substitution": sub}
        
        if c.get("soldInFrance") is False:
            continue
        
        c_sc = (c.get("score") or {}).get("total")
        if c_sc is None:
            continue
        # The same requirement rank_quality applies: an incomplete nutrition profile can still produce a score (score.py
        # computes one from whatever nutrients are present), but that score is not reliable enough to decide a ranking.
        if not (c.get("dataQuality") or {}).get("nutritionComplete"):
            continue

        # No floor against the scanned product here: the price-quality score already weighs nutrition (and damps weak products), and a list that
        # only shows products "better than yours" is empty exactly when the scanned product is already a good choice.
        sim = deep_similarity(orig, c)
        candidates.append((c, c_sc, p, sim, pt))
    
    if not candidates:
        return {"items": [], "no_baseline": no_baseline}
    
    # Cohort for percentile calculation: include original if known and usable
    cohort_items = [(c.get("barcode"), sc, p) for c, sc, p, _, _ in candidates]
    include_orig = not no_baseline and o_sc0 is not None and orig_price is not None and orig_price >= 3
    if include_orig:
        cohort_items.append(("__orig", float(o_sc0), float(orig_price)))
    
    # Fixed per-type reference first (stable whatever the search returned); the old cohort percentile only where a type has no reference.
    type_id = taxonomy.classify(orig).get("type")
    pct_map = percentile_value_scores(cohort_items)
    for key, sc_, pr_ in cohort_items:
        fixed = value_index.value_index(type_id, sc_, pr_)
        if fixed:
            pct_map[key] = fixed
    orig_pct = pct_map.get("__orig")
    orig_val_score = orig_pct["value_score"] if orig_pct else None
    
    # Calculate Pareto dominance (quality vs price)
    temp_rows = [{"product": c, "price_per_100_cents": p} for c, _, p, _, _ in candidates]
    pareto_keys = [lambda r: -r["price_per_100_cents"], lambda r: (r["product"].get("score") or {}).get("total")]
    dom_flags = dominated(temp_rows, pareto_keys, min_common=2)
    
    rows = []
    for (c, c_sc, p, sim, pt), is_dom in zip(candidates, dom_flags):
        pinfo = pct_map.get(c.get("barcode"))
        if not pinfo:
            continue
        val_score = pinfo["value_score"]
        
        # Detail: a price older than 90 days is worth a little less.
        factor = 1.0
        ag2 = None
        try:
            from .value import age_days as _ad
            ag2 = _ad(pt.get("date")) if pt.get("date") else None
        except Exception:
            ag2 = None
        if ag2 is not None and ag2 > 90:
            factor *= 0.95
        if pt.get("derived"):
            factor *= 0.92
        base_score = val_score
        val_score = max(1, round(val_score * factor))
        
        conf = pt.get("confidence") or "medium"
        conf_rank = 2 if conf == "high" else 1 if conf == "medium" else 0
        
        if no_baseline:
            why = tr(lang, "rk_qp_known", s=c_sc, p=f"{p*10/100:.2f}", v=val_score)
        else:
            why = tr(lang, "rk_qp", s=c_sc, p=f"{p*10/100:.2f}", o=f"{orig_price*10/100:.2f}",
                     os=o_sc0 if o_sc0 is not None else "?", v=val_score, ov=orig_val_score)
        
        rows.append({
            "product": c,
            "price_per_100_cents": round(p, 1),
            "similarity": round(sim, 2),
            "indicators": indicators(c, p),
            "tradeoffs": _tradeoffs(orig, c, sim, lang),
            "why": why,
            "value_score": val_score,
            "quality_percentile": pinfo["quality_percentile"],
            "affordability_percentile": pinfo["affordability_percentile"],
            "dominated": is_dom,
            "better_than_yours": (orig_val_score is not None and val_score > orig_val_score) if orig_val_score is not None else None,
            "value_detail": {"nutrition": c_sc, "price_per_100_cents": round(p, 1), "pack_cents": pt.get("pack_cents"), "size": c.get("quantity"),
                             "price_date": pt.get("date"), "price_derived": bool(pt.get("derived")), "freshness_factor": factor, "before_adjustment": base_score},
            "conf_rank": conf_rank,
            "price_source": pt if pt else None,
            "quality_score": c_sc,
        })
    
    # Sort: non-dominated first, then value index descending, then confidence, then quality
    rows.sort(key=lambda r: (-r["value_score"], bool(r["dominated"]), -r["conf_rank"], -(r["quality_score"] or 0), 0 if is_popular(r["product"], prices) else 1))   # the index already ranks a dominated product below its dominator; popularity only breaks a tie after it
    result = rows[:MAX_SHOWN]  # strict order: brand variety must never move a cheaper or better product down
    return {"items": result, "no_baseline": no_baseline, "original_value_score": orig_val_score}


def rank_closest(orig: Dict[str, Any], pool: List[Dict[str, Any]], prices: Optional[Dict[str, float]] = None,
                 points: Optional[Dict[str, Any]] = None, lang: str = "fr") -> List[Dict[str, Any]]:
    """Closest alternatives: genuine substitutes regardless of price or quality score.
    Pack sizes of the same product deduplicated, ordered by closeness (level 1-2) then similarity.
    Level 3-4 products are excluded from the closest tab.
    """
    # First, compute substitution levels and filter out level 3-4
    enriched = []
    for c in pool:
        sub = c.get("substitution") or taxonomy.substitution(orig, c)
        level = sub.get("level") if sub else 4
        if level > 2:  # exclude level 3-4 from closest tab
            continue
        enriched.append((level, c))
    # Sort by level (1 first, then 2), then by similarity
    # Within a match level, products about equally similar (same 0.1 band) are ordered priced-first: a card with a price is more useful.
    def _key(x):
        sim = deep_similarity(orig, x[1])
        has_price = (prices or {}).get(x[1].get("barcode")) is not None and ((points or {}).get(x[1].get("barcode")) or {}).get("source") != "estimate"
        return (x[0], -round(sim * 10) / 10, 0 if has_price else 1, -sim)
    enriched.sort(key=_key)
    close, seen_variant, per_brand = [], set(), {}
    for level, c in enriched:
        vk = variant_key(c)
        brand = (c.get("brand") or "").split(",")[0].strip().lower()
        if vk in seen_variant:
            continue
        seen_variant.add(vk)
        if per_brand.get(brand, 0) >= 2 and any(per_brand.get((x.get("brand") or "").split(",")[0].strip().lower(), 0) < 2 for _, x in enriched[enriched.index((level, c))+1:]):
            continue
        per_brand[brand] = per_brand.get(brand, 0) + 1
        close.append(c)
        if len(close) >= MAX_SHOWN:
            break
    out = []
    for c in close:
        sim = deep_similarity(orig, c)
        sub = c.get("substitution") or taxonomy.substitution(orig, c) or {}
        p = (prices or {}).get(c.get("barcode"))
        pt = (points or {}).get(c.get("barcode")) or {}
        out.append({
            "product": c,
            "why": tr(lang, "closest_" + sub.get("label", "broader")),
            "tradeoffs": _tradeoffs(orig, c, sim, lang),
            "price_source": pt if pt else None,
            "price_per_100_cents": round(p, 1) if p is not None else None,
            "similarity": round(sim, 2),
            "estimated": False,
        })
    return out


def build_rankings(orig: Dict[str, Any], pool: List[Dict[str, Any]], prices: Dict[str, float],
                   orig_price: Optional[float], priorities: List[str], mode: str, lang: str,
                   match_list: List[Dict[str, Any]], estimated: frozenset = frozenset(),
                   orig_estimated: bool = False, points: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build four separate rankings from one complete, shared search with HARD COMPATIBILITY GATE:
    - Budget: Cheapest comparable (lowest verified unit price above quality floor)
    - Quality: Best quality (highest reliable Mieux quality score)
    - Value: Best value (quality-price balance with quality floor)
    - Closest: Genuine close substitutes (levels 1-4)
    
    STRICT RULES:
    - Apply compatibility gate to entire pool first
    - Level 3/4 products only enter closest, not budget/quality/value
    - Low-confidence classifications rejected from strict rankings
    """
    # Step 1: Apply hard compatibility gate to create strict close-substitute pool
    strict_pool = []
    for c in pool:
        sub = taxonomy.substitution(orig, c)
        if sub is None:
            continue
        confidence = sub.get("confidence", "none")
        level = sub.get("level")
        
        # Add substitution to product
        c = {**c, "substitution": sub}
        
        # All qualified products go into closest (level 1-4 allowed)
        strict_pool.append(c)
    
    # Step 2: Filter for each ranking
    level_1_2 = [c for c in strict_pool if (c.get("substitution") or {}).get("level", 4) <= 2]
    high_confidence = [c for c in level_1_2 if (c.get("substitution") or {}).get("confidence") not in ("none", "low")]
    # Popularity used to be a hard eligibility filter here (dropping every candidate Open Food Facts has few scans of,
    # whenever 5+ better-known ones existed): a genuinely excellent niche product could be excluded from Quality and
    # Value for no reason but being new or poorly represented in OFF. It is now only a tiebreaker inside rank_quality
    # and rank_best_value themselves, after nutrition/value score, additive risk and similarity - never ahead of them.
    
    # Step 3: Build rankings
    # Closest: all levels 1-4, no price influence
    closest_items = rank_closest(orig, strict_pool, prices, points, lang)   # keeps levels 1-2 only
    cheapest = rank_cheapest(orig, high_confidence, prices, orig_price, points, estimated, orig_estimated, lang, max_age_days=365)   # an observed price up to a year old counts; older than 90 days it is flagged price_stale
    quality_items = rank_quality(orig, high_confidence, prices, points, lang)
    best_val = rank_best_value(orig, high_confidence, prices, orig_price, points, estimated, orig_estimated, lang)
    budget_items, value_items = cheapest["items"], best_val["items"]
    
    no_baseline = bool(orig_price is None or orig_estimated)
    
    return {
        "budget": budget_items,
        "value": value_items,
        "quality": quality_items,
        "closest": closest_items,
        "match": match_list[:MAX_SHOWN],
        "original_value_score": best_val.get("original_value_score"),
        "no_baseline": no_baseline,
    }
