"""A prepared dish is not an ingredient: the small category must stay small enough to be a true alternative."""
from app import taxonomy


def _type(name, tags):
    return taxonomy.classify({"name": name, "categories": tags}).get("type")


HARD = ["en:dairies", "en:cheeses", "en:hard-cheeses", "en:emmentaler"]


def test_a_dish_that_names_a_cheese_is_not_a_cheese():
    for name in ("Cordons bleus au Comté AOP", "Röstis de légumes et cheddar", "Pavés au blé épinards emmental",
                 "Croque-monsieur au comté", "Gougères au comté", "Tarte au comté",
                 "RIGATONI PESTO PARMESAN BASILIC", "Purée de pommes de terre à l'emmental",
                 "Lay's saveur emmental"):
        assert _type(name, HARD) != "hard_cheese", name


def test_actual_cheese_is_still_cheese():
    for name in ("Emmental râpé", "Comté AOP 18 mois", "Tomme de Savoie", "Parmesan Reggiano"):
        assert _type(name, HARD) == "hard_cheese", name


def test_a_dish_never_substitutes_a_cheese():
    grated = {"name": "Emmental râpé", "categories": HARD}
    dish = {"name": "Röstis de légumes et cheddar", "categories": HARD}
    assert taxonomy.substitution(grated, dish) is None


def test_every_product_gets_a_category():
    # A rule first, then the most specific category tag, then the explicit "uncategorised": never nothing.
    assert _type("Rillettes de canard", ["en:duck-rillettes"]) == "pate_terrine"
    assert _type("Filets de poulet", ["en:chicken-breasts"]) == "chicken"
    assert _type("Bière blonde", ["en:beers"]) == "beer"
    assert _type("Produit mystère", ["en:something-odd"]) == "cat:en:something-odd"
    for name, tags in (("Produit mystère", []), ("Truc sans nom", ["en:groceries"]), ("Machin", ["en:foods"])):
        assert _type(name, tags) == taxonomy.UNCATEGORISED, (name, tags)


def test_uncategorised_products_never_match_on_category_alone():
    a = {"name": "Truc rare", "categories": []}
    b = {"name": "Machin autre", "categories": []}
    assert taxonomy.substitution(a, b) is None
    assert taxonomy.substitution(a, {"name": "Truc rare bio", "categories": []})["level"] == 2   # a shared name word is evidence


def test_a_brand_or_flavour_word_is_never_the_head_noun():
    blueberries = {"name": "Myrtilles sauvages au sirop", "categories": []}
    same = {"name": "Myrtilles sauvages", "categories": ["en:blueberries"]}
    flavoured = {"name": "SOJASUN MYRTILLES 4X100G", "categories": ["en:soy-yogurts"]}
    assert taxonomy.substitution(blueberries, same)["level"] == 2
    assert taxonomy.substitution(blueberries, flavoured) is None


def test_a_category_only_product_never_substitutes_a_typed_one():
    olives = {"name": "Olives vertes dénoyautées", "categories": ["en:olives"]}
    other = {"name": "Machin rare", "categories": ["en:something-odd"]}
    assert taxonomy.is_category_only(other) and not taxonomy.is_category_only(olives)
    assert taxonomy.substitution(olives, other) is None
    assert taxonomy.substitution(other, olives) is None


def test_pantry_and_bakery_buckets_land_in_the_right_category():
    cases = [
        ("Sel fin au piment d'espelette", [], "salt"),
        ("Sucre en poudre", ["en:sugars"], "sugar"),
        ("Mélange d'épices", [], "spices"),
        ("Farine de blé T55", [], "flour"),
        ("Sauce marinière", [], "sauce"),
        ("Sauce tomate basilic", ["en:tomato-sauces"], "tomato_sauce"),
        ("Ketchup Heinz", ["en:ketchups"], "ketchup"),
        ("Mayonnaise", ["en:mayonnaises"], "mayonnaise"),
        ("Tarte aux fraises", [], "tart"),
        ("Quiche lorraine", [], "pizza"),
        ("Pâte feuilletée", [], "dough"),
        ("Pâte à pizza", [], "pizza_dough"),
        ("Pâte à tartiner", [], "chocolate_spread"),
        ("Jus pomme framboise", [], "fruit_juice"),
        ("Cocktail multifruits", [], "fruit_juice"),
        ("Caramel beurre salé", [], "candy"),
        ("Sirop de citron", [], "drink_syrup"),
        ("Pâté de tête persillé", [], "pate_terrine"),
        ("Pommes de terre", [], "potatoes"),
    ]
    for name, tags, want in cases:
        assert _type(name, tags) == want, (name, _type(name, tags), want)


def test_a_cough_syrup_is_not_a_drink_and_a_date_paste_is_not_a_pate():
    assert _type("Sirop pour la toux", []) != "drink_syrup"
    assert _type("Pâte de dattes", []) != "pate_terrine"


OLIVE_TAGS = ["en:pickles", "en:olive-tree-products", "en:plant-based-pickles", "en:olives", "en:marinated-olives", "en:pitted-olives"]


def test_olives_are_their_own_small_category():
    assert _type("Olives à l'andalouse Atelier Blini", OLIVE_TAGS) == "olives"
    assert _type("Olives manzanilla a la grecque", []) == "olives"        # name alone is enough here
    andalouse = {"name": "Olives à l'andalouse", "categories": OLIVE_TAGS}
    for name, tags in (("Olives vertes dénoyautées", ["en:olives", "en:green-olives"]), ("Olives noires", ["en:olives"])):
        sub = taxonomy.substitution(andalouse, {"name": name, "categories": tags})
        assert sub and sub["level"] == 1 and sub["type"] == "olives", name


def test_olive_oil_sauce_and_pizza_are_not_a_jar_of_olives():
    assert _type("Huile d'olive vierge extra", ["en:olive-oils", "en:vegetable-oils"]) == "oil"
    sauce = ["en:condiments", "en:sauces", "en:tomato-sauces", "en:olive-tree-products", "en:groceries"]
    assert _type("Tomates Olives", sauce) != "olives"                     # a sauce merely tagged with olive-tree-products
    assert _type("Pizza aux olives", ["en:meals", "en:pizzas"]) != "olives"
    andalouse = {"name": "Olives à l'andalouse", "categories": OLIVE_TAGS}
    assert taxonomy.substitution(andalouse, {"name": "Tomate olives", "categories": sauce}) is None


# ---- regressions found by auditing a random sample of the real catalogue -------------------------------------------
YOG = ["en:fermented-milks", "en:yogurts"]


def test_chocolate_is_never_a_soda():
    # "cola" was matching inside "chocolate", which sent every chocolate product to soda.
    for name in ("Milk chocolate date & peanut", "Belgian Chocolates", "Chocolate spread", "Assortiment de chocolats noirs"):
        assert _type(name, []) != "soda", name
    assert _type("Coca-Cola", ["en:colas", "en:sweetened-beverages"]) == "soda"
    assert _type("Limonade", ["en:lemonades"]) == "soda"


def test_chips_are_crisps_not_cookies_or_flatbread():
    assert _type("Tortilla Chips Saveur Chili", []) == "chips"
    assert _type("Chips de L'aveyron", []) == "chips"
    assert _type("McVitie's Choc Chip Cookies", []) != "chips"
    assert _type("Tortilla espanola oignons", []) != "chips"


def test_a_pate_is_not_pasta_and_a_sausage_is_not_a_ham():
    assert _type("Pâté Faisan aux Airelles et au Marc de Bourgogne", []) != "pasta"
    assert _type("Minis saucissons nature APERISEC", []) != "ham"
    assert _type("HERTA lardons Fumés 300g", ["en:pork-prepared", "en:smoked-lardons"]) != "ham"
    assert _type("Jambon sec du Morvan", ["en:cured-hams", "en:dried-hams"]) == "ham"


def test_a_drink_or_a_dish_named_after_an_ingredient_is_not_that_ingredient():
    assert _type("La mortuacienne limonade artisanale pomme aux épices", ["en:beverages"]) != "spices"
    assert _type("Sauce Pasta Tomate chèvre et miel", []) != "honey"
    assert _type("Galette Jambon Emmental", []) != "ham"
    assert _type("Salade de boulgour, cacahuetes et amandes", []) != "nuts"


def test_an_ingredient_that_only_sounds_like_a_dish_keeps_its_category():
    assert _type("Filets de poulet", ["en:chicken-breasts"]) == "chicken"
    assert _type("Purée de carotte", ["en:vegetables"]) != taxonomy.UNCATEGORISED


def test_fresh_fruit_is_not_juice_jam_or_a_cake():
    assert _type("Ananas entier", []) == "fresh_fruit"
    assert _type("Citrons 500g. Non Traité Après Récolte.", []) == "fresh_fruit"
    assert _type("Printemps jus de pomme", []) == "fruit_juice"
    assert _type("Myrtilles sauvages au sirop", []) != "fresh_fruit"
    assert _type("Financiers à la framboise pur beurre", []) != "fresh_fruit"
    assert _type("Confiture de framboise", ["en:jams"]) == "jam"


def test_two_different_fruits_are_never_substitutes():
    apple = {"name": "Pommes Golden", "categories": ["en:apples"]}
    orange = {"name": "Oranges", "categories": ["en:oranges"]}
    other_apple = {"name": "Pommes Gala", "categories": ["en:apples"]}
    assert taxonomy.substitution(apple, orange) is None
    assert taxonomy.substitution(apple, other_apple)["level"] <= 2


def test_only_real_grilled_vegetables_are_grilled_vegetables():
    assert _type("Poivrons grillés à l'huile", []) == "grilled_vegetables"
    for name, tags in (("Myrtille", ["en:berries", "en:blueberries"]), ("Grünkohl", ["en:leaf-vegetables"]),
                       ("Cornichons aigres doux", ["en:gherkins"]), ("Maïs doux sans sel", ["en:canned-sweet-corn"])):
        assert _type(name, tags) != "grilled_vegetables", name


def test_a_flavoured_yogurt_is_not_a_plain_one():
    assert _type("Yaourt nature", YOG) == "plain_yogurt"
    assert _type("Yaourt vanille", YOG) == "flavoured_yogurt"
    assert _type("Früchtetraum - Pfirsich-Maracuja", YOG) != "plain_yogurt"


def test_a_spanish_jam_is_a_jam_and_a_puree_is_a_puree():
    assert _type("Mermelada Extra de Frambuesa", ["en:jams", "en:berry-jams"]) == "jam"
    assert _type("Purée de carotte", ["en:vegetables"]) == "vegetable_puree"
    assert _type("Purée de brocoli", ["en:vegetables"]) == "vegetable_puree"
    assert _type("Confit de figues", ["en:chutneys"]) != "fresh_fruit"


def test_quinoa_and_lentils_carry_a_seeds_tag_but_are_not_nuts():
    assert _type("Quinoa rouge", ["en:seeds", "en:cereal-grains", "en:quinoa"]) != "nuts"
    assert _type("Linsen", ["en:seeds", "en:legumes", "en:lentils"]) != "nuts"
    assert _type("Graines de courges", ["en:seeds", "en:pumpkin-seeds"]) == "nuts"
