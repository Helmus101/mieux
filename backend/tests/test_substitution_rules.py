"""Roadmap checks: the product distinctions the review lists must hold, classification explains itself, money lists use verified prices only, rankings are deterministic."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import engine, taxonomy  # noqa: E402


def P(name, cats, **n):
    return {"barcode": name, "id": name, "name": name, "brand": "Marque", "categories": cats, "nutriments": {"energyKcal100g": 100, "saturatedFat100g": 1, "sugars100g": 5, "salt100g": 0.5, "protein100g": 5, "fiber100g": 2, **n},
            "score": {"total": 60}, "nutriScore": "c", "additives": [], "quantity": {"amount": 500, "unit": "g"}, "novaGroup": 3}


def sub(a, b):
    return taxonomy.substitution(a, b)


def test_distinctions_from_the_roadmap_table():
    capsule_n = P("Capsules Nespresso intenso", ["en:coffee-capsules"])
    capsule_dg = P("Capsules Dolce Gusto lungo", ["en:coffee-capsules"])
    assert sub(capsule_n, capsule_dg) is None                      # incompatible machines
    ground, beans = P("Café moulu classique", ["en:ground-coffees"]), P("Café en grains", ["en:coffee-beans"])
    assert sub(ground, beans)["level"] >= 3                       # beans need a grinder: never 'almost identical'
    assert sub(ground, capsule_n) is None
    rusks, toast = P("Biscottes complètes", ["en:rusks"]), P("Brioche tranchée toastée", ["en:toasted-brioche"])
    assert sub(rusks, toast)["level"] >= 2
    butter = P("Beurre doux", ["en:butters"])
    assert sub(P("Yaourt nature", ["en:plain-yogurts"]), butter) is None


def test_classification_says_why_and_how_sure():
    c = taxonomy.classify(P("Yaourt nature", ["en:yogurts", "en:plain-yogurts"]))
    assert c["type"] == "plain_yogurt" and c["confidence"] in ("high", "medium") and c["reason"]
    u = taxonomy.classify(P("Produit mystère", ["en:something-odd"]))
    assert u["type"] is None and u["confidence"] == "none" and "unclassified" in u["reason"]


def test_unclassified_products_only_match_the_exact_same_leaf():
    a, b = P("Mystère A", ["en:odd", "en:odd-leaf"]), P("Mystère B", ["en:odd", "en:odd-leaf"])
    assert sub(a, b)["level"] == 1
    assert sub(a, P("Mystère C", ["en:odd", "en:other-leaf"])) is None


def test_implausible_data_is_caught():
    assert engine.data_issues(P("ok", ["en:x"])) == []
    assert "nutrition_implausible" in engine.data_issues(P("typo", ["en:x"], fat100g=80, carbohydrates100g=70, protein100g=30))
    assert "sugars_exceed_carbohydrates" in engine.data_issues(P("units", ["en:x"], sugars100g=30, carbohydrates100g=10))


def _rank(estimated=frozenset(), orig_estimated=False):
    orig = P("Original", ["en:plain-yogurts"], sugars100g=6)
    pool = [P("Moins cher", ["en:plain-yogurts"]), P("Estimé", ["en:plain-yogurts"]), P("Plus cher", ["en:plain-yogurts"])]
    prices = {"Moins cher": 20.0, "Estimé": 10.0, "Plus cher": 90.0}
    return engine.build_rankings(orig, pool, prices, 50.0, ["value"], "similar", "fr", [], estimated, orig_estimated)


def test_estimated_prices_never_win_the_money_lists():
    names = lambda r: [x["product"]["name"] for x in r]  # noqa: E731
    r = _rank(frozenset({"Estimé"}))
    assert "Estimé" not in names(r["budget"]) and "Estimé" not in names(r["value"])
    assert "Moins cher" in names(r["budget"])
    assert _rank()["budget"][0]["product"]["name"] == "Estimé"     # the same price, verified, would win
    assert _rank(orig_estimated=True).get("no_baseline") is True   # an estimated price of your own product proves no saving


def test_rankings_are_deterministic():
    a, b = _rank(), _rank()
    key = lambda r: {k: [(x["product"]["name"], x.get("value_score"), x["price_per_100_cents"]) for x in r[k]] for k in ("budget", "value")}  # noqa: E731
    assert key(a) == key(b)
