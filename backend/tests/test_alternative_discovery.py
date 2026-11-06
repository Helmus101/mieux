import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import engine, taxonomy  # noqa: E402


def product(name, brand, tags, sold=True, **nutriments):
    return {
        "barcode": name,
        "id": name,
        "name": name,
        "brand": brand,
        "categories": tags,
        "soldInFrance": sold,
        "allergens": [],
        "traces": [],
        "ingredientsText": "lait",
        "analysis": [],
        "nutriments": {"energyKcal100g": 80, "fat100g": 2, "carbohydrates100g": 6,
                        "protein100g": 4, "sugars100g": 4, "salt100g": 0.1,
                        "saturatedFat100g": 1, "fiber100g": 0, **nutriments},
        "score": {"total": 60},
        "nutriScore": "b",
        "additives": [],
        "quantity": {"amount": 500, "unit": "g"},
    }


def test_closest_discovers_different_names_and_brands_without_priority_gain():
    original = product("Nature classique", "Danone", ["en:dairies", "en:yogurts"] , protein100g=10)
    peers = [
        product("Le crémeux", "Carrefour", ["en:yogurts"], protein100g=8),
        product("Douceur nature", "Auchan", ["en:yogurts"], protein100g=9),
        product("Tradition", "MDD", ["en:yogurts"], protein100g=7),
    ]
    result = engine.choose(original, peers, ["protein"], [], None, "similar", 5, lang="fr")
    assert {row["product"]["brand"] for row in result["alternatives"]} == {"Carrefour", "Auchan", "MDD"}
    assert len(result["alternatives"]) == 3


def test_closest_keeps_unknown_priority_as_unknown():
    original = product("Yaourt nature", "Danone", ["en:yogurts"], protein100g=5)
    candidate = product("Nature bio", "Carrefour", ["en:yogurts"])
    candidate["nutriments"]["protein100g"] = None
    result = engine.choose(original, [candidate], ["protein"], [], None, "similar", 5, lang="fr")
    assert len(result["alternatives"]) == 1
    assert result["alternatives"][0]["comparison"]["protein_difference_per_100g"] is None


def test_unknown_and_explicitly_unavailable_france_are_not_recommended():
    original = product("Yaourt nature", "Danone", ["en:yogurts"])
    unknown = product("Yaourt nature", "Unknown", ["en:yogurts"], sold=None)
    unavailable = product("Yaourt nature", "US Brand", ["en:yogurts"], sold=False)
    unknown["barcode"], unavailable["barcode"] = "unknown-code", "unavailable-code"   # distinct from the original, or they are skipped as "the same product"
    result = engine.choose(original, [unknown, unavailable], ["overall"], [], None, "similar", 5)
    assert result["alternatives"] == []
    assert result["excluded"]["not_in_france"] == 2


def test_incompatible_capsule_systems_and_coffee_forms_remain_rejected():
    nespresso = product("Nespresso intenso", "Brand A", ["en:coffee-capsules"])
    dolce = product("Dolce Gusto intenso", "Brand B", ["en:coffee-capsules"])
    ground = product("Café moulu", "Brand C", ["en:ground-coffees"])
    beans = product("Café en grains", "Brand D", ["en:coffee-beans"])
    assert taxonomy.substitution(nespresso, dolce) is None
    assert taxonomy.substitution(ground, beans)["level"] >= 3


def test_pack_sizes_deduplicate_as_one_product():
    original = product("Yaourt nature", "Danone", ["en:yogurts"])
    first = product("Nature", "Carrefour", ["en:yogurts"])
    second = product("Nature", "Carrefour", ["en:yogurts"])
    second["barcode"] = "second-pack"
    second["id"] = "second-pack"
    second["quantity"] = {"amount": 1, "unit": "kg"}
    result = engine.choose(original, [first, second], ["overall"], [], None, "similar", 5)
    assert len(result["alternatives"]) == 1
    assert result["alternatives"][0]["other_sizes"] == 1
