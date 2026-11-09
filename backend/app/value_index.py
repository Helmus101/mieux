"""The price-quality score (0-100), read against FIXED per-type distributions built by scripts/build_value_reference.py.

    quality percentile   where the Mieux nutrition score sits among priced products of the same type
    affordability pct    where the unit price (per 100 g/ml, so pack size is already factored out) sits; cheaper is higher
    index                100 * sqrt(quality * affordability) * damping

The geometric mean means a product must be good on BOTH to score well: cheap junk and expensive quality both land low. The damping stops a
poor product reading as a bargain just because its category is poor: below a nutrition score of 65 the index is scaled down (down to 50 %).
Because the distributions are fixed, a product's score does not move with how many alternatives a search returned."""
import bisect
import json
import math
import os
from typing import Any, Dict, Optional

VERSION = 2
LIFT_FROM = 0.4              # the geometric mean of two percentiles bunches around 30-60: above this point it is eased upward so a genuinely good AND cheap product reaches the 80s-90s
LIFT_POWER = 0.6             # (a lopsided product, good but dear or cheap but poor, stays low: below LIFT_FROM nothing changes)
DAMP_FULL_AT = 65.0          # nutrition score from which there is no damping
DAMP_FLOOR = 0.5             # damping factor at a nutrition score of 0
MIN_N = 15                   # smaller reference populations are not used
_REF: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _REF
    if _REF is None:
        _REF = {}
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for path in (os.environ.get("VALUE_REFERENCE"), "/data/value_reference.json", os.path.join(here, "value_reference.json")):
            if path and os.path.exists(path):
                try:
                    _REF = json.load(open(path, encoding="utf-8")).get("types", {})
                    break
                except (OSError, ValueError):
                    continue
    return _REF


def set_reference(types: Optional[Dict[str, Any]]) -> None:
    """For tests: install a reference (or None to reload from disk)."""
    global _REF
    _REF = types


def _pct(q, x: float) -> float:
    """Share of the reference at or below x, interpolated between the stored quantiles."""
    if x <= q[0]:
        return 0.0
    if x >= q[-1]:
        return 1.0
    i = bisect.bisect_right(q, x)
    lo, hi = q[i - 1], q[i]
    frac = 0.0 if hi == lo else (x - lo) / (hi - lo)
    return (i - 1 + frac) / (len(q) - 1)


def damping(score: float) -> float:
    return DAMP_FLOOR + (1 - DAMP_FLOOR) * min(1.0, max(0.0, score) / DAMP_FULL_AT)


def value_index(type_id: Optional[str], score: Optional[float], price100: Optional[float]) -> Optional[Dict[str, Any]]:
    """None when there is no usable reference for the type or the score/price is missing."""
    ref = _load().get(type_id or "")
    if not ref or ref.get("n", 0) < MIN_N or score is None or not price100 or price100 <= 0:
        return None
    q, a = _pct(ref["score_q"], float(score)), 1.0 - _pct(ref["price_q"], float(price100))
    g = math.sqrt(q * a)
    if g > LIFT_FROM:
        g = LIFT_FROM + (1 - LIFT_FROM) * ((g - LIFT_FROM) / (1 - LIFT_FROM)) ** LIFT_POWER
    idx = 100.0 * g * damping(float(score))
    return {"value_score": max(1, min(100, round(idx))), "quality_percentile": round(q * 100, 1), "affordability_percentile": round(a * 100, 1),
            "reference_n": ref["n"], "basis": "type_reference", "version": VERSION}
