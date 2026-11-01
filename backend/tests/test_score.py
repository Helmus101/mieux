from app.products import normalize
from app.score import additive_level, interp, banded, profile_of


def prod(nm, ing, adds=(), cats=("en:snacks",), extra=None):
    raw = {"code": "3000000000001", "product_name": "x", "nutriments": nm, "ingredients_text": ing, "additives_tags": list(adds),
           "categories_tags": list(cats), "countries_tags": ["en:france"]}
    return normalize(raw)


GOOD = {"energy-kcal_100g": 60, "sugars_100g": 4, "saturated-fat_100g": 0.5, "fat_100g": 2, "salt_100g": 0.1, "fiber_100g": 3, "proteins_100g": 8}
BAD = {"energy-kcal_100g": 540, "sugars_100g": 55, "saturated-fat_100g": 11, "fat_100g": 30, "salt_100g": 1.8, "fiber_100g": 1, "proteins_100g": 5}


def dim(p, key):
    return next(d for d in p["score"]["dimensions"] if d["key"] == key)


def test_piecewise_interpolation_and_bands():
    a = banded(5, 22.5)
    assert interp(0, a) == 100 and interp(5, a) == 75 and interp(22.5, a) == 30 and interp(45, a) == 0
    assert 30 < interp(13, a) < 75


def test_good_beats_bad_and_every_dimension_is_visible():
    g, b = prod(GOOD, "lait"), prod(BAD, "sucre, huile de palme")
    assert g["score"]["total"] > b["score"]["total"] and g["score"]["total"] >= 70 and b["score"]["total"] < 45
    assert {d["key"] for d in g["score"]["dimensions"]} == {"fat", "sugar", "salt", "energy", "protein", "fibre", "plant", "micro", "additives", "ingredients"}
    assert g["score"]["version"] == "3.0" and g["score"]["calculatedAt"]
    assert {"nutritional", "ingredient", "processing"} <= set(g["score"])  # the three separate outputs


def test_category_profile_drops_irrelevant_dimensions_and_redistributes():
    oil = prod({**GOOD, "fat_100g": 100, "saturated-fat_100g": 14}, "huile d'olive", cats=("en:fats", "en:olive-oils"))
    assert oil["score"]["profile"] == "oils_fats"
    protein = dim(oil, "protein")
    assert protein["relevant"] is False and protein["missing"] is False
    assert dim(oil, "fat")["detail"]["parts"] and all(x["k"] != "total" for x in dim(oil, "fat")["detail"]["parts"])  # an oil is not penalised for total fat
    assert profile_of(["en:dairies", "en:yogurts"]) == "plain_yogurt" and profile_of(["en:beverages", "en:sodas"]) == "drinks"


def test_missing_relevant_data_marks_score_incomplete_not_irrelevant():
    nm = {k: v for k, v in GOOD.items() if k != "fiber_100g"}
    p = prod(nm, "farine complète, eau", cats=("en:breads",))
    assert dim(p, "fibre")["relevant"] and dim(p, "fibre")["missing"] and p["score"]["incomplete"] and "fibre" in p["score"]["confidence"]["missing"]
    assert p["score"]["confidence"]["pct"] < 100


def test_sugar_origin_natural_is_judged_more_leniently_than_added():
    nm = {**GOOD, "sugars_100g": 12}
    nat, add = prod(nm, "lait entier, ferments"), prod(nm, "lait, sucre")
    assert dim(nat, "sugar")["detail"]["sugar"]["kind"] == "natural" and dim(add, "sugar")["detail"]["sugar"]["kind"] == "mixed"
    assert dim(nat, "sugar")["score"] > dim(add, "sugar")["score"]
    assert prod(nm, "farine, sucre, sirop de glucose")["score"]["sugar"]["added"] == ["sirop", "sucre"] or "sucre" in prod(nm, "farine, sucre, sirop de glucose")["score"]["sugar"]["added"]


def test_additives_levels_a_to_d_and_unknown_is_b_with_low_evidence():
    assert additive_level("e330") == ("A", True) and additive_level("e951") == ("C", True) and additive_level("e250") == ("C", True) and additive_level("e250", True) == ("D", True) and additive_level("e999") == ("B", False)
    clean = prod(GOOD, "lait")
    bad = prod(GOOD, "lait", adds=["en:e250", "en:e951"])
    assert dim(clean, "additives")["score"] == 100 and dim(bad, "additives")["score"] <= 60
    assert additive_level("e171") == ("D", True)                      # titanium dioxide: banned in the EU since 2022
    assert "additive_unknown" in prod(GOOD, "lait", adds=["en:e999"])["score"]["confidence"]["doubts"]


def test_warnings_are_independent_of_the_average():
    p = prod({**GOOD, "salt_100g": 2.0, "saturated-fat_100g": 8}, "farine, sel", cats=("en:snacks",))
    keys = {f["key"] for f in p["score"]["flags"]}
    assert {"high_salt", "high_sat_fat"} <= keys


def test_no_nutrition_data_gives_no_score():
    assert prod({}, "x")["score"] is None


def test_quality_price_prefers_more_quality_per_euro():
    from app.engine import qp
    a = {"score": {"total": 80}}; b = {"score": {"total": 80}}
    assert qp(a, 100) > qp(b, 200)          # same quality, half the price -> twice the quality per euro
    assert qp({"score": None}, 100) is None and qp(a, None) is None
    assert qp(a, 100) == 8.0                # 80 points / 10 euros per kg


def test_value_score_needs_both_quality_and_a_fair_price():
    from app.engine import value_scores
    # four comparable products around 100 (cents per 100 g); yours costs 100
    items = [("good_fair", 80, 100), ("junk_cheap", 20, 40), ("premium_dear", 90, 250), ("good_cheap", 80, 60), ("poor_fair", 30, 100)]
    v = value_scores(items, orig_price=100)
    assert v["good_cheap"] > v["good_fair"] > v["premium_dear"]                 # same quality: cheaper is better, much dearer is worse
    assert v["good_fair"] > v["junk_cheap"] and v["good_fair"] > v["poor_fair"]  # cheap junk and fairly priced poor quality both lose to solid quality at a fair price
    assert all(0 <= x <= 100 for x in v.values())
    assert value_scores([("a", None, 100), ("b", 80, None)], 100) == {"a": None, "b": None}   # unknown quality or price: no score invented


def test_value_score_is_robust_to_an_outlier_price():
    from app.engine import value_scores
    base = [("a", 70, 100), ("b", 70, 110), ("c", 70, 90), ("d", 70, 105)]
    v1 = value_scores(base, orig_price=100)
    v2 = value_scores(base + [("outlier", 70, 4000)], orig_price=100)               # a 40 EUR/100 g gourmet pack
    assert abs(v1["a"] - v2["a"]) <= 3 and abs(v1["c"] - v2["c"]) <= 3               # min-max scaling used to shift everybody by 20+ points here



def test_price_score_is_position_against_the_typical_price():
    from app.engine import price_scores, price_position
    ps = price_scores({"a": 100, "b": 200, "c": 300, "d": 150}, orig_price=150)
    assert ps["a"] > ps["d"] > ps["b"] > ps["c"]                                     # cheaper than typical scores higher
    assert round(price_position(100, 100)) == 50 and round(price_position(40, 100)) == 100 and round(price_position(250, 100)) == 0
    assert price_scores({"a": 100}, orig_price=100)["a"] == 50                      # compared with your own price: neutral



BRIOCHE = {"energy-kcal_100g": 438, "fat_100g": 11, "saturated-fat_100g": 5.4, "sugars_100g": 10, "salt_100g": 1.0, "fiber_100g": 4, "proteins_100g": 14, "carbohydrates_100g": 60}


def test_brioche_toast_is_not_rescued_by_protein_and_additives():
    p = prod(BRIOCHE, "farine de blé, sucre, sirop de glucose, huile de palme, arôme", adds=["en:e300", "en:e471", "en:e481"], cats=("en:breads", "en:toasted-breads"))
    s = p["score"]
    assert s["total"] <= 45 and s["band"] in ("poor", "bad")             # the old model gave 63
    assert s["nutritional"]["score"] <= 40                               # nutrition is the anchor, protein cannot offset it
    assert any(f["key"] == "high_sat_fat" for f in s["flags"])
    assert s["total"] <= s["nutritional"]["score"] + 8                  # clean additives cannot lift the total far above the nutrition
    protein = next(d for d in s["dimensions"] if d["key"] == "protein")
    assert protein["score"] >= 80                                        # protein still shown honestly, it just doesn't mask the rest


def test_reference_products_land_in_sensible_bands():
    oat = prod({"energy-kcal_100g": 45, "fat_100g": 1.5, "saturated-fat_100g": 0.2, "sugars_100g": 4, "salt_100g": 0.1, "fiber_100g": 0.8, "proteins_100g": 0.5}, "eau, avoine", cats=("en:beverages", "en:plant-based-beverages"))
    cola = prod({"energy-kcal_100g": 42, "fat_100g": 0, "saturated-fat_100g": 0, "sugars_100g": 10.6, "salt_100g": 0, "fiber_100g": 0, "proteins_100g": 0}, "eau, sucre, arôme", adds=["en:e150d", "en:e338"], cats=("en:beverages", "en:sodas"))
    lentils = prod({"energy-kcal_100g": 116, "fat_100g": 0.4, "saturated-fat_100g": 0.1, "sugars_100g": 1, "salt_100g": 0.01, "fiber_100g": 8, "proteins_100g": 9}, "lentilles", cats=("en:legumes",))
    yog = prod({"energy-kcal_100g": 60, "fat_100g": 3, "saturated-fat_100g": 2, "sugars_100g": 4.5, "salt_100g": 0.1, "fiber_100g": 0, "proteins_100g": 4}, "lait, ferments", cats=("en:dairies", "en:yogurts"))
    t = {k: v["score"]["total"] for k, v in dict(oat=oat, cola=cola, lentils=lentils, yog=yog).items()}
    assert t["lentils"] >= 75 and t["yog"] >= 65 and t["oat"] >= 60
    assert t["cola"] <= 45 and t["cola"] < t["oat"] < t["lentils"] + 1


def test_desiccated_coconut_matches_yuka_closely_and_shows_amounts_on_scales():
    coco = {"energy-kcal_100g": 682, "fat_100g": 66, "saturated-fat_100g": 59, "sugars_100g": 6.9, "salt_100g": 0.1, "fiber_100g": 15, "proteins_100g": 7.5, "carbohydrates_100g": 8}
    p = prod(coco, "Noix de coco râpée", cats=("en:plant-based-foods", "en:fruits-and-vegetables-based-foods", "en:coconuts"))
    s = p["score"]
    assert 55 <= s["total"] <= 66                                   # Yuka: 60
    sc = {d["key"]: d["scale"] for d in s["dimensions"] if d["scale"]}
    assert sc["fibre"]["value"] == 15 and sc["fibre"]["tier"] == "excellent" and sc["fibre"]["better"] == "more"
    assert sc["fat"]["tier"] == "bad" and sc["energy"]["tier"] == "bad" and sc["salt"]["tier"] == "excellent" and sc["sugar"]["tier"] == "good"
    assert sc["fibre"]["zones"][-1]["to"] == 12 and len(sc["sugar"]["zones"]) == 5


def test_scale_zones_cover_the_axis_and_label_the_amount():
    from app.score import scale_of
    s = scale_of("protein", 7.5, False, "more")
    assert s["tier"] == "good" and s["zones"][0]["from"] == 0 and s["zones"][-1]["to"] == s["max"]
    assert scale_of("sat", 0.5, False, "less")["tier"] == "excellent" and scale_of("sat", 9, False, "less")["tier"] == "bad"
    assert scale_of("salt", None, False, "less") is None


def test_alternatives_stay_in_the_same_product_type():
    from app import engine
    def mk(code, name, cats):
        return normalize({"code": code, "product_name": name, "nutriments": GOOD, "ingredients_text": "farine", "categories_tags": cats, "countries_tags": ["en:france"]})
    orig = mk("3760077537317", "Grissini Torinesi", ["en:plant-based-foods", "en:breads", "en:breadsticks"])
    sticks = [mk(f"30000000000{i}", f"Gressins {i}", ["en:plant-based-foods", "en:breads", "en:breadsticks"]) for i in range(4)]
    buns = mk("3000000000100", "pain Burger complet", ["en:plant-based-foods", "en:breads", "en:hamburger-buns"])
    sliced = mk("3000000000101", "Pain de mie", ["en:plant-based-foods", "en:breads", "en:sliced-breads"])
    kept = engine.type_filter(orig, sticks + [buns, sliced])
    assert {c["barcode"] for c in kept} == {c["barcode"] for c in sticks}          # enough same-type products: only those
    few = engine.type_filter(orig, sticks[:1] + [buns, sliced])
    assert buns["barcode"] not in {c["barcode"] for c in few}                      # parent-only matches must be very similar


def test_tomato_sauce_gets_vegetable_share_as_a_labelled_estimate_and_user_data_replaces_it():
    sauce = {"energy-kcal_100g": 60, "fat_100g": 3.1, "saturated-fat_100g": 0.4, "sugars_100g": 4.4, "salt_100g": 0.9, "fiber_100g": 1.3, "proteins_100g": 1.6}
    p = prod(sauce, None, cats=("en:condiments", "en:sauces", "en:pasta-sauces", "en:tomato-sauces", "en:fruits-and-vegetables-based-foods"))
    s = p["score"]
    assert s["profile"] == "sauces"
    plant = next(d for d in s["dimensions"] if d["key"] == "plant")
    assert plant["relevant"] and plant["scale"]["estimated"] is True and plant["scale"]["value"] == 70 and "plant_estimated" in s["confidence"]["doubts"]
    from app.score import quality
    better = quality(p, False, {"fvn": 90})                              # the user states 90 % vegetables: real data, no longer an estimate
    pl2 = next(d for d in better["dimensions"] if d["key"] == "plant")
    assert pl2["scale"]["estimated"] is False and pl2["scale"]["tier"] == "excellent" and better["total"] > s["total"]


def test_olive_oil_is_judged_on_its_fat_profile_not_like_a_food_with_too_much_saturated_fat():
    evoo = {"energy-kcal_100g": 821, "fat_100g": 91.2, "saturated-fat_100g": 14.0, "sugars_100g": 0, "salt_100g": 0, "fiber_100g": 0, "proteins_100g": 0}
    p = prod(evoo, "huile d'olive vierge extra", cats=("en:fats", "en:vegetable-oils", "en:olive-oils"))
    s = p["score"]
    assert s["profile"] == "oils_fats" and 62 <= s["total"] <= 82                       # Yuka: 72
    fat = next(d for d in s["dimensions"] if d["key"] == "fat")
    assert fat["scale"]["unit"] == "%" and fat["scale"]["tier"] in ("good", "average")       # saturated share of the fat (about 15 %), not 14 g
    assert not [f for f in s["flags"] if f["key"] in ("high_sat_fat", "high_energy")]
    assert all(d["scale"] is None for d in s["dimensions"] if not d["relevant"])         # no scale for dimensions that do not apply
    butter = prod({"energy-kcal_100g": 740, "fat_100g": 82, "saturated-fat_100g": 52, "sugars_100g": 0.6, "salt_100g": 0.05, "fiber_100g": 0, "proteins_100g": 0.7}, "crème, sel", cats=("en:dairies", "en:fats", "en:butters"))
    assert butter["score"]["total"] < s["total"] - 20                                      # a butter-like fat scores far below olive oil


def test_strict_additive_mode_follows_the_yuka_formula_and_sorbate_is_flagged():
    from app.score import additive_level, quality
    assert additive_level("e202") == ("B", True) and additive_level("e202", strict=True) == ("D", True) and additive_level("e330", strict=True)[0] == "A"
    hummus = {"energy-kcal_100g": 277, "fat_100g": 22, "saturated-fat_100g": 3.5, "sugars_100g": 2.3, "salt_100g": 1.2, "fiber_100g": 7.2, "proteins_100g": 6.9}
    p = prod(hummus, "pois chiches, huile, sel, conservateur : sorbate de potassium", adds=["en:e202", "en:e330"], cats=("en:condiments", "en:sauces", "en:dips", "en:hummus"))
    balanced = p["score"]["total"]
    strict = quality(p, False, {**p["scoreInputs"], "strict": True})
    assert strict["mode"] == "strict" and strict["total"] <= 45 and strict["total"] < balanced - 15      # Yuka: 32
    assert any(f["key"] == "additive_d" for f in strict["flags"]) and "additive_d" in strict["caps"]
    clean = quality(prod(hummus, "pois chiches, huile, sel", cats=("en:condiments", "en:sauces")), False, {"strict": True})
    assert clean["total"] > strict["total"] + 15                                                      # the additive is what pulls it down


def test_additive_table_is_complete_consistent_and_cited():
    from app.additives_db import T
    assert len(T) >= 80
    for code, (name, balanced, strict, why) in T.items():
        assert code.startswith("e") and name and why and len(why) > 15, code
        assert balanced in "ABCD" and strict in "ABCD" and strict >= balanced, code      # the precautionary reading is never milder than the evidence-based one
    assert T["e171"][1:3] == ("D", "D") and T["e452"][2] == "D" and T["e330"][1:3] == ("A", "A") and T["e202"][1:3] == ("B", "D")
    assert T["e471"][1:3] == ("B", "D") and T["e481"][1:3] == ("B", "C")                # Yuka rates these emulsifiers high / moderate; the balanced reading stays with the EFSA


def test_strict_mode_caps_nutriscore_d_and_e_at_49_and_uses_yuka_penalties():
    from app.score import quality, d_additives
    assert d_additives(["en:e202"], strict=True)[0] == 0 and d_additives(["en:e407"], strict=True)[0] == 50   # high 0, moderate 50 of the additive score
    assert d_additives(["en:e471"], strict=True)[0] == 0 and d_additives(["en:e481"], strict=True)[0] == 50   # emulsifiers follow Yuka: E471 high, E481 moderate
    choc = {"energy-kcal_100g": 540, "fat_100g": 30, "saturated-fat_100g": 11, "sugars_100g": 45, "salt_100g": 0.1, "fiber_100g": 2, "proteins_100g": 6}
    p = prod(choc, "sucre, huile, noisettes", cats=("en:snacks",))
    s = quality(p, True, {**p["scoreInputs"], "strict": True})                       # organic would add 10 points, still capped by the D/E rule
    assert s["total"] <= 49 and "nutriscore_d_e" in s["caps"]


def test_plant_foods_are_not_mistaken_for_drinks_and_dried_legumes_score_high():
    flag = {"energy-kcal_100g": 319, "fat_100g": 1.5, "saturated-fat_100g": 0.3, "sugars_100g": 2, "salt_100g": 0.02, "fiber_100g": 16, "proteins_100g": 20.6}
    cats = ("en:plant-based-foods-and-beverages", "en:plant-based-foods", "en:seeds", "en:legume-seeds", "en:pulses", "en:dried-flageolet-green-beans")
    p = prod({k: v for k, v in flag.items() if k != "fiber_100g"}, "flageolets", cats=cats)           # fibre unknown, no pack size: the old code read 'beverages' in the tag and called it a drink
    s = p["score"]
    assert s["liquid"] is False and s["profile"] == "legumes"
    assert "high_energy" not in {f["key"] for f in s["flags"]} and s["total"] >= 85                    # Yuka: 100
    from app.score import quality
    assert quality(p, True, {**p["scoreInputs"], "strict": True})["total"] >= 95                       # organic adds 10 points in strict mode


DATES = {"energy-kcal_100g": 287, "sugars_100g": 57, "saturated-fat_100g": 0.1, "fat_100g": 0.4, "salt_100g": 0.05, "fiber_100g": 7.5, "proteins_100g": 2.2}
FRUIT = ("en:fruits-and-vegetables-based-foods", "en:dried-fruits", "en:dates")


def test_dates_without_ingredient_list_are_not_punished_for_natural_sugar():
    p = prod(DATES, None, cats=FRUIT)["score"]
    assert p["total"] >= 65 and not p["caps"]                       # was ~42: unknown sugar was read as added sugar and capped the score
    assert [f["key"] for f in p["flags"]] == ["high_sugar_natural"]  # a mild warning, not a serious weakness
    assert dim(prod(DATES, None, cats=FRUIT), "energy")["scale"]["tone"] in ("g", "g2")  # calories are low impact for a whole fruit
    assert prod(DATES, "Dattes", cats=FRUIT)["score"]["total"] >= 65


def test_drink_sold_by_volume_is_scored_as_a_drink():
    raw = {"code": "3000000000002", "product_name": "Kombucha", "quantity": "75 cl", "product_quantity": 750,
           "nutriments": {"energy-kcal_100g": 11, "sugars_100g": 2.5, "saturated-fat_100g": 0, "fat_100g": 0, "salt_100g": 0, "fiber_100g": 0, "proteins_100g": 0},
           "ingredients_text": "eau, thé, sucre", "categories_tags": ["en:beverages", "en:fermented-drinks", "en:kombuchas"], "countries_tags": ["en:france"]}
    p = normalize(raw)
    assert p["quantity"] == {"amount": 750.0, "unit": "ml"}      # "75 cl" used to be read as 750 g, which scored drinks like solid food
    assert p["score"]["nutritional"]["points"] >= 2 and p["score"]["nutritional"]["score"] < 70   # a sweetened drink is a Nutri-Score C, not a B/A
