"""Choice Engine: deterministic, explainable. Candidates -> hard restrictions -> completeness -> rank by priority order -> explain."""
import math
from typing import Any, Dict, List, Optional

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


def dominated(items: List[Dict[str, Any]], keys) -> List[bool]:
    """True for items that another item beats or ties on every key (larger is better) and strictly beats on one. Unknown keys count as -inf."""
    vec = [[(k(i) if k(i) is not None else float("-inf")) for k in keys] for i in items]
    out = []
    for a in vec:
        out.append(any(all(b[j] >= a[j] for j in range(len(a))) and any(b[j] > a[j] for j in range(len(a))) for b in vec if b is not a))
    return out


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
    if (o["name"] or "").strip().lower() == (c["name"] or "").strip().lower() or (o["name"] or "").strip().lower() in (c["name"] or "").strip().lower():
        T.append(tr(lang, "tr_same"))
    on, cn = o.get("novaGroup"), c.get("novaGroup")
    if on and cn and cn > on:
        T.append(tr(lang, "tr_nova", a=on, b=cn))
    if price_unknown:
        T.append(tr(lang, "tr_price_unknown"))
    T.append(tr(lang, "tr_diff_type") if sim < 0.8 else tr(lang, "tr_diff_flavour"))
    return T


def choose(orig: Dict[str, Any], peers: List[Dict[str, Any]], priorities: List[str], allergens: List[str], diet: Optional[str],
           mode: str = "similar", limit: int = 5, prices: Optional[Dict[str, float]] = None,
           orig_price: Optional[float] = None, lang: str = "fr") -> Dict[str, Any]:
    ex = {"conflict": 0, "unverified": 0, "incomplete": 0, "not_better": 0, "dissimilar": 0, "not_in_france": 0}
    cats = set(orig["categories"])
    found = []
    for c in peers:
        if c["barcode"] == orig["barcode"]:
            continue
        if c.get("soldInFrance") is not True:  # recommend only what can be bought in France; unknown availability is not assumed
            ex["not_in_france"] += 1
            continue
        st = restriction_status(c, allergens, diet)
        if st != "ok":
            ex[st] += 1
            continue
        d = {k: _diff(orig, c, k, prices, orig_price, priorities) for k in priorities}
        for k in priorities[1:]:
            if k in ("budget", "value") and d[k] is None:
                d[k] = 0.0  # price unknown for a secondary priority: keep the product, say so in the trade-offs
        if any(v is None for v in d.values()):
            ex["incomplete"] += 1
            continue
        first = priorities[0]
        if not d[first] > PRIORITIES[first][2]:
            ex["not_better"] += 1
            continue
        sim = deep_similarity(orig, c)
        if mode == "similar" and sim < 0.45:
            ex["dissimilar"] += 1
            continue
        rank = [round(d[k] / (PRIORITIES[k][2] or 1)) for k in priorities]
        found.append((rank, sim, c, d))
    found.sort(key=lambda x: (tuple(-r for r in x[0]), -((x[2].get("score") or {}).get("total") or 0), -x[1]))  # your priorities first, then overall quality score, then similarity
    seen, uniq, nvar = set(), [], {}
    for it in found:  # the same product in several pack sizes is one recommendation (best ranked kept)
        k = variant_key(it[2])
        nvar[k] = nvar.get(k, 0) + 1
        if k not in seen:
            seen.add(k); uniq.append(it)
    found = uniq
    alts = []
    for rank, sim, c, d in found[:limit]:
        imp = []
        for k in priorities:
            if k == "overall":
                if d[k] > 0: imp.append(tr(lang, "imp_nutriscore", a=orig["nutriScore"].upper(), b=c["nutriScore"].upper()))
            elif k == "value":
                if d[k] > PRIORITIES[k][2]:
                    b = value_basis(priorities)
                    if b == "floor":
                        imp.append(tr(lang, "imp_value_floor", d=f"{d[k]:.2f}"))
                    else:
                        f = "protein100g" if b == "protein" else "fiber100g"
                        imp.append(tr(lang, "imp_value", what=tr(lang, "n_" + b), a=f"{per_euro(orig['nutriments'], f, orig_price):.1f}", b=f"{per_euro(c['nutriments'], f, prices[c['barcode']]):.1f}"))
            elif k == "budget":
                if d[k] > PRIORITIES[k][2]: imp.append(tr(lang, "imp_price", d=f"{d[k]/100:.2f}", a=f"{orig_price/100:.2f}", b=f"{prices[c['barcode']]/100:.2f}"))
            elif k == "additives":
                if d[k] > 0: imp.append(tr(lang, "imp_additives", n=int(d[k]), a=len(orig["additives"]), b=len(c["additives"])))
            elif d[k] > PRIORITIES[k][2]:
                f = PRIORITIES[k][0]
                imp.append(tr(lang, "imp_more" if PRIORITIES[k][1] > 0 else "imp_less", d=f"{abs(d[k]):.1f}", what=tr(lang, NAME_KEY[k]), a=f"{orig['nutriments'][f]:.1f}", b=f"{c['nutriments'][f]:.1f}"))
        alts.append({"product_id": c["id"], "product": c, "comparison": {DIFF_KEY[k]: (d[k] if k == "overall" else round(d[k] * PRIORITIES[k][1], 2)) for k in priorities},
                     "price_per_100_cents": (prices or {}).get(c["barcode"]),
                     "value": value_card(orig, c, orig_price, (prices or {}).get(c["barcode"])),
                     "improvements": imp, "tradeoffs": _tradeoffs(orig, c, sim, lang, bool({"budget", "value"} & set(priorities)) and (prices or {}).get(c["barcode"]) is None), "similarity": round(sim, 2), "other_sizes": nvar[variant_key(c)] - 1,
                     "data_quality": "complete" if c["dataQuality"]["nutritionComplete"] else "partial"})
    return {"alternatives": alts, "excluded": ex, "candidates_considered": len(peers),
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


def prefilter(orig: Dict[str, Any], peers: List[Dict[str, Any]], allergens: List[str], diet: Optional[str], mode: str,
              n: int = 40, priorities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Candidates that pass hard restrictions and similarity, kept for the price comparison.

    It is the union of the closest n products and the n products that are furthest ahead on the first priority: a product
    that is clearly better on what the person cares about must not be dropped before prices are compared just because it
    is a little less similar. Prices are attached to this list, so it is the only place where a good candidate can be lost."""
    out = []
    for c in peers:
        if c["barcode"] == orig["barcode"] or c.get("soldInFrance") is not True or restriction_status(c, allergens, diet) != "ok":
            continue
        sim = deep_similarity(orig, c)
        if mode == "similar" and sim < 0.45:
            continue
        out.append((sim, c))
    out.sort(key=lambda x: -x[0])
    keep: List[Dict[str, Any]] = [c for _, c in out[:n]]
    first = (priorities or [None])[0]
    if first in PRIORITIES and len(out) > n:
        ahead = []
        for sim, c in out:
            d = _diff(orig, c, first, None, None, priorities)
            if d is not None and d > PRIORITIES[first][2]:
                ahead.append((d, sim, c))
        ahead.sort(key=lambda x: (-x[0], -x[1]))
        seen = {c["barcode"] for c in keep}
        for _, _, c in ahead[:n]:
            if c["barcode"] not in seen:
                seen.add(c["barcode"])
                keep.append(c)
    return keep


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
    """Typical (median) price of the comparable products, your own included; needs at least 4 priced products, else your own price is the reference."""
    allp = [p for p in prices if p] + ([orig_price] if orig_price else [])
    if orig_price is None:
        return _median(allp)  # no baseline of your own: the typical price of the comparable products
    return _median(allp) if len(allp) >= 4 else orig_price


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


# Largest quality-score drop (out of 100) a 'cheaper' pick may have against the scanned product.
QUALITY_FLOOR = 8


def build_rankings(orig, pool, prices, orig_price, priorities, mode, lang, match_list):
    """Three separate rankings. Budget: cheapest that keeps minimum nutrition. Value: most nutrient per euro without big sugar/salt
    penalties. Match: the user's own priority order (already computed by choose)."""
    out = {"budget": [], "value": [], "match": match_list[:10]}
    on = orig["nutriments"]
    basis = "fibre" if (value_basis(priorities) == "fibre") else "protein"
    field = "fiber100g" if basis == "fibre" else "protein100g"
    cats = set(orig["categories"])
    rows = []
    ref = [v for v in list(prices.values()) + [orig_price] if v]
    med = sorted(ref)[len(ref) // 2] if ref else None
    for c in pool:
        p = prices.get(c["barcode"])
        if p is None or c["barcode"] == orig["barcode"] or p < 3:  # under 0.30 EUR/kg is a mis-scaled community price, not a real shelf price
            continue
        if med and len(ref) >= 5 and (p > med * 6 or p < med / 8):  # far outside what this kind of product costs: a mis-scaled price, never a cheapest/best-value pick
            continue
        sim = deep_similarity(orig, c)
        if mode == "similar" and sim < 0.45:
            continue
        n = c["nutriments"]
        big_penalty = _gap(on.get("sugars100g"), n.get("sugars100g"), 5) or _gap(on.get("salt100g"), n.get("salt100g"), 0.5)
        # "cheaper" must not mean "much worse": judged on the whole quality score (nutrition, additives, ingredients), not on each nutrient separately,
        # which silently dropped almost every real candidate over a gram of fibre. Without scores, the old nutrient floor is the fallback.
        c_sc, o_sc0 = (c.get("score") or {}).get("total"), (orig.get("score") or {}).get("total")
        if c_sc is not None and o_sc0 is not None:
            min_ok = c_sc >= o_sc0 - QUALITY_FLOOR
        else:
            min_ok = (not _gap(on.get("sugars100g"), n.get("sugars100g"), 3) and not _gap(on.get("salt100g"), n.get("salt100g"), 0.3)
                      and not (on.get("protein100g") and n.get("protein100g") is not None and n["protein100g"] < 0.8 * on["protein100g"])
                      and not (on.get("fiber100g") and n.get("fiber100g") is not None and n["fiber100g"] < 0.8 * on["fiber100g"]))
        min_ok = min_ok and not big_penalty
        rows.append({"product": c, "price_per_100_cents": round(p, 1), "similarity": round(sim, 2), "min_ok": min_ok, "big_penalty": big_penalty,
                     "indicators": indicators(c, p), "tradeoffs": _tradeoffs(orig, c, sim, lang)})
    if orig_price is None:
        # Your own product has no known price, so nothing can be PROVEN cheaper or better value than it. Still useful: the comparable products that do have a real price,
        # cheapest first (and best quality-for-price first), flagged 'no_baseline' so the screen says the comparison is by price, not against yours.
        good = [r for r in rows if r["min_ok"]]
        vs = value_scores([(r["product"]["barcode"], (r["product"].get("score") or {}).get("total"), r["price_per_100_cents"]) for r in rows])
        ps = price_scores({r["product"]["barcode"]: r["price_per_100_cents"] for r in rows})
        for r in rows:
            r["value_score"], r["price_score"] = vs.get(r["product"]["barcode"]), ps.get(r["product"]["barcode"])
        budget = sorted(good, key=lambda r: r["price_per_100_cents"])
        value = sorted([r for r in good if r["value_score"] is not None], key=lambda r: (-r["value_score"], r["price_per_100_cents"]))
        for r in budget: r["why"] = tr(lang, "rk_known", p=f"{r['price_per_100_cents']/100:.2f}")
        for r in value: r["why"] = tr(lang, "rk_qp_known", s=r["product"]["score"]["total"], p=f"{r['price_per_100_cents']*10/100:.2f}", v=r["value_score"])
        out["budget"], out["value"] = budget[:10], value[:10]
        out["no_baseline"] = True
        out["basis"] = basis
        return out
    # Precision over quantity: a list holds only what really qualifies, however short. Nothing is added to reach a number.
    budget = sorted([r for r in rows if r["min_ok"] and r["price_per_100_cents"] < orig_price * 0.98], key=lambda r: r["price_per_100_cents"])
    o_pe = per_euro(on, field, orig_price)
    def pe(r): return per_euro(r["product"]["nutriments"], field, r["price_per_100_cents"])
    o_sc = (orig.get("score") or {}).get("total")
    vs = value_scores([(r["product"]["barcode"], (r["product"].get("score") or {}).get("total"), r["price_per_100_cents"]) for r in rows] + [("__orig", o_sc, orig_price)], orig_price)
    o_vs = vs.get("__orig")
    for r in rows: r["value_score"] = vs.get(r["product"]["barcode"])
    ps = price_scores({r["product"]["barcode"]: r["price_per_100_cents"] for r in rows}, orig_price)
    for r in rows: r["price_score"] = ps.get(r["product"]["barcode"])
    # Quality-price: more quality (score /100) per euro than the scanned product, without losing more than 5 quality points.
    value = sorted([r for r in rows if r["value_score"] is not None and o_vs is not None and r["value_score"] >= o_vs + 3
                    and r["min_ok"] and (o_sc is None or r["product"]["score"]["total"] >= o_sc - 5)], key=lambda r: (-r["value_score"], r["price_per_100_cents"]))
    for r in budget: r["why"] = tr(lang, "rk_budget", d=f"{(orig_price - r['price_per_100_cents'])/100:.2f}")
    for r in value:
        r["why"] = tr(lang, "rk_qp", s=r["product"]["score"]["total"], p=f"{r['price_per_100_cents']*10/100:.2f}", o=f"{orig_price*10/100:.2f}", os=o_sc if o_sc is not None else "?", v=r["value_score"], ov=o_vs)
    # Pareto flag: a product that is not more expensive, not less nutritious (per euro), not worse on Nutri-Score/NOVA and not less similar, for every key,
    # than another candidate is "dominated"; the flag lets the UI prefer the efficient ones. Nothing is hidden.
    keys = [lambda r: -r["price_per_100_cents"], lambda r: r.get("value_score"), lambda r: NS_RANK.get(r["product"]["nutriScore"] or "", None),
            lambda r: -(r["product"].get("novaGroup") or 9) if r["product"].get("novaGroup") else None, lambda r: r["similarity"]]
    for group in (budget, value):
        for r, dom in zip(group, dominated(group, keys)):
            r["dominated"] = dom
    out["budget"], out["value"] = budget[:10], value[:10]
    out["basis"] = basis
    return out
