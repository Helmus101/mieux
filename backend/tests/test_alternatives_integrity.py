"""Integrity rules for the money and quality rankings.

A price may win Cheapest or Best value only when it is an observed, dated price for that exact barcode:
undated observations, inferred pack-size prices and estimates are indicative, never verified. Strict rankings keep their
order (brand variety must not move a cheaper product down), and a quality pick must be a meaningful gain.
"""
from datetime import date, timedelta

from app import engine


def P(barcode, name, brand="Brand", score=70, categories=None, complete=True, **nutriments):
    n = {"energyKcal100g": 80, "fat100g": 3.0, "saturatedFat100g": 1.5, "carbohydrates100g": 5.0, "sugars100g": 4.5,
         "protein100g": 5.0, "fiber100g": 0.0, "salt100g": 0.1}
    n.update(nutriments)
    return {"barcode": barcode, "id": barcode, "name": name, "brand": brand,
            "categories": categories if categories is not None else ["en:dairies", "en:yogurts", "en:plain-yogurts"],
            "soldInFrance": True, "allergens": [], "traces": [], "ingredientsText": "lait", "analysis": [],
            "nutriments": n, "score": {"total": score}, "nutriScore": "a" if score >= 80 else "b",
            "additives": [], "quantity": {"amount": 500, "unit": "g"},
            "dataQuality": {"nutritionComplete": complete}}


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def test_undated_observation_cannot_win_cheapest():
    orig, cheap = P("000", "Yaourt nature"), P("001", "Yaourt nature bio")
    res = engine.rank_cheapest(orig, [cheap], {"001": 30.0}, orig_price=50.0,
                               points={"001": {"source": "open_prices", "date": None}})
    assert res["items"] == []


def test_undated_observation_cannot_win_best_value():
    orig, cheap = P("000", "Yaourt nature"), P("001", "Yaourt nature bio", score=75)
    res = engine.rank_best_value(orig, [cheap], {"001": 30.0}, orig_price=50.0,
                                 points={"001": {"source": "open_prices"}})
    assert res["items"] == []


def test_expired_observation_is_rejected():
    orig, cheap = P("000", "Yaourt nature"), P("001", "Yaourt nature bio")
    res = engine.rank_cheapest(orig, [cheap], {"001": 30.0}, orig_price=50.0,
                               points={"001": {"source": "open_prices", "date": days_ago(200)}})
    assert res["items"] == []


def test_a_dated_recent_observation_qualifies():
    orig, cheap = P("000", "Yaourt nature"), P("001", "Yaourt nature bio")
    res = engine.rank_cheapest(orig, [cheap], {"001": 30.0}, orig_price=50.0,
                               points={"001": {"source": "open_prices", "date": days_ago(4)}})
    assert [r["product"]["barcode"] for r in res["items"]] == ["001"]


def test_inferred_pack_price_cannot_win_cheapest_or_value():
    orig = P("000", "Yaourt nature")
    cheap = P("001", "Yaourt nature bio")
    derived = {"source": "open_prices", "date": days_ago(2), "derived": True}
    assert engine.rank_cheapest(orig, [cheap], {"001": 30.0}, orig_price=50.0, points={"001": derived})["items"] == []
    assert engine.rank_best_value(orig, [P("001", "Yaourt nature bio", score=80)], {"001": 30.0},
                                  orig_price=50.0, points={"001": derived})["items"] == []


def test_cheapest_keeps_strict_unit_price_order_across_one_brand():
    orig = P("000", "Yaourt nature", score=70)
    a, b, c = P("001", "Yaourt nature a", score=70), P("002", "Yaourt nature b", score=70), P("003", "Yaourt nature c", score=70)
    res = engine.rank_cheapest(orig, [c, a, b], {"001": 20.0, "002": 30.0, "003": 40.0}, orig_price=50.0)
    assert [r["product"]["barcode"] for r in res["items"]] == ["001", "002", "003"]


def test_quality_requires_a_meaningful_gain():
    orig = P("000", "Yaourt nature", score=70)
    one_point = P("001", "Yaourt nature x", score=71)
    five_points = P("002", "Yaourt nature y", score=75)
    assert engine.rank_quality(orig, [one_point, five_points]) == [r for r in engine.rank_quality(orig, [one_point, five_points]) if r["product"]["barcode"] == "002"]
    assert [r["product"]["barcode"] for r in engine.rank_quality(orig, [one_point, five_points])] == ["002"]


def test_incomplete_nutrition_is_not_a_quality_pick():
    orig = P("000", "Yaourt nature", score=70)
    patchy = P("001", "Yaourt nature x", score=90, complete=False)
    assert engine.rank_quality(orig, [patchy]) == []
