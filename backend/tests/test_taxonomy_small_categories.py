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
