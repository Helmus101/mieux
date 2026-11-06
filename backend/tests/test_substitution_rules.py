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


def test_choose_also_refuses_impossible_data():
    from app.products import normalize

    def real(code, name, protein, fat, carbs):
        return normalize({"code": code, "product_name": name, "brands": "B", "categories_tags": ["en:yogurts", "en:plain-yogurts"], "ingredients_text": "lait",
                          "nutriments": {"energy-kcal_100g": 90, "fat_100g": fat, "saturated-fat_100g": 1, "carbohydrates_100g": carbs, "sugars_100g": 4, "proteins_100g": protein,
                                         "fiber_100g": 0, "salt_100g": 0.1},
                          "allergens_tags": [], "ingredients_analysis_tags": [], "nutriscore_grade": "b", "quantity": "400 g", "countries_tags": ["en:france"]})
    orig, good, bad = real("1", "Original", 3, 2, 8), real("2", "Bon", 9, 2, 8), real("3", "Faute de frappe", 60, 80, 70)
    out = engine.choose(orig, [bad, good], ["protein"], [], None, "similar", 5, lang="en")
    names = [a["product"]["name"] for a in out["alternatives"]]
    assert "Bon" in names and "Faute de frappe" not in names


def test_best_value_is_not_excluded_by_the_sugar_rule_that_limits_cheapest():
    orig = P("Original", ["en:breakfast-cereals"], sugars100g=10)
    sweeter = P("Plus sucré mais bien noté", ["en:breakfast-cereals"], sugars100g=22)   # +12 g: over the cereal limit
    sweeter["score"] = {"total": 66}
    r = engine.build_rankings(orig, [sweeter], {"Plus sucré mais bien noté": 25.0}, 60.0, ["value"], "similar", "fr", [])
    assert not r["budget"]                                  # Cheapest keeps the safeguard
    assert r["value"] and r["value"][0]["product"]["name"] == "Plus sucré mais bien noté"
    assert any("sucres" in x for x in r["value"][0]["tradeoffs"])   # and the cost is shown, not hidden


def test_french_availability_states_are_counted_apart():
    from app.products import normalize

    def real(code, name, sold):
        p = normalize({"code": code, "product_name": name, "brands": "B", "categories_tags": ["en:yogurts", "en:plain-yogurts"], "ingredients_text": "lait",
                       "nutriments": {"energy-kcal_100g": 90, "fat_100g": 2, "saturated-fat_100g": 1, "carbohydrates_100g": 8, "sugars_100g": 4, "proteins_100g": 5 if name == "Original" else 9,
                                      "fiber_100g": 0, "salt_100g": 0.1},
                       "allergens_tags": [], "ingredients_analysis_tags": [], "nutriscore_grade": "b", "quantity": "400 g", "countries_tags": []})
        p["soldInFrance"] = sold
        return p
    out = engine.choose(real("1", "Original", True), [real("2", "Confirmé", True), real("3", "Inconnu", None), real("4", "Étranger", False)], ["protein"], [], None, "similar", 5, lang="en")
    assert [a["product"]["name"] for a in out["alternatives"]] == ["Confirmé"]
    assert out["excluded"]["not_in_france"] == 2 and out["excluded"]["france_unknown"] == 1   # unknown is part of the total, counted apart too


def test_ricola_lozenges_lead_to_lozenges_not_gummies_or_gum():
    ricola = {"name": "Ricola Citron Mélisse", "brand": "Ricola", "categories": ["en:snacks", "en:sweet-snacks", "en:confectioneries", "en:candies"]}
    valda = {"name": "Valda pastilles menthe eucalyptus", "brand": "Valda", "categories": ["en:confectioneries", "en:candies"]}
    gummies = {"name": "Gommes fruits rouges", "brand": "X", "categories": ["en:confectioneries", "en:candies", "en:gummi-candies"]}
    gum = {"name": "Chewing-gum menthe", "brand": "X", "categories": ["en:confectioneries", "en:chewing-gum"]}
    biscuit = {"name": "Petit beurre", "brand": "X", "categories": ["en:biscuits"]}
    assert taxonomy.classify(ricola)["type"] == "herbal_lozenge"
    assert sub(ricola, valda)["level"] == 1
    assert sub(ricola, gummies) is None and sub(ricola, gum) is None and sub(ricola, biscuit) is None


def test_hazelnuts_lead_to_hazelnuts_not_other_nuts_or_snacks():
    hazel = {"name": "Noisettes décortiquées", "brand": "A", "categories": ["en:nuts", "en:hazelnuts"]}
    hazel2 = {"name": "Noisettes grillées", "brand": "B", "categories": ["en:nuts", "en:hazelnuts"]}
    almond = {"name": "Amandes entières", "brand": "C", "categories": ["en:nuts", "en:almonds"]}
    raisins = {"name": "Mélange fruits secs et raisins", "brand": "D", "categories": ["en:nuts", "en:dried-fruits"]}
    spread = {"name": "Pâte à tartiner noisettes et cacao", "brand": "E", "categories": ["en:spreads", "en:chocolate-spreads"]}
    assert sub(hazel, hazel2) is not None
    assert sub(hazel, almond) is None and sub(hazel, raisins) is None
    assert sub(hazel, spread) is None


def test_lotus_biscoff_leads_to_other_speculoos_not_crackers_spreads_or_sweets():
    lotus = {"name": "Spéculoos Biscoff", "brand": "Lotus", "categories": ["en:snacks", "en:sweet-snacks", "en:biscuits-and-cakes", "en:biscuits", "en:crackers"]}
    carrefour = {"name": "Spéculoos original", "brand": "Carrefour", "categories": ["en:biscuits"]}
    bastogne = {"name": "LU Bastogne Original", "brand": "LU", "categories": ["en:biscuits-and-cakes", "en:biscuits"]}
    plain = {"name": "Petit beurre", "brand": "LU", "categories": ["en:biscuits"]}
    cracker = {"name": "Galettes au bon beurre", "brand": "St Michel", "categories": ["en:crackers"]}
    spread = {"name": "Pâte à tartiner spéculoos", "brand": "X", "categories": ["en:spreads", "en:sweet-spreads"]}
    gum = {"name": "Chewing-gum menthe", "brand": "X", "categories": ["en:chewing-gum"]}
    assert taxonomy.classify(lotus)["type"] == "speculoos"
    assert sub(lotus, carrefour)["level"] == 1 and sub(lotus, bastogne)["level"] == 1
    assert sub(lotus, plain)["level"] == 3                     # a plain biscuit is only a broader alternative
    assert sub(lotus, cracker) is None and sub(lotus, gum) is None
    assert sub(lotus, spread) is None or sub(lotus, spread)["level"] >= 4
    assert "speculoos" in taxonomy.search_terms(lotus)
