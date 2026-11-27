"""The gates that decide which candidates may be offered as alternatives, kept apart from the web layer so each can be tested alone.

    retrieve -> market / supermarket / price -> substitution gate (taxonomy.py) -> mieux_gate -> quality_floor -> rank (engine.py)
    and, at the very end, is_great_already() decides whether a list is worth showing at all.

Every function here is pure: it gets what it needs as arguments (the Open Food Facts client, the scanned product, the candidates).
"""
from typing import Any, Dict, List, Optional

from . import taxo1000, value_index

THIN_POOL = 8             # below this many alternatives above the floor, the floor relaxes to the scanned product's own score
RELAXED_FLOOR_MIN = 40    # ...but never below this
MIN_ALT_QUALITY = 50      # an alternative must score above this on quality to be offered at all
MIN_SAME_MIEUX_TYPE = 12  # with at least this many same-type candidates, sibling types of the category are not offered
GREAT_ALREADY = 90        # both the Valeur and the quality score above this: nothing is worth suggesting instead


def mieux_gate(off: Any, orig: Dict[str, Any], kept: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """The Mieux taxonomy gate. Only products placed at a specific type take part: a candidate must be in the scanned product's
    category, and in its exact type whenever enough of those exist. Returns None when the gate does not apply (the scanned
    product is not placed, or the index is missing): the older gates alone decide then.

    A placement made from the product's own name is trusted: a thin category then simply yields few or no alternatives rather than
    wrong ones. A placement made only from tags is a softer gate: it is used when it leaves at least 3 candidates."""
    fn = getattr(off, "taxo_places", None)
    if fn is None or not kept:
        return None
    o = taxo1000.classify(orig.get("name"), None, orig.get("brand"), orig.get("categories"))
    if o.get("level") not in (2, 3) or not o.get("category"):
        return None
    places = fn([c["barcode"] for c in kept])
    if not places:
        return None
    in_cat = [c for c in kept if (places.get(c["barcode"]) or {}).get("level") == 3 and places[c["barcode"]]["category"] == o["category"]]
    same_type = [c for c in in_cat if o.get("type") and places[c["barcode"]]["type"] == o["type"]]
    if len(same_type) >= MIN_SAME_MIEUX_TYPE:
        pool = same_type
    else:
        # Too few of the exact type (e.g. "sliced smoked salmon"): widen to the product's own other types (plain "smoked salmon")
        # before the whole category, which would offer sardines or fresh salmon for a pack of smoked slices.
        own = set(o.get("types") or [])
        related = [c for c in in_cat if places[c["barcode"]]["type"] in own] if len(own) > 1 else []
        pool = related if len(related) >= MIN_SAME_MIEUX_TYPE else in_cat
    if o.get("source") == "name" or len(pool) >= 3:
        return pool
    return None


def quality_floor(peers: List[Dict[str, Any]], orig_score: Optional[float] = None) -> List[Dict[str, Any]]:
    """Only alternatives with a quality score above MIN_ALT_QUALITY. An unknown score is unverified, not good.

    Some categories sit under that floor by nature: smoked salmon is ~2.9 g salt per 100 g, so nearly every one is capped at 49 by its
    Nutri-Score D/E and the strict floor would leave 5 of 115. When fewer than THIN_POOL pass it, the floor drops to the scanned
    product's own score, and only when that score is itself 40-50 (a cap-bound category, not a poor product): a candidate that is at least as good as what the shopper holds is a valid
    alternative, and the ranking then puts the best of that category first. The strict floor still applies whenever it leaves enough."""
    scored = [c for c in peers if isinstance((c.get("score") or {}).get("total"), (int, float))]
    strict = [c for c in scored if c["score"]["total"] > MIN_ALT_QUALITY]
    if len(strict) >= THIN_POOL or not isinstance(orig_score, (int, float)) or not RELAXED_FLOOR_MIN <= orig_score <= MIN_ALT_QUALITY:
        return strict
    return [c for c in scored if c["score"]["total"] >= orig_score]


def is_great_already(orig: Dict[str, Any], price100: Optional[float]) -> bool:
    """True when the scanned product is above GREAT_ALREADY on BOTH numbers its page shows: the price-quality Valeur (value_index)
    and the quality score. One high number alone still leaves a list worth showing; a missing one never counts as high."""
    q = (orig.get("score") or {}).get("total")
    if not price100 or not isinstance(q, (int, float)):
        return False
    vi = value_index.value_index(taxo1000.classify(orig.get("name"), None, orig.get("brand"), orig.get("categories")).get("type"), q, price100)
    return bool(vi) and min(vi["value_score"], q) > GREAT_ALREADY
