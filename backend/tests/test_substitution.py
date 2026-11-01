"""Substitution precision set: for each original product, candidates that must be accepted (with the minimum level) and candidates that must be rejected."""
import pytest

from app.taxonomy import classify, substitution


def P(name, tags):
    return {"name": name, "categories": tags, "brand": None}


BRIOCHE_TOAST = P("Toast brioché Pelletier LU", ["en:plant-based-foods", "en:breads", "en:brioches", "en:toasted-breads"])
CASES = [
    # (original, [(candidate, max level allowed)], [rejected candidates])
    (BRIOCHE_TOAST,
     [(P("Toast brioché Auchan", ["en:breads", "en:toasted-breads"]), 2), (P("Brioche tranchée nature Harrys", ["en:breads", "en:brioches", "en:sliced-breads"]), 3),
      (P("Pain de mie nature Carrefour Classic", ["en:breads", "en:sliced-breads"]), 4)],
     [P("Grissini stirati a mano De Mori", ["en:breads", "en:breadsticks"]), P("pain Burger complet", ["en:breads", "en:hamburger-buns"]), P("Yaourt nature", ["en:dairies", "en:yogurts"]),
      P("Spaghetti n°5", ["en:pastas"]), P("Jus d'orange", ["en:beverages", "en:fruit-juices"])]),
    (P("Grissini Torinesi", ["en:breads", "en:breadsticks"]),
     [(P("Gressins sésame", ["en:breads", "en:breadsticks"]), 1), (P("Crackers nature", ["en:snacks", "en:crackers"]), 2)],
     [P("Toast brioché", ["en:breads", "en:toasted-breads", "en:brioches"]), P("Pain de mie", ["en:sliced-breads"]), P("Burger buns", ["en:hamburger-buns"])]),
    (P("Burger buns nature x4", ["en:breads", "en:hamburger-buns"]),
     [(P("Pains hot dog", ["en:breads", "en:hot-dog-buns"]), 1)],
     [P("Grissini", ["en:breadsticks"]), P("Biscottes", ["en:rusks"]), P("Baguette tradition", ["en:baguettes"])]),
    (P("Biscottes complètes", ["en:breads", "en:rusks"]),
     [(P("Biscottes 6 céréales", ["en:rusks"]), 1), (P("Pain grillé Pelletier", ["en:toasts"]), 2), (P("Toast brioché", ["en:toasted-breads", "en:brioches"]), 2)],
     [P("Gressins", ["en:breadsticks"]), P("Burger bun", ["en:hamburger-buns"]), P("Céréales chocolat", ["en:breakfast-cereals"])]),
    (P("Yaourt nature Danone", ["en:dairies", "en:yogurts"]),
     [(P("Yaourt grec nature", ["en:dairies", "en:yogurts", "en:greek-yogurts"]), 1), (P("Fromage blanc 3%", ["en:dairies", "en:fromages-blancs"]), 2), (P("Yaourt à la fraise", ["en:dairies", "en:flavoured-yogurts"]), 3)],
     [P("Camembert", ["en:cheeses"]), P("Lait demi-écrémé", ["en:milks"]), P("Glace vanille", ["en:ice-creams"]), P("Crème fraîche épaisse", ["en:creams"])]),
    (P("Boisson au riz coco", ["en:beverages", "en:plant-based-beverages", "en:rice-based-drinks"]),
     [(P("Boisson avoine", ["en:beverages", "en:plant-based-milk-alternatives", "en:oat-based-drinks"]), 1), (P("Boisson soja nature", ["en:soy-milks", "en:beverages"]), 1)],
     [P("Coca-Cola", ["en:beverages", "en:sodas"]), P("Jus de pomme", ["en:beverages", "en:fruit-juices"]), P("Eau minérale", ["en:waters"]), P("Yaourt au soja", ["en:plant-based-yogurts"])]),
    (P("Coca-Cola Zero", ["en:beverages", "en:sodas", "en:colas"]),
     [(P("Pepsi Max", ["en:beverages", "en:sodas", "en:colas"]), 1), (P("Limonade", ["en:beverages", "en:sodas"]), 1)],
     [P("Jus d'orange", ["en:fruit-juices"]), P("Eau gazeuse", ["en:waters"]), P("Boisson à l'avoine", ["en:oat-based-drinks"]), P("Chips", ["en:chips"])]),
    (P("Pur jus d'orange", ["en:beverages", "en:fruit-juices", "en:orange-juices"]),
     [(P("Jus de pomme", ["en:fruit-juices"]), 1), (P("Nectar d'abricot", ["en:fruit-nectars"]), 1)],
     [P("Soda orange", ["en:sodas"]), P("Lait", ["en:milks"]), P("Eau", ["en:waters"])]),
    (P("Nutella", ["en:spreads", "en:sweet-spreads", "en:chocolate-spreads"]),
     [(P("Pâte à tartiner noisette Auchan", ["en:chocolate-spreads"]), 1), (P("Beurre de cacahuète", ["en:peanut-butters"]), 3), (P("Confiture de fraises", ["en:jams"]), 3)],
     [P("Tablette chocolat noir", ["en:chocolates"]), P("Biscuits", ["en:biscuits"]), P("Mayonnaise", ["en:mayonnaises"]), P("Pain de mie", ["en:sliced-breads"])]),
    (P("Spaghetti n°5 Barilla", ["en:cereals-and-potatoes", "en:pastas", "en:spaghetti"]),
     [(P("Penne rigate", ["en:pastas"]), 1), (P("Coquillettes", ["en:pastas"]), 1), (P("Riz basmati", ["en:rices", "en:basmati-rices"]), 4)],
     [P("Sauce tomate", ["en:tomato-sauces"]), P("Pizza", ["en:pizzas"]), P("Baguette", ["en:baguettes"]), P("Céréales", ["en:breakfast-cereals"])]),
    (P("Corn Flakes", ["en:breakfast-cereals", "en:cornflakes"]),
     [(P("Pétales de maïs", ["en:breakfast-cereals"]), 1), (P("Muesli croustillant", ["en:mueslis"]), 2)],
     [P("Barre chocolatée", ["en:chocolates"]), P("Pain", ["en:breads"]), P("Lait", ["en:milks"])]),
    (P("Chips nature Lay's", ["en:snacks", "en:chips", "en:potato-crisps"]),
     [(P("Chips ondulées", ["en:chips"]), 1), (P("Tortilla chips", ["en:tortilla-chips", "en:chips"]), 1)],
     [P("Gâteau", ["en:cakes"]), P("Gressins", ["en:breadsticks"]), P("Bonbons", ["en:candies"])]),
    (P("Ketchup Heinz", ["en:condiments", "en:sauces", "en:ketchups"]),
     [(P("Ketchup bio", ["en:ketchups"]), 1), (P("Mayonnaise", ["en:mayonnaises"]), 2)],
     [P("Confiture", ["en:jams"]), P("Soupe", ["en:soups"]), P("Huile d'olive", ["en:olive-oils"])]),
    (P("Huile d'olive vierge extra", ["en:fats", "en:vegetable-oils", "en:olive-oils"]),
     [(P("Huile de tournesol", ["en:vegetable-oils", "en:sunflower-oils"]), 1)],
     [P("Beurre", ["en:butters"]), P("Vinaigrette", ["en:vinaigrettes"]), P("Olives", ["en:olives"])]),
    (P("Lait demi-écrémé UHT", ["en:dairies", "en:milks", "en:semi-skimmed-milks"]),
     [(P("Lait entier", ["en:milks", "en:whole-milks"]), 1), (P("Boisson à l'avoine", ["en:oat-based-drinks"]), 3)],
     [P("Yaourt nature", ["en:yogurts"]), P("Crème fraîche", ["en:creams"]), P("Soda", ["en:sodas"])]),
]

COFFEE_CAPS = P("Café Classique capsules compatibles Nespresso", ["en:beverages", "en:coffees", "en:coffee-capsules"])
CASES.append((COFFEE_CAPS,
              [(P("Intenso capsules Nespresso x10", ["en:coffee-capsules", "en:coffees"]), 1)],
              [P("Café Classique grains 500 g", ["en:coffees", "en:coffee-beans"]), P("Café moulu classique 250 g", ["en:coffees", "en:ground-coffees"]), P("Café soluble", ["en:instant-coffees"]),
               P("Capsules Dolce Gusto espresso", ["en:coffee-capsules"]), P("Dosettes Senseo", ["en:coffee-pods"]), P("Thé vert", ["en:teas"]), P("Tisane verveine", ["en:herbal-teas"])]))
CASES.append((P("Café moulu classique 250 g", ["en:coffees", "en:ground-coffees"]),
              [(P("Café moulu pur arabica", ["en:ground-coffees", "en:coffees"]), 1), (P("Café en grains arabica", ["en:coffee-beans", "en:coffees"]), 3)],
              [P("Capsules Nespresso", ["en:coffee-capsules"]), P("Café soluble", ["en:instant-coffees"]), P("Thé noir", ["en:teas"])]))


@pytest.mark.parametrize("orig,accepted,rejected", CASES, ids=[c[0]["name"][:24] for c in CASES])
def test_accepts_the_right_substitutes_and_rejects_the_wrong_ones(orig, accepted, rejected):
    for cand, max_level in accepted:
        s = substitution(orig, cand)
        assert s is not None, f"{cand['name']} should be accepted as a substitute of {orig['name']}"
        assert s["level"] <= max_level, f"{cand['name']}: level {s['level']} > {max_level}"
    for cand in rejected:
        assert substitution(orig, cand) is None, f"{cand['name']} must NOT be a substitute of {orig['name']}"


def test_levels_describe_closeness_and_never_cross_clusters():
    assert substitution(BRIOCHE_TOAST, P("Toast brioché X", ["en:toasted-breads", "en:brioches"]))["level"] == 1
    assert substitution(BRIOCHE_TOAST, P("Pain de mie", ["en:sliced-breads"]))["level"] == 4          # broader alternative
    assert classify(P("Grissini", ["en:breadsticks"]))["type"] == "breadsticks"
    assert substitution(P("Grissini", ["en:breadsticks"]), BRIOCHE_TOAST) is None                   # symmetric rejection


def test_unclassified_products_only_match_their_own_leaf_category():
    a, b = P("Truc rare", ["en:foo", "en:bar"]), P("Autre truc", ["en:foo", "en:bar"])
    assert substitution(a, b)["level"] == 1
    assert substitution(a, P("Truc différent", ["en:foo", "en:baz"])) is None
