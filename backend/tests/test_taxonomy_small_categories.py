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
