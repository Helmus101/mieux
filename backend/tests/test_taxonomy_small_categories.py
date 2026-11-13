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
