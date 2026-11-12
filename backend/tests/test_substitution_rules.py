"""Roadmap checks: the product distinctions the review lists must hold, classification explains itself, money lists use verified prices only, rankings are deterministic."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import engine, taxonomy  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_gemini_state():
    """Every test starts with Gemini available: a failure in one test must not leak its pause into the next."""
    from app import webprice
    webprice._gemini.update(down_until=0.0, error=None)
    yield


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
    a, b = P("Mystère alpha", ["en:odd", "en:odd-leaf"]), P("Énigme beta", ["en:odd", "en:odd-leaf"])
    assert sub(a, b) is None       # a shared category leaf alone is not proof of substitutability
    assert sub(a, P("Mystère gamma", ["en:odd", "en:other-leaf"])) is None
    assert sub(a, P("Mystère gamma", ["en:odd", "en:odd-leaf"])) is not None   # same leaf and a shared name word


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
        u = vi.value_index("unknown type", 70, 60)
        assert u is not None and u["basis"] == "all_products" and u["approximate"] is True        # unknown type: a rougher pooled score, marked approximate
        assert vi.value_index("toy", None, 60) is None and vi.value_index("toy", 70, 0) is None
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
    monkeypatch.setenv("PARALLEL_API_KEY", "k"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "parallel"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp3.db"))
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
    assert webprice.lookup(prod, use_cache=False, http=par(("Ferrero Nutella 400 g", "à 3,20 €", "https://www.auchan.fr/a")))["pack_cents"] == 320   # a supermarket's own page with this exact size is enough
    assert webprice.lookup(prod, use_cache=False, http=par(("Ferrero Nutella 400 g", "à 3,20 €", "https://blog-quelconque.fr/a"))) is None           # a random single page is not
    assert webprice.lookup(prod, use_cache=False, http=par(("Ferrero Nutella 825 g", "6,50 €", "https://a.fr/x"), ("Ferrero Nutella 825 g", "6,40 €", "https://b.fr/y"))) is None   # other size
    assert webprice.lookup(prod, use_cache=False, http=par(("Ferrero Nutella 400 g", "3,20 €", "https://a.fr/x"), ("Ferrero Nutella 400 g", "9,90 €", "https://b.fr/y"))) is None    # disagreement
    monkeypatch.delenv("PARALLEL_API_KEY"); assert webprice.lookup(prod, use_cache=False, http=good) is None                                                          # off without a key


def test_deepseek_built_in_web_search_prices_are_still_verified(monkeypatch, tmp_path):
    from app import webprice
    for k in ("PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY", "WEBPRICE_PROVIDERS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "d"); monkeypatch.setenv("GEMINI_API_KEY", "g")
    webprice._down.clear(); webprice._gemini.update(down_until=0.0, error=None)
    assert webprice.providers() == ["deepseek", "gemini"]          # DeepSeek's own search is asked first
    monkeypatch.setenv("WEBPRICE_PROVIDERS", "deepseek"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp_ds.db"))
    monkeypatch.setattr(webprice, "_page_prices", lambda *a, **k: [])          # no live page fetch from a unit test
    prod = {"barcode": "3017620422003", "name": "Nutella pâte à tartiner", "brand": "Ferrero", "quantity": {"amount": 400.0, "unit": "g"}}
    calls = []

    def http(method, url, headers, body):
        calls.append((method, url, headers, body))
        assert url == "https://api.deepseek.com/v1/tools/search" and headers["Authorization"] == "Bearer d"
        assert 0 < len(body["query"]) <= 128 and body["count"] == 20 and body["need_content"] is False
        return {"results": [
            {"title": "Nutella 400 g", "snippet": "Nutella Ferrero 400 g à 3,20 €", "summary": "Pâte à tartiner", "url": "https://www.auchan.fr/a"},
            {"title": "Nutella Ferrero 400g", "snippet": "3,35 € le pot de 400 g", "summary": "", "url": "https://www.carrefour.fr/b"},
        ]}
    r = webprice.lookup(prod, use_cache=False, http=http)
    assert r and r["provider"] == "deepseek" and r["pack_cents"] in (320, 335) and r["approximate"] and len(calls) >= 1
    single = {"results": [{"title": "Nutella 400 g", "snippet": "Nutella Ferrero 400 g à 3,20 €", "summary": "", "url": "https://www.auchan.fr/a"}]}
    assert webprice.lookup(prod, use_cache=False, http=lambda *a: single)["pack_cents"] == 320     # a supermarket's own page is enough
    unrelated = {"results": [{"title": "Nutella 400 g", "snippet": "Nutella Ferrero 400 g à 3,20 €", "summary": "", "url": "https://blog-quelconque.fr/a"}]}
    assert webprice.lookup(prod, use_cache=False, http=lambda *a: unrelated) is None               # a random single page is not


def test_deepseek_ai_is_the_last_resort_when_the_search_has_no_price(monkeypatch, tmp_path):
    from app import webprice
    for k in ("PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY", "GEMINI_API_KEY", "WEBPRICE_PROVIDERS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "d"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "deepseek")
    monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp_ds_ai.db"))
    monkeypatch.setattr(webprice, "_page_prices", lambda *a, **k: [])
    webprice._down.clear(); webprice._gemini.update(down_until=0.0, error=None)
    prod = {"barcode": "3350033109384", "name": "Poivrons grillés", "brand": "Monoprix", "quantity": {"amount": 280.0, "unit": "g"}}

    def http(method, url, headers, body):
        return {"results": [{"title": "Poivrons grillés 280 g", "snippet": "Poivrons grillés Monoprix 280 g", "summary": "", "url": "https://example.com/p/poivrons"}]}

    def tr(url, body):
        assert url == "https://api.deepseek.com/responses" and body["model"] == "deepseek-v4-pro" and body["tools"] == [{"type": "web_search"}]
        return {"output": [
            {"type": "message", "content": [{"type": "output_text", "text": '{"price_eur": 3.99, "pack_size": "280 g", "store": "Carrefour", "found": true}'}]},
            {"type": "web_search_call", "action": {"type": "open_page", "url": "https://www.carrefour.fr/p/poivrons-grilles#ws_call_id=1"}},
        ]}
    r = webprice.lookup(prod, transport=tr, use_cache=False, http=http)
    assert r and r["provider"] == "deepseek_ai" and r["pack_cents"] == 399 and r["approximate"]
    assert r["source_urls"] == ["https://www.carrefour.fr/p/poivrons-grilles"]          # the page the model opened, without its search marker

    def no_citation(url, body):
        return {"output": [{"type": "message", "content": [{"type": "output_text", "text": '{"price_eur": 3.99, "pack_size": "280 g", "store": "Carrefour", "found": true}'}]}]}
    assert webprice.lookup(prod, transport=no_citation, use_cache=False, http=http) is None   # no opened page: not a sourced price


def test_gemini_is_asked_first_then_the_others(monkeypatch, tmp_path):
    from app import webprice
    for k in ("PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "BRAVE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g"); monkeypatch.setenv("PARALLEL_API_KEY", "p"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "gemini,parallel"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp6.db"))
    assert webprice.providers() == ["gemini", "parallel"]
    monkeypatch.delenv("PARALLEL_API_KEY"); monkeypatch.setenv("BRAVE_API_KEY", "x"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "gemini,brave")
    assert webprice.providers() == ["gemini", "brave"]                          # free-tier search APIs come after Gemini, when explicitly enabled alongside it
    monkeypatch.setenv("PARALLEL_API_KEY", "p"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "gemini,parallel")
    prod = {"barcode": "3017620422003", "name": "Nutella", "brand": "Ferrero", "quantity": {"amount": 400.0, "unit": "g"}}
    reply = {"candidates": [{"content": {"parts": [{"text": '{"price_eur": 3.2, "pack_size": "400 g", "store": "Auchan", "found": true}'}]},
                             "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://www.auchan.fr/a"}}]}}]}
    calls = []

    def tr(url, body):
        calls.append(url)
        return reply
    r = webprice.lookup(prod, transport=tr, use_cache=False, http=lambda *a: (_ for _ in ()).throw(AssertionError("Parallel must not be called")))
    assert r and r["provider"] == "gemini" and r["pack_cents"] == 320 and len(calls) == 1
    def boom(url, body):
        raise RuntimeError("quota")
    par = {"results": [{"title": "Ferrero Nutella 400 g", "excerpts": ["Nutella Ferrero 400 g à 3,20 €"], "url": "https://www.auchan.fr/a"}]}
    r = webprice.lookup(prod, transport=boom, use_cache=False, http=lambda *a: par)              # Gemini fails: Parallel answers
    assert r and r["provider"] == "parallel"


def test_web_price_is_cached_per_barcode(monkeypatch, tmp_path):
    from app import webprice
    monkeypatch.setenv("PARALLEL_API_KEY", "k"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "parallel"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp5.db"))
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
    monkeypatch.setenv("GEMINI_API_KEY", "k"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp9.db"))
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
    monkeypatch.delenv("GEMINI_API_KEY")
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
    monkeypatch.setenv("WEBPRICE_PROVIDERS", "parallel,langsearch")
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


def test_web_prices_are_kept_in_the_price_database_but_not_shown_as_observed(monkeypatch):
    from app import main, db
    s = db.make_session_factory("sqlite:///:memory:")()
    prod = {"barcode": "9990000000017", "quantity": {"amount": 400.0, "unit": "g"}}
    main._record_web_price(s, prod, {"date": "2026-11-09", "pack_cents": 320, "per100_cents": 80.0})
    main._record_web_price(s, prod, {"date": "2026-11-09", "pack_cents": 320, "per100_cents": 80.0})       # same day: not duplicated
    s.commit()
    rows = s.query(db.ProductPrice).filter_by(product_id="9990000000017", source="web_search").all()
    assert len(rows) == 1 and rows[0].confidence == "approximate" and rows[0].per100_cents == 80.0
    assert main._price_history(s, "someone", "9990000000017") == []                                          # never displayed as an observed price
    s.close()


def test_crackers_never_substitute_nuts_or_chips_closely():
    from app import taxonomy
    assert taxonomy.level_between("crackers", "nuts") is None
    assert taxonomy.level_between("crackers", "chips") == 3
    assert taxonomy.level_between("crackers", "breadsticks") == 2


def test_a_second_site_without_the_size_confirms_an_exact_price(monkeypatch):
    from app import webprice
    prod = {"barcode": "3270160850990", "name": "Spécialité à la tomate sechée et au basilic", "brand": "Picard", "quantity": {"amount": 110.0, "unit": "g"}}
    res = [("https://www.picard.fr/produits/a", "Picard Spécialité à la tomate sechée et au basilic 110 g 2,75 €"),
           ("https://fraicheurbio.fr/produit/b", "Spécialité à la tomate séchée et au basilic Picard 2,75 € 2,20 € HT")]
    r = webprice._price_from(prod, res)
    assert r and r["pack_cents"] == 275
    blog = ("https://un-blog.fr/a", "Picard Spécialité à la tomate sechée et au basilic 110 g 2,75 €")                                              # not a supermarket: needs a confirmation
    assert webprice._price_from(prod, [blog]) is None
    assert webprice._price_from(prod, [blog, ("https://autre.fr/c", "Spécialité à la tomate sechée et au basilic Picard 4,10 €")]) is None            # a different price confirms nothing
    assert webprice._price_from(prod, [blog, ("https://autre.fr/c", "Sauce tomate basilic 2,75 €")]) is None                                         # another product confirms nothing
    assert webprice._price_from(prod, [blog, res[1]])["pack_cents"] == 275                                                                            # a matching second page confirms it
    assert webprice._price_from(prod, [res[0]])["pack_cents"] == 275                                                                                  # a supermarket's own page is enough alone


def test_a_per_kilo_price_gives_the_individual_price():
    from app import webprice
    prod = {"barcode": "3270160850990", "name": "Spécialité à la tomate sechée et au basilic", "brand": "Picard", "quantity": {"amount": 110.0, "unit": "g"}}
    res = [("https://www.picard.fr/a", "Picard Spécialité à la tomate sechée et au basilic 110 g – 25,00 €/kg"),
           ("https://www.auchan.fr/b", "Spécialité à la tomate sechée et au basilic Picard 110 g 24,50 € le kilo")]
    r = webprice._price_from(prod, res)
    assert r and r["pack_cents"] in (275, 270)                      # 25 €/kg x 0.11 kg = 2.75 EUR (24,50 x 0.11 = 2.70)
    assert webprice._pack_price("Pâtes 500 g à 3,00 € 6,00 €/kg", 0.5) == 3.0     # a real pack price still wins


def test_readiness_is_ready_and_rate_limit_uses_the_real_client(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    r = c.get("/health/ready")
    assert r.status_code == 200 and r.json()["status"] == "ready" and "price_search" in r.json()
    class Req:
        def __init__(self, h): self.headers, self.client = h, type("C", (), {"host": "10.0.0.1"})()
    assert main.client_ip(Req({"x-forwarded-for": "203.0.113.7, 76.76.21.1", "fly-client-ip": "76.76.21.1"})) == "203.0.113.7"
    assert main.client_ip(Req({"fly-client-ip": "198.51.100.2"})) == "198.51.100.2"


def test_cereal_clusters_with_nuts_are_muesli_not_nuts():
    from app import taxonomy
    cats = ["en:breakfast-cereals", "en:mueslis", "en:cereals-with-nuts", "en:crunchy-cereal-clusters", "en:cereal-clusters-with-nuts"]
    assert taxonomy.classify({"name": "cruesly mélange de noix", "categories": cats, "category": cats[-1]})["type"] == "muesli"
    assert taxonomy.classify({"name": "Noix de cajou grillées", "categories": ["en:nuts", "en:cashew-nuts"], "category": "en:cashew-nuts"})["type"] == "nuts"


def test_tapenade_and_tomato_specialties_are_their_own_type():
    from app import taxonomy
    c = lambda n: taxonomy.classify({"name": n, "categories": [], "category": None})["type"]       # noqa: E731
    assert c("Tapenade De Tomates Séchées") == "tapenade" and c("Spécialité à la tomate sechée et au basilic") == "tapenade"
    assert c("Sauce tomate basilic") != "tapenade"
    a, b = {"name": "Tapenade noire", "categories": [], "category": None}, {"name": "Tapenade verte aux olives", "categories": [], "category": None}
    assert (taxonomy.substitution(a, b) or {}).get("level") == 1


def test_pack_price_ignores_shop_conditions_and_matches_the_per_kilo_price():
    from app import webprice
    page = "Montant du panier 0,00 €. Min 60,00 €. BIENVENUE20 20€ offerts. 125g 34,32 € / kilo 125g (34,32 € / kilo) 4,29 € Ajouter"
    assert webprice._pack_price(page, 0.125) == 4.29


def test_size_is_guessed_from_the_exact_product_page_only(monkeypatch):
    from app import webprice
    monkeypatch.setenv("PARALLEL_API_KEY", "k"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "parallel"); monkeypatch.delenv("GEMINI_API_KEY", raising=False); monkeypatch.delenv("LANGSEARCH_API_KEY", raising=False)
    monkeypatch.setattr(webprice, "_day", {"d": "", "n": 0})
    prod = {"barcode": "3350033972711", "name": "Cerneaux de noix", "brand": "Monoprix", "quantity": None}
    def par(*pages):
        return lambda method, url, headers, body: {"results": [{"title": "", "excerpts": [text], "url": u} for u, text in pages]}
    one = par(("https://courses.monoprix.fr/products/monoprix-cerneaux-de-noix-125g/MPX_1", "125g 34,32 € / kilo 125g 4,29 €"),
              ("https://courses.monoprix.fr/products/maitre-prunille-cerneaux-de-noix-bio-200g/MPX_2", "200g 6,00 €"))      # another brand's page on the same site
    assert webprice._guess_size(prod, one) == {"amount": 125.0, "unit": "g"}
    two = par(("https://courses.monoprix.fr/products/monoprix-cerneaux-de-noix-125g/MPX_1", "125g 4,29 €"),
              ("https://www.auchan.fr/p/monoprix-cerneaux-de-noix-250g", "250g 8,10 €"))
    assert webprice._guess_size(prod, two) == {"amount": 125.0, "unit": "g"}                                 # the pages disagree: the most common size, the smaller one on a tie


def test_a_price_from_another_flavour_or_a_listing_page_is_never_used():
    from app import webprice
    prod = {"barcode": "3760151012464", "name": "Barres au chocolat et orange", "brand": "Dukan", "quantity": {"amount": 150.0, "unit": "g"}}
    wrong_flavour = ("https://www.dukannewboutique.com/produit/barres-au-chocolat-et-noisette", "Dukan Barres au chocolat et noisette 150 g 5,65 € 5,65€ orange")
    listing = ("https://www.carrefour.fr/s?q=dukan", "Dukan barres chocolat orange 150 g 5,65 €")
    assert webprice._price_from(prod, [wrong_flavour, listing]) is None
    right = ("https://www.auchan.fr/dukan-barres-au-chocolat-et-orange/p-1", "Dukan Barres au chocolat et orange 150 g 5,65 €")
    assert webprice._price_from(prod, [right])["pack_cents"] == 565          # a supermarket's own page for exactly this variant


def test_the_default_is_gemini_only_even_with_other_provider_keys_set(monkeypatch):
    """Gemini is the one price search used in production: another provider's key being present (left over, or set for some
    other reason) must never pull it back in on its own. WEBPRICE_PROVIDERS is the only way to use it, for tests or for a
    deliberate, explicit override."""
    from app import webprice
    monkeypatch.delenv("WEBPRICE_PROVIDERS", raising=False)
    monkeypatch.setenv("PARALLEL_API_KEY", "p"); monkeypatch.setenv("SERPER_API_KEY", "s"); monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert webprice.providers() == []
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert webprice.providers() == ["gemini"]
    monkeypatch.setenv("WEBPRICE_PROVIDERS", "serper,parallel")
    assert webprice.providers() == ["serper", "parallel"]                       # an explicit override still works, for tests or a deliberate re-enable



def test_an_interactive_lookup_stops_at_its_deadline_and_does_not_cache_the_timeout_as_a_miss(monkeypatch, tmp_path):
    import time
    from app import webprice
    for k in ("PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp7.db"))
    prod = {"barcode": "3017620422999", "name": "Barre", "brand": "Marque", "quantity": {"amount": 180.0, "unit": "g"}}
    calls = []
    assert webprice.lookup(prod, transport=lambda u, b: calls.append(u), deadline=time.time() - 1) is None
    assert calls == []                                                   # the deadline had passed: no provider was called
    fresh, data = webprice._cached("3017620422999")
    assert not fresh and data is None                                    # a timeout is not remembered as "no price exists"


def test_quick_search_providers_run_before_slow_gemini_and_a_hit_skips_it(monkeypatch, tmp_path):
    from app import webprice
    for k in ("PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "BRAVE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g"); monkeypatch.setenv("SERPER_API_KEY", "s"); monkeypatch.setenv("WEBPRICE_PROVIDERS", "serper,gemini")
    monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp8.db"))
    prod = {"barcode": "3017620422888", "name": "Barres chocolat orange", "brand": "Dukan", "quantity": {"amount": 150.0, "unit": "g"}}
    order = []
    def http(method, url, headers, body):
        order.append("serper")
        return {"organic": [{"link": "https://www.carrefour.fr/p/barres-chocolat-orange-dukan", "snippet": "Dukan Barres chocolat orange 150 g 3,50 €"},
                            {"link": "https://courses.monoprix.fr/p/barres-chocolat-orange-dukan", "snippet": "Dukan Barres chocolat orange 150 g 3,60 €"}]}
    def gemini(url, body, **kw):
        order.append("gemini"); return {}
    out = webprice.lookup(prod, transport=gemini, http=http)
    assert out and out["provider"] == "serper" and order == ["serper"]     # found by the quick search: the slow Gemini call never ran


def test_a_product_with_no_size_still_gets_a_price_from_gemini_with_the_size_it_cites(monkeypatch, tmp_path):
    from app import webprice
    for k in ("PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g"); monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp9.db"))
    prod = {"barcode": "3234750022280", "name": "Caviar d'aubergine au citron et épices", "brand": "Albert Ménès", "quantity": None}
    reply = {"candidates": [{"content": {"parts": [{"text": '{"price_eur": 2.9, "pack_size": "90 g", "store": "Carrefour", "found": true}'}]},
                             "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://www.carrefour.fr/p/caviar"}}]}}]}
    out = webprice.lookup(prod, transport=lambda u, b, **kw: reply)
    assert out and out["pack_cents"] == 290 and out["size_assumed"] == {"amount": 90.0, "unit": "g"}


def test_plural_names_match_and_a_single_product_page_gives_a_price_but_another_pack_size_does_not():
    from app import webprice
    prod = {"barcode": "3234750022280", "name": "Caviar d'aubergine au citron et épices", "brand": "Albert Ménès", "quantity": {"amount": 100.0, "unit": "g"}}
    res = [("https://www.houra.fr/albert-menes-caviar-d-aubergines-au-citron-et-epices-bio-100g/1/", "Albert Ménès Caviar d'Aubergines au Citron et Epices Bio, 100g, , prix : 46,30€/Kg"),
           ("https://www.supermarchesmatch.fr/fr/p/1/albert-menes-caviar-d-aubergines-citron-et-epices", "Albert Ménès : Caviar d'aubergines citron et épices 100 g ; 180 g env. 16,99€/kg")]
    got = webprice._price_from(prod, res)
    assert got and got["pack_cents"] == 463          # 'aubergine' = 'aubergines'; the 180 g price is another pack, so it is ignored


def test_a_page_naming_the_barcode_is_this_exact_pack_and_a_snippet_price_broken_into_pieces_is_repaired():
    from app import webprice
    prod = {"barcode": "3234750022280", "name": "Caviar d'aubergine au citron et épices", "brand": "Albert Ménès", "quantity": {"amount": 100.0, "unit": "g"}}
    res = [("https://www.carrefour.fr/p/caviar-d-aubergines-citron-et-epices-bio-albert-menes-3234750022280", "Caviar D'Aubergines Citron Et Épices Bio ALBERT MENES Drive ou Livraison. 4. ,59. €. 45.90 € / KG."),
           ("https://fr.openfoodfacts.org/produit/3234750022280/caviar", "Caviar d'aubergine au citron et épices – Albert Ménès 3234750022280 4,00 €")]
    got = webprice._price_from(prod, res)
    assert got and got["pack_cents"] == 459 and got["stores"] == ["Carrefour"]      # the barcode in the address: no size needed in the snippet; the database page never counts
    assert webprice._clean("4. ,59. €") == "4,59 €" and webprice._clean("4,59 €") == "4,59 €"


def test_a_multipack_written_with_a_star_is_the_whole_pack():
    from app.value import parse_quantity
    assert parse_quantity("4*125 g") == (500.0, "g") and parse_quantity("6 x 25 g") == (150.0, "g")


def test_the_second_search_wording_uses_the_barcode():
    from app import webprice
    prod = {"barcode": "8001060034785", "name": "Pesto alla genovese", "brand": "Saclà", "quantity": {"amount": 190.0, "unit": "g"}}
    assert webprice._query(prod, 0) == "Saclà Pesto alla genovese 190 g prix €"
    assert webprice._query(prod, 1) == "8001060034785 Saclà prix"
    assert webprice._query({**prod, "barcode": "20386238"}, 1) == "Saclà Pesto alla genovese 190 g prix supermarché drive"   # a short code is too ambiguous to search by


def test_a_chain_from_another_market_is_never_credited_with_selling_a_french_product(monkeypatch):
    from app import webprice
    monkeypatch.setenv("WEBPRICE_PROVIDERS", "serper")
    prod = {"barcode": "3017620422888", "name": "Barres chocolat orange", "brand": "Dukan", "quantity": {"amount": 150.0, "unit": "g"}}
    res = [("https://www.carrefour.fr/p/barres-chocolat-orange-dukan", "Dukan Barres chocolat orange 150 g 3,50 €"),
           ("https://www.target.com/p/dukan-barres-chocolat-orange-150g", "Dukan Barres chocolat orange 150 g $3.60")]
    got = webprice._price_from(prod, res)
    assert got is None or "target" not in [s.lower() for s in (got.get("stores") or [])]    # a single French source with no second agreeing French one: no price
    stores, chains = webprice._extract_grocers(prod, res)
    assert "target" not in [c.lower() for c in chains] and not any("target" in s.lower() for s in stores)


def test_a_price_right_before_a_free_delivery_threshold_is_never_read_as_the_product_price():
    from app import webprice
    text = "Dukan Barre Orange Nappage Chocolat 6 Acheter ici ! Livraison GRATUITE 24H àpd 39€, Expre"
    assert webprice._pack_price(text, 150 / 1000, (150, "g")) is None


def test_a_barcode_match_still_skips_a_category_or_search_page():
    from app import webprice
    prod = {"barcode": "3017620422888", "name": "Barres chocolat orange", "brand": "Dukan", "quantity": {"amount": 150.0, "unit": "g"}}
    res = [("https://www.exemple.fr/categorie/barres?q=dukan", "Toutes les barres Dukan 3017620422888 à partir de 2,50 €"),
           ("https://www.carrefour.fr/p/barres-chocolat-orange-dukan-3017620422888", "Dukan Barres chocolat orange 150 g 3,50 €"),
           ("https://courses.monoprix.fr/p/dukan-barres-chocolat-orange-3017620422888", "Dukan Barres chocolat orange 150 g 3,55 €")]
    got = webprice._price_from(prod, res)
    assert got and 349 <= got["pack_cents"] <= 356    # the category page (barcode among many) never contributes; Carrefour + Monoprix agree


def test_extract_grocers_never_invents_a_chain_from_an_unrelated_site():
    from app import webprice
    prod = {"barcode": "3017620422888", "name": "Barres chocolat orange", "brand": "Dukan", "quantity": {"amount": 150.0, "unit": "g"}}
    res = [("https://www.idealo.fr/compare/dukan-barres-chocolat-orange", "Dukan Barres chocolat orange 150 g comparatif de prix"),
           ("https://www.youtube.com/watch?v=xyz", "Dukan Barres chocolat orange 150 g : notre avis")]
    stores, chains = webprice._extract_grocers(prod, res)
    assert stores == [] and chains == []    # a comparator and a video site are never shops


def test_a_price_split_across_markdown_lines_or_escaped_is_read_whole():
    from app import webprice
    # a markdown-rendered page (the 'parallel' provider) often escapes the decimal point and puts the fraction on its own line
    assert webprice._clean("Drive ou Livraison\n\n5\n\n,65\n\n€\n\n22\\.60 € / KG") == "Drive ou Livraison\n\n5,65\n\n€\n\n22.60 € / KG"
    prod = {"barcode": "3017620422888", "name": "Café moulu", "brand": "Malongo", "quantity": {"amount": 250.0, "unit": "g"}}
    res = [("https://www.carrefour.fr/p/cafe-moulu-malongo-3017620422888", "Café Moulu MALONGO la boite de 250 g\n\nDrive ou Livraison\n\n5\n\n,65\n\n€\n\n22\\.60 € / KG"),
           ("https://www.monoprix.fr/p/cafe-moulu-malongo", "Malongo Café moulu pur arabica 250g\n\n5\\.61€\n\n22\\.44€ / Kg")]
    got = webprice._price_from(prod, res)
    assert got and 550 <= got["pack_cents"] <= 575          # ~5,6 €, not the bare "65" / "61" a naive read would pick up


def test_a_provider_that_trickles_bytes_past_its_own_timeout_is_abandoned_at_the_wall_clock_cap(monkeypatch):
    import time as _time
    from app import webprice
    monkeypatch.setenv("WEBPRICE_PROVIDERS", "serper")
    prod = {"barcode": "3017620422888", "name": "Barres chocolat orange", "brand": "Dukan", "quantity": {"amount": 150.0, "unit": "g"}}
    def slow_http(method, url, headers, body=None):
        _time.sleep(5)          # longer than the deadline given to lookup(); a socket-level timeout would not catch this
        return {"organic": []}
    t0 = _time.time()
    out = webprice.lookup(prod, use_cache=False, http=slow_http, deadline=_time.time() + 1.5)
    assert out is None and _time.time() - t0 < 3        # abandoned near the 1.5 s deadline, not after the full 5 s sleep


def test_a_background_search_started_for_alternatives_has_the_same_overall_time_budget_as_the_product_page(monkeypatch, tmp_path):
    """Without an overall deadline, a background search can try every provider on both wordings with no ceiling, which is what
    made alternatives rows sit on "Recherche du prix…" far longer than the product page's own, bounded lookup ever would."""
    import time
    from app import main as m, webprice
    monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp10.db"))
    seen = {}

    def fake_lookup(product, **kw):
        seen["deadline"] = kw.get("deadline")
        return None
    monkeypatch.setattr(webprice, "lookup", fake_lookup)
    f = m._search_once({"barcode": "3017620422999", "name": "Produit", "brand": "X", "quantity": {"amount": 100.0, "unit": "g"}}, persist=False, force=True)
    f.result(timeout=5)
    assert seen["deadline"] is not None and seen["deadline"] <= time.time() + 26


def test_a_configured_search_api_stands_in_once_gemini_fails_and_stops_once_it_recovers(monkeypatch, tmp_path):
    """Gemini is tried alone normally; once it fails (its quota, say) the other configured provider is used for the ten
    minutes it is skipped, so a run of searches is not simply empty for that whole window."""
    import time as _time
    from app import webprice
    monkeypatch.delenv("WEBPRICE_PROVIDERS", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g"); monkeypatch.setenv("SERPER_API_KEY", "s")
    monkeypatch.setattr(webprice, "_gemini", {"down_until": 0.0, "error": None})
    assert webprice.providers() == ["gemini"]                                 # normally: Gemini only
    webprice._gemini["down_until"] = _time.time() + 600                       # Gemini just failed
    assert webprice.providers() == ["gemini", "serper"]                       # the configured free-tier API stands in while it is skipped
    webprice._gemini["down_until"] = 0.0                                      # the cooldown passed
    assert webprice.providers() == ["gemini"]                                 # back to Gemini alone


def test_a_search_falls_back_to_serper_within_the_same_lookup_once_gemini_fails(monkeypatch, tmp_path):
    from app import webprice
    monkeypatch.delenv("WEBPRICE_PROVIDERS", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g"); monkeypatch.setenv("SERPER_API_KEY", "s")
    monkeypatch.setattr(webprice, "_gemini", {"down_until": 0.0, "error": None})
    monkeypatch.setattr(webprice, "CACHE_PATH", str(tmp_path / "wp11.db"))
    prod = {"barcode": "3017620422888", "name": "Barres chocolat orange", "brand": "Dukan", "quantity": {"amount": 150.0, "unit": "g"}}

    def gemini(url, body, **kw):
        raise RuntimeError("quota exceeded")

    def http(method, url, headers, body):
        return {"organic": [{"link": "https://www.carrefour.fr/p/barres-chocolat-orange-dukan", "snippet": "Dukan Barres chocolat orange 150 g 3,50 €"},
                            {"link": "https://courses.monoprix.fr/p/barres-chocolat-orange-dukan", "snippet": "Dukan Barres chocolat orange 150 g 3,55 €"}]}
    out = webprice.lookup(prod, use_cache=False, transport=gemini, http=http)
    assert out and out["provider"] == "serper"
    assert webprice._gemini["down_until"] > 0            # the failure is remembered, so the next lookup skips straight to the fallback


def test_gemini_tries_another_model_on_a_retired_one_but_gives_up_at_once_on_a_quota_error(monkeypatch):
    from app import webprice
    import urllib.error
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setattr(webprice, "MODEL", "gemini-retired-model")
    monkeypatch.setattr(webprice, "FALLBACK_MODELS", ("gemini-retired-model", "gemini-flash-latest"))
    prod = {"barcode": "3017620422888", "name": "Produit", "brand": "Marque", "quantity": {"amount": 150.0, "unit": "g"}}
    reply = {"candidates": [{"content": {"parts": [{"text": '{"price_eur": 3.5, "pack_size": "150 g", "store": "Carrefour", "found": true}'}]},
                             "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://www.carrefour.fr/p/x"}}]}}]}
    tried = []

    def transport_404_then_ok(url, body, **kw):
        tried.append(url)
        if "retired" in url:
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        return reply
    out = webprice._gemini_lookup(prod, transport_404_then_ok)
    assert out and out["pack_cents"] == 350 and len(tried) == 2            # the retired model failed; the next one was tried and found the price

    tried.clear()

    def transport_429(url, body, **kw):
        tried.append(url)
        raise urllib.error.HTTPError(url, 429, "quota", {}, None)
    out = webprice._gemini_lookup(prod, transport_429)
    assert out is None and len(tried) == 1                                 # a quota error is account-wide: no point trying a second model


def test_gemini_rejects_a_pack_size_that_contradicts_the_one_already_known(monkeypatch):
    from app import webprice
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    prod = {"barcode": "3017620422888", "name": "Produit", "brand": "Marque", "quantity": {"amount": 150.0, "unit": "g"}}

    def reply_with(pack_size):
        return {"candidates": [{"content": {"parts": [{"text": '{"price_eur": 3.5, "pack_size": "%s", "store": "Carrefour", "found": true}' % pack_size}]},
                                "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://www.carrefour.fr/p/x"}}]}}]}
    agree = webprice._gemini_lookup(prod, lambda u, b, **k: reply_with("150 g"))
    assert agree and agree["pack_cents"] == 350 and agree["per100_cents"] == round(350 / 150 * 100, 1)
    close_enough = webprice._gemini_lookup(prod, lambda u, b, **k: reply_with("155 g"))
    assert close_enough and close_enough["per100_cents"] == round(350 / 150 * 100, 1)        # within 10%: the known size still wins
    contradicts = webprice._gemini_lookup(prod, lambda u, b, **k: reply_with("500 g"))
    assert contradicts is None                                              # names a size nothing like the one already known: not trusted


def test_a_price_comparator_that_merely_lists_the_barcode_is_never_trusted_alone():
    """A barcode match lets a page skip the name/brand/size checks so it can be weighed alongside other sources, but it must
    never, on its own, make an aggregator or listing site count as a confirmed price the way a real shop's own page does."""
    from app import webprice
    prod = {"barcode": "8000500082379", "name": "Nutella", "brand": "Ferrero", "quantity": {"amount": 1000.0, "unit": "g"}}
    comparator = ("https://prices.example.net/fr/product/8000500082379", "8000500082379 6,65 €")
    assert webprice._price_from(prod, [comparator]) is None
    shop_dedicated_page = ("https://www.exampleshop.fr/produit/nutella-ferrero-1kg-pate-a-tartiner", "Nutella Ferrero pâte à tartiner 1 kg 8,49 €")
    assert webprice._price_from(prod, [shop_dedicated_page])["pack_cents"] == 849     # names the product fully in its own address: trusted alone


def test_social_media_and_comparator_sites_never_contribute_a_price():
    from app import webprice
    prod = {"barcode": "8000500082379", "name": "Nutella", "brand": "Ferrero", "quantity": {"amount": 1000.0, "unit": "g"}}
    fb = ("https://www.facebook.com/ELeclercGranville/posts/promo-nutella-1kg", "Nutella Ferrero 1kg -20% 10,00 €")
    idealo = ("https://www.idealo.fr/compare/nutella-1kg", "Nutella Ferrero 1kg comparatif 9,50 €")
    carrefour = ("https://www.carrefour.fr/p/pate-a-tartiner-nutella-ferrero-1kg", "Nutella Ferrero pâte à tartiner 1 kg 7,49 €")
    monoprix = ("https://courses.monoprix.fr/p/nutella-ferrero-1kg", "Nutella Ferrero pâte à tartiner 1 kg 8,69 €")
    assert webprice._price_from(prod, [fb, idealo]) is None                                  # neither is a shop: no price at all
    got = webprice._price_from(prod, [fb, idealo, carrefour, monoprix])
    assert got and got["pack_cents"] in (749, 869) and got["stores"] == ["Carrefour", "Monoprix"]   # only the two real shops count


def test_grilled_vegetables_and_vegetable_puree_are_distinct_from_each_other_and_from_raw_produce():
    """A jarred grilled/marinated vegetable, a smooth cooked purée, and fresh or frozen produce are different preparations
    with different uses: Poivrons grillés and Purée de brocoli must never substitute each other just because both carry
    only the broad 'en:vegetables' tag."""
    poivrons = P("Poivrons grillés", ["en:vegetables"])
    brocoli = P("Purée de brocoli", ["en:vegetables"])
    carottes = P("Carottes vapeur", ["en:vegetables"])
    assert sub(poivrons, brocoli) is None
    assert sub(poivrons, carottes) is None
    assert sub(brocoli, carottes) is None
    assert sub(poivrons, P("Aubergines grillées", ["en:vegetables"]))["level"] == 1          # still substitute each other
    assert sub(brocoli, P("Purée de carotte", ["en:vegetables"]))["level"] == 1
