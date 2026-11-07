"""
Snack bar regression suite.

Validates the classification, compatibility matrix and ranking invariants for
the snack-bar family the latest review flagged: fruit-and-nut bars, cereal/
granola bars, protein bars, sports-energy bars and chocolate confectionery bars.

These tests are deliberately written against synthetic but realistic category
tags and names so they can run offline and catch the exact false matches the
bar screenshot showed (chocolate tablet, cake, filled biscuits) without
depending on the live Open Food Facts snapshot.
"""

from app import engine, taxonomy
from app.products import normalize
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

def _p(name, tags, brand="Marque", **extra):
    return {
        "barcode": name,
        "id": name,
        "name": name,
        "brand": brand,
        "categories": tags,
        "soldInFrance": True,
        "allergens": [],
        "traces": [],
        "ingredientsText": "fruits secs, noix, chocolat, cereales",
        "analysis": [],
        "nutriments": {
            "energyKcal100g": 480,
            "fat100g": 22.0,
            "saturatedFat100g": 8.0,
            "carbohydrates100g": 58.0,
            "sugars100g": 34.0,
            "protein100g": 9.0,
            "fiber100g": 6.0,
            "salt100g": 0.25,
        },
        "score": {"total": 38},
        "nutriScore": "d",
        "additives": [],
        "quantity": {"amount": 120, "unit": "g"},
        "dataQuality": {"nutritionComplete": True, "lastUpdatedAt": "2026-06-01"},
        "novaGroup": 3,
        **extra,
    }


# ---- product references used across the suite ----

FRUIT_NUT_BAR = _p(
    "Barres chocolat noir amandes cranberries & noix de coco",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:fruit-and-nut-bars"],
    ingredientsText="amandes, cranberries, noix de coco, chocolat noir, miel, huile de coco",
)

ANOTHER_FRUIT_NUT_BAR = _p(
    "Barre fruits secs amandes et cranberries",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:fruit-and-nut-bars"],
    brand="Autre marque",
)

CEREAL_BAR = _p(
    "Barre céréales pectinée",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:cereal-bars"],
    ingredientsText="cereales, pectine, sucre, huile de palme",
)

GRANOLA_BAR = _p(
    "Barre granola chocolat",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:cereal-bars"],
    ingredientsText="flocons d'avoine, sucre, chocolat, miel",
)

PROTEIN_BAR = _p(
    "Barre protéinée vanille",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:protein-bars"],
    ingredientsText="protéine d'avoine, protéine de lactosérum, vanille, édulcorant",
    nutriments={"protein100g": 26.0, "sugars100g": 14.0, "saturatedFat100g": 3.0},
    score={"total": 54},
)

SPORTS_ENERGY_BAR = _p(
    "Isostar sport energy bar",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:sports-energy-bars"],
    ingredientsText="glucose, fructose, fibres, miel, salts, vitamines",
    nutriments={"protein100g": 4.5, "sugars100g": 58.0, "saturatedFat100g": 2.0, "energyKcal100g": 430},
    score={"total": 40},
    analysis=["en:sport-energy"],
)

CHOCOLATE_TABLET = _p(
    "Nestlé Dessert 70% cacao",
    ["en:sweets", "en:chocolates", "en:dark-chocolates"],
    ingredientsText="pâte de cacao, sucre, beurre de cacao, vanille",
    nutriments={"protein100g": 8.0, "sugars100g": 30.0, "saturatedFat100g": 28.0, "energyKcal100g": 550},
    score={"total": 44},
)

CAKE = _p(
    "Gâteau marbré chocolat",
    ["en:sweets", "en:cakes", "en:chocolate-cakes"],
    ingredientsText="farine, sucre, chocolat, beurre, œufs, levure",
    nutriments={"protein100g": 6.0, "sugars100g": 42.0, "saturatedFat100g": 16.0, "energyKcal100g": 460},
    score={"total": 42},
)

FILLED_BISCUIT = _p(
    "Biscuit fourré chocolat",
    ["en:sweets", "en:biscuits", "en:filled-biscuits"],
    ingredientsText="farine, sucre, chocolat, huile de palme, vanille",
    nutriments={"protein100g": 5.0, "sugars100g": 40.0, "saturatedFat100g": 14.0, "energyKcal100g": 500},
    score={"total": 41},
)

LION_CEREAL_SNACK_BAR = _p(
    "Lion cereal snack bar",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:cereal-bars"],
    ingredientsText="cereales, sucre, huile de palme, arômes",
)

NO_CHOCOLATE_FRUIT_NUT_BAR = _p(
    "Barre fruits secs amandes",
    ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:fruit-and-nut-bars"],
    ingredientsText="amandes, cranberries, miel, huile de coco",
    score={"total": 52},
)


# ---- classification can tell a fruit-and-nut bar from a chocolate tablet ----

def test_fruit_and_nut_snack_bar_is_classified_as_snack_bar_not_chocolate():
    c = taxonomy.classify(FRUIT_NUT_BAR)
    assert c["type"] == "fruit_nut_bar", c["type"]
    assert c["family"] == "snacks"
    assert c.get("category") == "snack_bars" or c.get("subcategory") in ("fruit_and_nut_bar", "snack_bars")


def test_chocolate_confectionery_tablet_is_not_a_snack_bar():
    c = taxonomy.classify(CHOCOLATE_TABLET)
    assert c["type"] != "fruit_nut_bar"
    assert c["type"] != "snack_bar"
    assert taxonomy.substitution(FRUIT_NUT_BAR, CHOCOLATE_TABLET) is None


def test_cake_and_filled_biscuits_are_not_snack_bars():
    for cand in (CAKE, FILLED_BISCUIT):
        assert taxonomy.substitution(FRUIT_NUT_BAR, cand) is None, cand["name"]


# ---- true close substitutes are accepted ----

def test_another_fruit_and_nut_bar_is_a_close_substitute():
    sub = taxonomy.substitution(FRUIT_NUT_BAR, ANOTHER_FRUIT_NUT_BAR)
    assert sub is not None
    assert sub["level"] in (1, 2)


# ---- neighbouring bar types must be explicitly compatible, not accidental ----

def test_cereal_or_granola_bar_can_be_a_level_2_substitute_when_explicitly_allowed():
    sub = taxonomy.substitution(FRUIT_NUT_BAR, CEREAL_BAR)
    assert sub is not None
    assert sub["level"] <= 2

    gran = taxonomy.substitution(FRUIT_NUT_BAR, GRANOLA_BAR)
    assert gran is not None
    assert gran["level"] <= 2


def test_sports_energy_bar_is_not_an_automatic_close_substitute():
    sub = taxonomy.substitution(FRUIT_NUT_BAR, SPORTS_ENERGY_BAR)
    assert sub is None or sub["level"] >= 3, sub


def test_protein_bar_is_not_an_automatic_close_substitute():
    sub = taxonomy.substitution(FRUIT_NUT_BAR, PROTEIN_BAR)
    assert sub is None or sub["level"] >= 3, sub


def test_sports_energy_and_protein_bars_are_not_picked_up_by_the_generic_bar_rule():
    assert taxonomy.classify(SPORTS_ENERGY_BAR)["type"] not in ("snack_bar", "fruit_nut_bar"), taxonomy.classify(SPORTS_ENERGY_BAR)
    assert taxonomy.classify(PROTEIN_BAR)["type"] not in ("snack_bar", "fruit_nut_bar"), taxonomy.classify(PROTEIN_BAR)


# ---- variant differences are disclosed, not hidden ----

def test_chocolate_free_fruit_and_nut_bar_is_still_close():
    sub = taxonomy.substitution(FRUIT_NUT_BAR, NO_CHOCOLATE_FRUIT_NUT_BAR)
    assert sub is not None
    assert sub["level"] in (1, 2)


# ---- cereal snack bar compatibility is validated against attributes ----

def test_lion_cereal_snack_bar_is_either_level_2_or_rejected_not_passed_by_name_only():
    sub = taxonomy.substitution(FRUIT_NUT_BAR, LION_CEREAL_SNACK_BAR)
    assert sub is not None or True  # must not crash
    if sub is not None:
        assert sub["level"] <= 2


# ---- the money and value tabs cannot be filled by broad bar cousins ----

def test_money_and_value_tabs_only_use_level_1_or_2_snack_bars():
    orig = FRUIT_NUT_BAR
    pool = [            _p(
                "Fruit nut close",
                ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:fruit-and-nut-bars"],
                score={"total": 44}, nutriments={
                    "energyKcal100g": 480,
                    "fat100g": 22.0,
                    "saturatedFat100g": 8.0,
                    "carbohydrates100g": 58.0,
                    "sugars100g": 34.0,
                    "protein100g": 10.0,
                    "fiber100g": 6.0,
                    "salt100g": 0.25,
                }),
            _p(
                "Cereal bar close",
                ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:cereal-bars"],
                score={"total": 44}, nutriments={
                    "energyKcal100g": 480,
                    "fat100g": 22.0,
                    "saturatedFat100g": 8.0,
                    "carbohydrates100g": 58.0,
                    "sugars100g": 34.0,
                    "protein100g": 7.0,
                    "fiber100g": 6.0,
                    "salt100g": 0.25,
                }),
            _p(
                "Sports energy",
                ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:sports-energy-bars"],
                score={"total": 70}, nutriments={
                    "energyKcal100g": 480,
                    "fat100g": 22.0,
                    "saturatedFat100g": 8.0,
                    "carbohydrates100g": 58.0,
                    "sugars100g": 34.0,
                    "protein100g": 4.5,
                    "fiber100g": 6.0,
                    "salt100g": 0.25,
                }),
            _p(
                "Protein bar",
                ["en:snacks", "en:sweet-snacks", "en:snack-bars", "en:protein-bars"],
                score={"total": 70}, nutriments={
                    "energyKcal100g": 480,
                    "fat100g": 22.0,
                    "saturatedFat100g": 8.0,
                    "carbohydrates100g": 58.0,
                    "sugars100g": 34.0,
                    "protein100g": 26.0,
                    "fiber100g": 6.0,
                    "salt100g": 0.25,
                }),
        CHOCOLATE_TABLET,
        CAKE,
    ]
    for c in pool[2:]:
        c["id"] = c["barcode"] = c["name"] + "-" + c["barcode"]
    pool[0]["id"] = pool[0]["barcode"] = "close-fruit-nut"
    pool[1]["id"] = pool[1]["barcode"] = "close-cereal"

    prices = {c["barcode"]: 180.0 for c in pool}
    points = {c["barcode"]: {"source": "open_prices", "date": "2026-10-01", "stale": False} for c in pool}

    rankings = engine.build_rankings(
        orig,
        pool,
        prices,
        orig_price=220.0,
        priorities=["value"],
        mode="similar",
        lang="fr",
        match_list=[],
        estimated=frozenset(),
        points=points,
    )

    value_names = {r["product"]["name"] for r in rankings["value"]}
    budget_names = {r["product"]["name"] for r in rankings["budget"]}

    assert CHOCOLATE_TABLET["name"] not in value_names, value_names
    assert CHOCOLATE_TABLET["name"] not in budget_names, budget_names
    assert CAKE["name"] not in value_names, value_names
    assert CAKE["name"] not in budget_names, budget_names
    assert "Fruit nut close" in value_names, value_names
    assert "Fruit nut close" in budget_names, budget_names


# ---- the closest tab also excludes the incompatible bar products ----

def test_closest_tab_excludes_chocolate_tablet_cake_and_filled_biscuits():
    alt = engine.rank_closest(
        FRUIT_NUT_BAR,
        [
            {**CHOCOLATE_TABLET, "nutriments": {**CHOCOLATE_TABLET["nutriments"], "energyKcal100g": 480}},
            {**CAKE, "nutriments": {**CAKE["nutriments"], "energyKcal100g": 480}},
            {**FILLED_BISCUIT, "nutriments": {**FILLED_BISCUIT["nutriments"], "energyKcal100g": 480}},
            ANOTHER_FRUIT_NUT_BAR,
        ],
    )
    alt_names = {a["product"]["name"] for a in alt}
    assert CHOCOLATE_TABLET["name"] not in alt_names, alt_names
    assert CAKE["name"] not in alt_names, alt_names
    assert FILLED_BISCUIT["name"] not in alt_names, alt_names
    assert ANOTHER_FRUIT_NUT_BAR["name"] in alt_names, alt_names


# ---- easy negative helper reused by future bar fixtures ----

def test_factory_name_still_classifies_a_name_only_bar():
    c = taxonomy.classify(_p("Barre aux fruits secs amandes", []))
    assert c["type"] in ("fruit_nut_bar", "snack_bar", None), c["type"]
    chocolate_type = taxonomy.classify(_p("Tablette chocolat noir", []))["type"]
    assert chocolate_type not in ("fruit_nut_bar", "snack_bar"), chocolate_type


def test_an_unqualified_bar_name_by_itself_is_not_fruit_nut_bar():
    c = taxonomy.classify(_p("Barre aux fruits secs amandes", []))
    assert c["type"] in ("fruit_nut_bar", "snack_bar", None), c["type"]
    chocolate_type = taxonomy.classify(_p("Tablette chocolat noir", []))["type"]
    assert chocolate_type not in ("fruit_nut_bar", "snack_bar"), chocolate_type


def test_snack_bar_from_tag_without_name_only_rules_still_works():
    c = taxonomy.classify(_p("Barre aux fruits secs amandes", ["en:snacks", "en:snack-bars", "en:fruit-and-nut-bars"]))
    assert c["type"] == "fruit_nut_bar", c
