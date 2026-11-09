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
    assert sub(a, b) is None       # a shared category leaf alone is not proof of substitutability
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
    orig = P("Yaourt nature", ["en:dairies", "en:yogurts", "en:plain-yogurts"], sugars100g=6)
    near = [P(f"Yaourt nature proche {i}", ["en:dairies", "en:yogurts", "en:plain-yogurts"]) for i in range(3)]
    broad = [P("Yaourt aux fruits large", ["en:dairies", "en:yogurts", "en:flavoured-yogurts"])]
    for i, x in enumerate(near + broad):
        x["barcode"] = f"b{i}"
    orig["barcode"] = "orig"
    prices = {x["barcode"]: 20.0 for x in near + broad}
    r = engine.build_rankings(orig, near + broad, prices, 50.0, ["value"], "similar", "fr", [])
    names = [x["product"]["name"] for k in ("budget", "value", "quality") for x in r[k]]
    assert "Yaourt aux fruits large" not in names     # a broader kind of yogurt never enters a money or quality tab


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


def test_repeated_idempotency_key_replays_the_first_answer():
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    h = {"X-Session-Id": "idem-session-1", "Idempotency-Key": "k-1"}
    a = c.post("/v1/auth/register", json={"email": "idem1@example.com", "password": "Passw0rd!x"}, headers=h)
    b = c.post("/v1/auth/register", json={"email": "idem1@example.com", "password": "Passw0rd!x"}, headers=h)
    assert a.status_code < 400 and b.status_code == a.status_code and b.headers.get("Idempotent-Replay") == "true"


def test_marks_and_spencer_products_are_never_candidates():
    from app import main
    ok = {"product_name": "Biscuits", "brands": "Lu", "countries_tags": ["en:france"], "categories_tags": ["en:biscuits"]}
    assert main._raw_candidate(ok, [], [], {"categories": ["en:biscuits"]})
    for brand in ("Marks & Spencer", "Marks and Spencer", "M&S Food"):
        assert not main._raw_candidate({**ok, "brands": brand}, [], [], {"categories": ["en:biscuits"]}), brand


def test_french_tagged_chocolate_spreads_match_each_other():
    from app import taxonomy
    tags = ["en:snacks", "en:cocoa-and-its-products", "en:chocolates", "en:petit-dejeuners", "en:produits-a-tartiner", "en:pates-a-tartiner", "en:pates-a-tartiner-aux-noisettes-et-au-cacao"]
    a = {"name": "Nutella", "categories": tags}
    b = {"name": "Pâte à tartiner noisettes cacao", "brand": "Carrefour", "categories": tags}
    assert taxonomy.classify(a)["type"] == "chocolate_spread" and taxonomy.classify(a)["confidence"] in ("high", "medium")
    assert taxonomy.substitution(a, b)["level"] == 1


def test_brand_chains_fill_in_chains_for_a_known_brand(tmp_path, monkeypatch):
    import json
    from app import main
    f = tmp_path / "bc.json"
    f.write_text(json.dumps([{"rank": 1, "brand": "bonne maman", "scans": 5, "chains": [{"chain": "Carrefour", "products": 100}, {"chain": "Auchan", "products": 60}, {"chain": "Lidl", "products": 2}]}]))
    monkeypatch.setenv("BRAND_CHAINS", str(f)); monkeypatch.setattr(main, "_BRAND_CHAINS", None)
    assert main._brand_chain_ids("Bonne Maman") == ["carrefour", "auchan"]     # Lidl's 2 sightings are noise
    assert main._brand_chain_ids("Unknown brand") == []


def test_closest_list_prefers_priced_products_among_equally_close_ones():
    base = {"categories": ["en:dairies", "en:yogurts", "en:plain-yogurts"], "nutriments": {"energyKcal100g": 60, "sugars100g": 4}}
    o = {**base, "barcode": "o", "name": "Yaourt nature", "brand": "A", "score": {"total": 70}}
    nop = {**base, "barcode": "n", "name": "Yaourt nature bio", "brand": "B", "score": {"total": 70}}
    yes = {**base, "barcode": "y", "name": "Yaourt nature bio", "brand": "C", "score": {"total": 70}}
    out = engine.rank_closest(o, [nop, yes], {"y": 150.0}, {"y": {"source": "open_prices", "date": "2026-11-08"}})
    assert [e["product"]["barcode"] for e in out][0] == "y"


def test_pack_size_is_read_from_the_name_when_the_record_has_none():
    from app.products import normalize
    q = normalize({"code": "3770011743131", "product_name": "Barre Energy beurre cacahuètes chocolat 50g", "categories_tags": ["en:snacks"], "nutriments": {}})["quantity"]
    assert q == {"amount": 50.0, "unit": "g"}
    assert normalize({"code": "1", "product_name": "Barre", "quantity": "6 x 25 g", "categories_tags": ["en:snacks"], "nutriments": {}})["quantity"]["amount"] == 150.0


def test_pantry_staples_have_their_own_types():
    from app import taxonomy
    cases = [("Pesto alla genovese", ["en:sauces", "en:green-pestos"], "pesto"), ("Sauce soja salée", ["en:soy-sauces"], "soy_sauce"),
             ("Cacao maigre en poudre", ["en:cocoa-powders"], "cocoa_powder"), ("Sucre en poudre", ["en:sugars", "en:white-sugars"], "sugar"),
             ("Sirop d'agave bio", ["en:agave-syrups"], "syrup"), ("Truite fumée", ["en:smoked-trouts"], "smoked_fish")]
    for name, cats, tid in cases:
        assert taxonomy.classify({"name": name, "categories": cats})["type"] == tid, name
    pesto, soy = cases[0], cases[1]
    assert taxonomy.substitution({"name": pesto[0], "categories": pesto[1]}, {"name": "Pesto rosso", "categories": ["en:red-pestos"]})["level"] == 1
    assert taxonomy.substitution({"name": pesto[0], "categories": pesto[1]}, {"name": soy[0], "categories": soy[1]}) is None


def _install_reference():
    from app import value_index
    score_q = [float(x) for x in range(10, 91, 2)]          # 41 quantiles: scores 10..90
    price_q = [20.0 + 5.0 * i for i in range(41)]            # 20..220 cents per 100 g
    value_index.set_reference({"toy": {"n": 500, "score_q": score_q, "price_q": price_q}})
    return value_index


def test_price_quality_score_needs_both_quality_and_low_price():
    vi = _install_reference()
    try:
        cheap_good = vi.value_index("toy", 85, 40)["value_score"]
        cheap_poor = vi.value_index("toy", 15, 40)["value_score"]
        dear_good = vi.value_index("toy", 85, 200)["value_score"]
        assert cheap_good > 75 and cheap_poor < 35 and dear_good < 35
        assert vi.value_index("toy", 60, 40)["value_score"] > vi.value_index("toy", 60, 120)["value_score"]       # cheaper is better at equal quality
        assert vi.value_index("toy", 80, 100)["value_score"] > vi.value_index("toy", 50, 100)["value_score"]     # better is better at equal price
    finally:
        vi.set_reference(None)


def test_price_quality_score_is_stable_and_damped_for_poor_nutrition():
    vi = _install_reference()
    try:
        assert vi.value_index("toy", 70, 60) == vi.value_index("toy", 70, 60)          # no dependence on any search
        assert vi.value_index("unknown type", 70, 60) is None and vi.value_index("toy", None, 60) is None and vi.value_index("toy", 70, 0) is None
        # same percentile position, but the weak product is scaled down
        assert vi.damping(20) < vi.damping(65) == 1.0
    finally:
        vi.set_reference(None)


def test_nutrition_given_only_per_serving_or_as_plain_energy_still_scores():
    from app.products import normalize
    base = {"code": "3000000000001", "product_name": "Compote myrtille", "categories_tags": ["en:fruit-compotes"], "serving_quantity": 100}
    per_serving = normalize({**base, "nutriments": {"energy-kcal_serving": 80, "sugars_serving": 14, "saturated-fat_serving": 0.1, "salt_serving": 0.02}})
    assert per_serving["nutriments"]["energyKcal100g"] == 80 and per_serving["nutriments"]["sugars100g"] == 14 and per_serving["score"] is not None
    plain = normalize({**base, "nutriments": {"energy_100g": 335, "sugars_100g": 14, "salt_100g": 0.02, "saturated-fat_100g": 0.1}})
    assert round(plain["nutriments"]["energyKcal100g"]) == 80


def test_value_list_does_not_require_beating_the_scanned_product():
    base = {"categories": ["en:dairies", "en:yogurts", "en:plain-yogurts"], "nutriments": {"energyKcal100g": 60, "sugars100g": 4, "carbohydrates100g": 5}}
    o = {**base, "barcode": "o", "name": "Yaourt nature top", "brand": "A", "score": {"total": 92}}
    c = {**base, "barcode": "c", "name": "Yaourt nature simple", "brand": "B", "score": {"total": 70}}
    pts = {"c": {"source": "open_prices", "date": "2026-11-01"}}
    r = engine.rank_best_value(o, [c], {"c": 100.0}, 80.0, pts)
    assert [x["product"]["barcode"] for x in r["items"]] == ["c"]       # a worse-scoring but priced alternative still appears, labelled by the flag below
    assert r["items"][0]["better_than_yours"] in (True, False, None) and "value_detail" in r["items"][0]


def test_search_price_needs_two_sites_that_mention_the_pack_size(monkeypatch, tmp_path):
    from app import webprice
    monkeypatch.delenv("GEMINI_API_KEY", raising=False); monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.setenv("PARALLEL_API_KEY", "k"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp3.db"))
    assert webprice.providers() == ["parallel"]
    prod = {"barcode": "3017620422003", "name": "Nutella pâte à tartiner", "brand": "Ferrero", "quantity": {"amount": 400.0, "unit": "g"}}

    def par(*rs):
        def http(method, url, headers, body):
            assert url == "https://api.parallel.ai/v1/search" and headers["x-api-key"] == "k" and body["search_queries"]
            return {"results": [{"title": t_, "excerpts": [d], "url": u} for t_, d, u in rs]}
        return http
    good = par(("Ferrero Nutella 400 g", "Pâte à tartiner Nutella Ferrero 400 g à 3,20 €", "https://www.auchan.fr/a"),
               ("Nutella Ferrero 400g", "prix 3,35 € le pot de 400 g, 8,37 €/kg", "https://www.carrefour.fr/b"),
               ("Ferrero Nutella 825 g", "grand pot 6,50 €", "https://www.leclerc.fr/c"))
    r = webprice.lookup(prod, use_cache=False, http=good)
    assert r and r["pack_cents"] in (320, 335) and r["approximate"] and r["provider"] == "parallel" and r["per100_cents"] == round(r["pack_cents"] / 400 * 100, 1)
    assert webprice.lookup(prod, use_cache=False, http=par(("Ferrero Nutella 400 g", "à 3,20 €", "https://www.auchan.fr/a"))) is None          # one site is not enough
    assert webprice.lookup(prod, use_cache=False, http=par(("Ferrero Nutella 825 g", "6,50 €", "https://a.fr/x"), ("Ferrero Nutella 825 g", "6,40 €", "https://b.fr/y"))) is None   # other size
    assert webprice.lookup(prod, use_cache=False, http=par(("Ferrero Nutella 400 g", "3,20 €", "https://a.fr/x"), ("Ferrero Nutella 400 g", "9,90 €", "https://b.fr/y"))) is None    # disagreement
    monkeypatch.delenv("PARALLEL_API_KEY"); assert webprice.lookup(prod, use_cache=False, http=good) is None                                                          # off without a key


def test_brave_and_gemini_keys_do_not_switch_the_lookup_on(monkeypatch):
    from app import webprice
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False); monkeypatch.setenv("BRAVE_API_KEY", "x"); monkeypatch.setenv("GEMINI_API_KEY", "y")
    assert webprice.providers() == [] and not webprice.enabled()


def test_web_price_is_cached_per_barcode(monkeypatch, tmp_path):
    from app import webprice
    monkeypatch.setenv("PARALLEL_API_KEY", "k"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp5.db"))
    calls = []

    def http(method, url, headers, body):
        calls.append(1)
        return {"results": [{"title": "Biscuits 200 g", "excerpts": ["Biscuits 200 g à 2,00 €"], "url": "https://a.fr/x"}, {"title": "Biscuits 200 g", "excerpts": ["200 g : 2,10 €"], "url": "https://b.fr/y"}]}
    prod = {"barcode": "123456789012", "name": "Biscuits", "brand": "Lu", "quantity": {"amount": 200.0, "unit": "g"}}
    a, b = webprice.lookup(prod, http=http), webprice.lookup(prod, http=http)
    assert a and a == b and len(calls) == 1


def test_price_per_kilo_is_not_mistaken_for_the_pack_price():
    from app import webprice
    assert webprice._pack_price("Piments 29 g : 98,28 € le kilo, 2,85 € le pot", 0.029) == 2.85          # per-kilo price is skipped
    assert webprice._pack_price("Piments 29 g 98,28€ 2,85€", 0.029) == 2.85                                # even unlabelled: 2,85 / 0,029 kg = 98,28
    assert webprice._pack_price("Nutella 400 g à 3,20 € (8,00 €/kg)", 0.4) == 3.20


def test_money_and_quality_lists_prefer_products_shoppers_know():
    base = {"categories": ["en:dairies", "en:yogurts", "en:plain-yogurts"], "nutriments": {"energyKcal100g": 60, "sugars100g": 4, "carbohydrates100g": 5}}

    def prod(code, name, brand, score, scans=0, chains=0):
        return {**base, "barcode": code, "name": name, "brand": brand, "score": {"total": score}, "dataQuality": {"nutritionComplete": True}, "popularity": {"scans": scans, "chains": chains}}
    orig = prod("o", "Yaourt nature", "Z", 60)
    known = [prod(f"k{i}", f"Yaourt nature connu {i}", f"B{i}", 70 + i, scans=200) for i in range(5)]
    obscure = prod("x", "Yaourt nature rare", "Rare", 99, scans=0)
    r = engine.build_rankings(orig, known + [obscure], {f"k{i}": 100.0 + i for i in range(5)}, 150.0, ["value"], "similar", "fr", [])
    assert "x" not in [e["product"]["barcode"] for e in r["quality"]]                       # a 99 nobody has scanned is not the best-quality pick
    thin = engine.build_rankings(orig, known[:2] + [obscure], {"k0": 100.0}, 150.0, ["value"], "similar", "fr", [])
    assert "x" in [e["product"]["barcode"] for e in thin["quality"]]                        # too few known products: the list is not emptied


def test_web_price_endpoints_return_price_and_supermarket(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app import main, webprice
    monkeypatch.setenv("PARALLEL_API_KEY", "k"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp9.db"))
    monkeypatch.setattr(main.app.state.prices, "latest", lambda *a, **k: None, raising=False)
    fake = {"per100_cents": 80.0, "pack_cents": 320, "store": "Auchan", "stores": ["Auchan", "Carrefour"], "chains": ["auchan", "carrefour"], "source_urls": ["https://a.fr"], "date": "2026-11-08", "source": "web_search", "approximate": True}
    monkeypatch.setattr(webprice, "lookup", lambda p, **k: fake)
    monkeypatch.setattr(main, "load_product", lambda s_, code: {"barcode": code, "name": "Produit", "brand": "X", "quantity": {"amount": 400.0, "unit": "g"}})
    c = TestClient(main.app)
    main.limiter.reset()                         # other tests share the per-minute counters
    h = {"X-Session-Id": "webprice-test-1"}
    r = c.get("/v1/products/3579260039060/web-price", headers=h).json()
    assert r["price"]["stores"] == ["Auchan", "Carrefour"] and r["price"]["approximate"] is True
    r2 = c.post("/v1/web-prices", json={"barcodes": ["3579260039060", "3175680011480"]}, headers=h).json()
    assert set(r2["prices"]) == {"3579260039060", "3175680011480"} and r2["prices"]["3175680011480"]["pack_cents"] == 320
    monkeypatch.delenv("PARALLEL_API_KEY")
    assert c.get("/v1/products/3579260039060/web-price", headers=h).json() == {"price": None}


def test_pizza_sticks_are_breadsticks_not_pizza():
    from app import taxonomy
    c = lambda n, cats: taxonomy.classify({"name": n, "categories": cats, "category": cats[-1] if cats else None}).get("type")   # noqa: E731
    assert c("Clip Pizza Sticks", ["en:snacks", "en:salty-snacks"]) == "breadsticks"
    assert c("Bâtonnets salés apéritif", []) == "breadsticks"
    assert c("Pizza margherita", ["en:pizzas"]) == "pizza"
    assert c("Mozzarella sticks", ["en:cheeses"]) != "breadsticks"


def test_parallel_is_main_and_langsearch_the_fallback(monkeypatch, tmp_path):
    from app import webprice
    monkeypatch.setenv("LANGSEARCH_API_KEY", "ls"); monkeypatch.setenv("PARALLEL_API_KEY", "pa"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp4.db"))
    assert webprice.providers() == ["parallel", "langsearch"]
    prod = {"barcode": "3017620422003", "name": "Nutella pâte à tartiner", "brand": "Ferrero", "quantity": {"amount": 400.0, "unit": "g"}}
    ls_ok = {"data": {"webPages": {"value": [{"name": "Ferrero Nutella 400 g", "url": "https://www.auchan.fr/a", "snippet": "Nutella Ferrero 400 g à 3,20 €"},
                                              {"name": "Nutella Ferrero 400g", "url": "https://www.carrefour.fr/b", "snippet": "prix 3,25 € le pot de 400 g"}]}}}
    par_ok = {"results": [{"title": "Ferrero Nutella 400 g", "excerpts": ["Nutella Ferrero 400 g 3,40 €"], "url": "https://www.leclerc.fr/c"},
                          {"title": "Nutella Ferrero 400g", "excerpts": ["Nutella Ferrero 400 g 3,45 €"], "url": "https://www.intermarche.com/d"}]}
    calls = []

    def http(ls_resp):
        def f(method, url, headers, body):
            calls.append(url)
            if "langsearch" in url:
                assert headers["Authorization"] == "Bearer ls"
                return ls_resp
            return par_ok
        return f
    r = webprice.lookup(prod, use_cache=False, http=http(ls_ok))
    assert r and r["provider"] == "parallel" and calls == ["https://api.parallel.ai/v1/search"]          # Parallel answers first
    calls.clear()
    monkeypatch.setattr(webprice, "_cached", lambda b: (False, None))
    monkeypatch.setattr(webprice, "PARALLEL", "https://api.parallel.ai/none")                              # Parallel gets nothing: LangSearch answers
    def http2(method, url, headers, body):
        calls.append(url)
        return {"results": []} if "parallel" in url else ls_ok
    r = webprice.lookup(prod, use_cache=False, http=http2)
    assert r and r["provider"] == "langsearch" and len(calls) == 2


def test_web_search_has_a_daily_cap_and_never_breaks_the_request(monkeypatch, tmp_path):
    from app import webprice
    monkeypatch.setenv("PARALLEL_API_KEY", "k"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp5.db"))
    prod = {"barcode": "3017620422003", "name": "Nutella pâte à tartiner", "brand": "Ferrero", "quantity": {"amount": 400.0, "unit": "g"}}
    monkeypatch.setattr(webprice, "DAILY_CAP", 0)
    boom = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network down"))     # noqa: E731
    assert webprice.lookup(prod, use_cache=False, http=boom) is None                # over the cap: no search at all
    monkeypatch.setattr(webprice, "DAILY_CAP", 10); webprice._day.update(d="", n=0)
    assert webprice.lookup(prod, use_cache=False, http=boom) is None                # a failing search is an empty answer, not an exception
