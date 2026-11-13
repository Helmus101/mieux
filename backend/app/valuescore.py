"""The single recommendation score. Three separate measurements per product, one final number:

    nutrition N     the Mieux quality score (score.py), 0-100: describes the product, never the shopper's budget
    affordability A how accessible the price is: the unit price against the median of the comparable products, and
                    whether the pack fits the shopper's stated spending limit
    efficiency E    nutritional benefit per euro, as a percentile of the comparable products

    V = w_a*A + w_n*N + w_e*E, weighted by the shopper's own profile, then softly damped below the nutrition floor.

Low nutrition is a penalty, not an exclusion: the engine ranks what can actually be bought, it does not hide the only
affordable options because none is excellent. Confidence is tracked separately and never changes a score."""
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROFILES: Dict[str, Tuple[float, float, float]] = {       # (affordability, nutrition, efficiency)
    "budget": (0.70, 0.25, 0.05),       # the cheapest decent product: price leads, nutrition keeps junk from the top
    "balanced": (0.35, 0.50, 0.15),     # the best value: quality for the money
    "nutrition": (0.05, 0.90, 0.05),    # the best quality: price only breaks ties
}
DEFAULT_PROFILE = "budget"
SOFT_FLOOR = 50          # below this nutrition score the value score is damped (down to 60 % at a score of 0)
FLOOR_MIN_FACTOR = 0.6


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def median(xs: Iterable[float]) -> Optional[float]:
    s = sorted(x for x in xs if x is not None)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def relative_price(price100: Optional[float], median100: Optional[float]) -> Optional[float]:
    """R_p = unit price / category median unit price. 0.75 = 25 % cheaper than the median, 1.30 = 30 % dearer."""
    if not price100 or not median100 or price100 <= 0 or median100 <= 0:
        return None
    return round(price100 / median100, 3)


def affordability(price100: Optional[float], median100: Optional[float], pack_cents: Optional[float] = None,
                  budget_cents: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """0-100. Half the median price = 100, the median = 60, 1.5x = 20, twice the median or more = 0.
    A pack dearer than the shopper's stated limit is halved: cheap for its category is not the same as affordable."""
    rp = relative_price(price100, median100)
    if rp is None:
        return None
    score = _clamp(100.0 - 80.0 * (rp - 0.5))
    fit: Optional[bool] = None
    if budget_cents is not None and pack_cents is not None:
        fit = pack_cents <= budget_cents
        if not fit:
            score *= 0.5
    return {"score": round(score), "relative_price": rp, "budget_fit": fit}


def quality_per_euro(nutrition: Optional[float], price100: Optional[float]) -> Optional[float]:
    if nutrition is None or not price100 or price100 <= 0:
        return None
    return nutrition / (price100 / 10.0)        # price100 is cents per 100 g -> euros per kg


def efficiency_percentiles(items: List[Tuple[Any, Optional[float], Optional[float]]]) -> Dict[Any, Optional[int]]:
    """items = [(key, nutrition, price100)] -> key -> 0-100 percentile of nutrition-per-euro within the cohort."""
    qpe = {k: quality_per_euro(n, p) for k, n, p in items}
    vals = [v for v in qpe.values() if v is not None]
    out: Dict[Any, Optional[int]] = {}
    n = len(vals)
    for k, v in qpe.items():
        if v is None or n == 0:
            out[k] = None
        elif n == 1:
            out[k] = 50
        else:
            less = sum(1 for x in vals if x < v)
            eq = sum(1 for x in vals if x == v)
            out[k] = round(100.0 * (less + 0.5 * eq) / n)
    return out


def soft_floor_factor(nutrition: float) -> float:
    if nutrition >= SOFT_FLOOR:
        return 1.0
    return FLOOR_MIN_FACTOR + (1.0 - FLOOR_MIN_FACTOR) * max(0.0, nutrition) / SOFT_FLOOR


def value(nutrition: Optional[float], afford: Optional[float], efficiency: Optional[float], profile: str = DEFAULT_PROFILE) -> Optional[int]:
    """The final recommendation score, 1-100. None when a measurement is missing: nothing is invented."""
    if nutrition is None or afford is None:
        return None
    wa, wn, we = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
    if efficiency is None:        # no cohort to compare against: give its weight to the two measured parts
        tot = wa + wn
        wa, wn, we = wa / tot, wn / tot, 0.0
    v = wa * afford + wn * nutrition + we * (efficiency or 0.0)
    v *= soft_floor_factor(nutrition)
    return int(_clamp(round(v), 1.0, 100.0))


def confidence(point: Optional[Dict[str, Any]], nutrition_complete: bool, has_chain: bool) -> str:
    """How firmly a recommendation may be presented: 'high', 'medium' or 'low'. Separate from the score."""
    from .value import price_confidence
    pc = price_confidence(point) if point else None
    if pc in (None, "low", "estimate") or not nutrition_complete:
        return "low"
    if pc == "high" and has_chain:
        return "high"
    return "medium"
