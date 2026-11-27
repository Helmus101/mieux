from app import alt_gates


def _c(score):
    return {"barcode": str(score), "score": {"total": score}}


def test_quality_floor_keeps_only_scores_above_50_and_drops_unknown():
    kept = alt_gates.quality_floor([_c(49), _c(50), _c(51), {"barcode": "x", "score": {}}, {"barcode": "y"}])
    assert [c["barcode"] for c in kept] == ["51"]


def test_great_already_needs_both_numbers_above_90(monkeypatch):
    monkeypatch.setattr(alt_gates.value_index, "value_index", lambda t, q, p: {"value_score": 59})
    assert alt_gates.is_great_already({"name": "Haricots rouges", "score": {"total": 91}}, 26.2) is False   # value 59: still show
    monkeypatch.setattr(alt_gates.value_index, "value_index", lambda t, q, p: {"value_score": 97})
    assert alt_gates.is_great_already({"name": "Haricots rouges", "score": {"total": 91}}, 26.2) is True    # both above 90: hide
    assert alt_gates.is_great_already({"name": "Haricots rouges", "score": {"total": 89}}, 26.2) is False   # quality 89: show
    assert alt_gates.is_great_already({"name": "Haricots rouges", "score": {}}, 26.2) is False              # unknown quality never counts as high
    assert alt_gates.is_great_already({"name": "Haricots rouges", "score": {"total": 95}}, None) is False   # no price: no Valeur, show


def test_mieux_gate_does_not_apply_without_an_index():
    class NoIndex:  # an Open Food Facts client that has no taxonomy index
        pass
    assert alt_gates.mieux_gate(NoIndex(), {"name": "Cola"}, [_c(60)]) is None


def test_quality_floor_relaxes_for_cap_bound_category():
    """Smoked salmon: nearly all capped at 49. With the scanned product at 49 and fewer than THIN_POOL above 50, 49s stay."""
    pool = [_c(49)] * 20 + [_c(92), _c(96)]
    assert len(alt_gates.quality_floor(pool, 49)) == 22
    assert len(alt_gates.quality_floor(pool, 20)) == 2      # a poor scanned product never relaxes it
    assert len(alt_gates.quality_floor(pool, None)) == 2
    assert len(alt_gates.quality_floor([_c(60)] * 8 + [_c(49)], 49)) == 8   # enough above the floor: strict
