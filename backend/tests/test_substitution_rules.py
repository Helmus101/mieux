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


def test_speculoos_flavoured_desserts_are_not_speculoos_biscuits():
    for name in ("Pommes morceaux speculoos", "Dessert lacté saveur spéculoos", "Fromage blanc spéculoos", "Céréales spéculoos"):
        assert taxonomy.classify({"name": name, "brand": "X", "categories": []})["type"] != "speculoos", name


def _lvl(p, level):
    return {**p, "substitution": {"level": level}}


def test_money_tabs_use_only_the_closest_kinds_of_product():
    orig = P("Original", ["en:plain-yogurts"], sugars100g=6)
    near = [_lvl(P(f"Proche {i}", ["en:plain-yogurts"]), 1) for i in range(3)]
    broad = [_lvl(P("Large", ["en:plain-yogurts"]), 4), _lvl(P("Moyen", ["en:plain-yogurts"]), 3)]
    prices = {x["name"]: 20.0 for x in near + broad}
    r = engine.build_rankings(orig, near + broad, prices, 50.0, ["value"], "similar", "fr", [])
    names = [x["product"]["name"] for x in r["budget"]]
    assert names and all(n.startswith("Proche") for n in names)           # three close products exist: nothing broader appears
    few = engine.build_rankings(orig, near[:1] + broad, prices, 50.0, ["value"], "similar", "fr", [])
    assert "Large" not in [x["product"]["name"] for x in few["budget"]]   # level 4 never appears, level 3 only when too few are closer


def test_one_brand_cannot_fill_the_top_of_a_tab():
    items = [{"b": "Lotus"}, {"b": "Lotus"}, {"b": "Lotus"}, {"b": "Aldi"}, {"b": "Netto"}, {"b": "Delacre"}, {"b": "Lotus"}]
    out = engine.brand_variety(items, lambda x: x["b"])
    assert [x["b"] for x in out[:5]].count("Lotus") == 2
    assert len(out) == len(items)                                          # nothing is dropped, only reordered
    short = engine.brand_variety([{"b": "Lotus"}] * 3 + [{"b": "Aldi"}], lambda x: x["b"])
    assert [x["b"] for x in short].count("Lotus") == 3                     # when no other brand is left, the same brand fills the list


def test_a_pack_size_without_a_price_takes_the_price_of_its_sibling():
    from app import main
    a, b = P("Spéculoos", ["en:biscuits"]), P("Spéculoos", ["en:biscuits"])
    a["barcode"], b["barcode"] = "pack-small", "pack-big"
    prices, points = {"pack-small": 40.0}, {"pack-small": {"source": "open_prices", "date": "2026-10-01"}}
    main._fill_pack_prices([a, b], prices, points)
    assert prices["pack-big"] == 40.0 and points["pack-big"]["derived"] is True
    est_only = {"pack-small": 40.0}; est_points = {"pack-small": {"source": "estimate", "date": None}}
    main._fill_pack_prices([a, b], est_only, est_points)
    assert "pack-big" not in est_only                                      # estimates are never copied


def test_nuts_keep_shell_and_roast_apart():
    from app import taxonomy
    base = {"categories": ["en:nuts", "en:pistachios"]}
    raw = {**base, "name": "Pistaches décortiquées non grillées"}
    roasted = {**base, "name": "Pistaches grillées"}
    inshell = {**base, "name": "Pistaches en coque grillées"}
    assert taxonomy.substitution(raw, inshell) is None
    assert taxonomy.substitution(raw, roasted)["level"] > taxonomy.substitution(raw, {**base, "name": "Pistaches décortiquées crues"})["level"]


def test_roasted_vs_raw_tradeoff_text_renders():
    from app import engine
    base = {"categories": ["en:nuts", "en:pistachios"], "nutriments": {"energyKcal100g": 600}, "score": {"total": 80}}
    o = {**base, "barcode": "1", "name": "Pistaches non grillées"}
    c = {**base, "barcode": "2", "name": "Pistaches grillées", "brand": "X"}
    from app import taxonomy
    c["substitution"] = taxonomy.substitution(o, c)
    assert c["substitution"]["variant_diff"] == ["raw", "roasted"]
    assert "grillé" in " ".join(engine._tradeoffs(o, c, 0.9, "fr"))


def test_every_variant_has_a_label_in_both_languages():
    from app import taxonomy, i18n
    names = {n for rules in taxonomy._VARIANTS.values() for n, _ in rules} | {"standard", "raw", "roasted", "plain", "salted"}
    for n in names:
        assert "var_" + n in i18n.FR and "var_" + n in i18n.EN, n


def test_snack_bar_rejects_tablet_cake_and_filled_biscuits():
    from app import taxonomy
    bar = {"name": "Barres chocolat noir amandes cranberries & noix de coco", "categories": ["en:snacks", "en:sweet-snacks", "en:bars", "en:cereal-bars"]}
    nope = [
        {"name": "NESTLÉ DESSERT 70% Absolu 170g", "categories": ["en:snacks", "en:sweet-snacks", "en:cocoa-and-its-products", "en:chocolates", "en:dark-chocolates"]},
        {"name": "Gâteau marbré au chocolat", "categories": ["en:snacks", "en:sweet-snacks", "en:biscuits-and-cakes", "en:cakes"]},
        {"name": "Fourrés chocolat lait noisettes", "categories": ["en:snacks", "en:sweet-snacks", "en:biscuits-and-cakes", "en:biscuits"]},
    ]
    for c in nope:
        assert taxonomy.substitution(bar, c) is None, c["name"]
    cereal = {"name": "6 Barres Céréales Pomme Vert", "categories": ["en:snacks", "en:cereal-bars"]}
    assert taxonomy.substitution(bar, cereal)["level"] == 2
    sport = {"name": "Energy sport bar multifruits", "categories": ["en:snacks", "en:energy-bars"]}
    assert taxonomy.substitution(bar, sport)["level"] >= 3


def test_build_rankings_runs_end_to_end_and_keeps_only_close_products():
    from app import engine, taxonomy
    base = {"categories": ["en:snacks", "en:bars", "en:cereal-bars"], "nutriments": {"energyKcal100g": 400, "sugars100g": 10, "carbohydrates100g": 60}}
    orig = {**base, "barcode": "1", "name": "Barres fruits secs amandes", "brand": "A", "score": {"total": 40}}
    cand = {**base, "barcode": "2", "name": "Barres céréales pomme", "brand": "B", "score": {"total": 50}}
    cake = {"barcode": "3", "name": "Gâteau marbré au chocolat", "brand": "C", "categories": ["en:cakes"], "nutriments": {"energyKcal100g": 400}, "score": {"total": 60}}
    r = engine.build_rankings(orig, [cand, cake], {"2": 800.0, "3": 300.0}, 1000.0, ["value"], "similar", "fr", [])
    names = [e["product"]["name"] for k in ("closest", "budget", "quality", "value") for e in r[k]]
    assert "Gâteau marbré au chocolat" not in names


def test_house_brands_point_to_their_chain():
    from app import chains
    for brand, chain in [("Auchan, Auchan Bio", "Auchan"), ("Milbona", "Lidl"), ("Reflets de France", "Carrefour"), ("Monique Ranou", "Intermarché"),
                         ("Nos régions ont du talent", "E.Leclerc"), ("Bien Vu", "Monoprix"), ("Nestlé", None)]:
        assert chains.own_brand_chain(brand) == chain, brand
