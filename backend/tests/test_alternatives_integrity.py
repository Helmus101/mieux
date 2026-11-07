"""Integrity rules for the money and quality rankings.

A price may win Cheapest or Best value only when it is an observed, dated price for that exact barcode:
undated observations, inferred pack-size prices and estimates are indicative, never verified. Strict rankings keep their
order (brand variety must not move a cheaper product down), and a quality pick must be a meaningful gain.
"""
from datetime import date, timedelta

from app import engine, taxonomy


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


JAM = ["en:fruit-and-vegetable-preserves", "en:jams", "en:berry-jams", "en:strawberry-jams"]


def test_strawberry_jam_is_classified_as_jam_not_a_spread():
    jam = P("010", "Confiture extra de Fraises", categories=JAM)
    assert taxonomy.classify(jam)["type"] == "jam"
    praline = P("011", "Pâte à tartiner noisettes et cacao", categories=["en:sweet-spreads", "en:chocolate-spreads"])
    assert taxonomy.classify(praline)["type"] == "chocolate_spread"
    assert taxonomy.substitution(jam, praline)["level"] == 3     # a spread, but not a jam: never a money or quality pick


def test_unrelated_products_are_never_substitutes():
    jam = P("010", "Confiture extra de Fraises", categories=JAM)
    lentils = P("012", "Orge, lentilles vertes, riz rouge", categories=["en:legumes", "en:lentils"])
    barley = P("013", "Orge mondé", categories=["en:cereals", "en:barley"])
    assert taxonomy.substitution(jam, lentils) is None
    assert taxonomy.substitution(jam, barley) is None


def test_quality_tab_only_lists_the_same_kind_of_product():
    jam = P("010", "Confiture extra de Fraises", score=44, categories=JAM)
    other = P("011", "Confiture de mûres", score=90, categories=JAM)
    praline = P("012", "Pâte à tartiner noisettes", score=95, categories=["en:sweet-spreads", "en:chocolate-spreads"])
    lentils = P("013", "Orge et lentilles", score=94, categories=["en:legumes", "en:lentils"])
    assert [r["product"]["name"] for r in engine.rank_quality(jam, [other, praline, lentils])] == ["Confiture de mûres"]


def test_generic_spread_tag_alone_cannot_make_a_substitute():
    """The exact production bug: a broad tag must not turn an unrelated product into a level-1 substitute."""
    jam = P("010", "Confiture extra de Fraises", categories=JAM)
    vague = P("014", "Spécialité de cassis", categories=["en:sweet-spreads", "en:groceries"])
    sub = taxonomy.substitution(jam, vague)
    assert sub is None or sub["level"] >= 3


def test_juice_is_a_juice_not_a_plant_drink():
    juice = P("020", "Pur jus d'orange", categories=["en:plant-based-beverages", "en:fruit-juices", "en:orange-juices"])
    assert taxonomy.classify(juice)["type"] == "fruit_juice"


def test_sliced_bread_is_not_a_baguette():
    sliced = P("021", "Pain de mie complet", categories=["en:breads", "en:sliced-breads"])
    baguette = P("022", "Baguette tradition", categories=["en:breads", "en:baguettes"])
    sub = taxonomy.substitution(sliced, baguette)
    assert sub is None or sub["level"] >= 3      # a loaf is a different purchase, never a money or quality pick


def test_lentil_chips_are_chips_not_crackers():
    chips = P("023", "Chips de lentilles", categories=["en:salty-snacks", "en:crackers"])
    assert taxonomy.classify(chips)["type"] == "chips"


def test_plain_yogurt_stays_plain():
    y = P("024", "Yaourt nature", categories=["en:dairies", "en:yogurts", "en:desserts"])
    assert taxonomy.classify(y)["type"] == "plain_yogurt"
