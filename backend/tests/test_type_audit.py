"""Mix-ups found by auditing alternatives for the most-scanned products (scripts/audit_alternatives.py).
Each line is a real product name that once landed in the wrong type, so it got - or was offered as - an absurd alternative."""
import pytest
from app import taxonomy

NOT_TYPE = [  # (name, a type it must never be)
    ("Perrier fines bulles", "soda"), ("Badoit rouge", "soda"), ("La Salvetat", "soda"), ("Monster Energy Nitro", "soda"), ("Powerade mountain blast zero", "soda"),
    ("Frites 500g", "chips"), ("Pommes Frites 9/9 2,5kg", "chips"), ("Les pommes allumettes", "chips"),
    ("Tartare d'algues", "cream_cheese"), ("Tartare de saumon marine x2 140g", "cream_cheese"), ("Escargolo", "cream_cheese"),
    ("Pains Aux Fruits Epeautre", "fruit_nut_bar"), ("apericube 24 cubes", "stock_cube"), ("Levure de bière", "beer"),
    ("Flan pâtissier aux oeufs", "sweet_biscuits"), ("Carob Pulver", "chocolate_bar"), ("Peanut 100% crunchy", "muesli"),
    ("Milled Hemp Seed", "breakfast_cereal"), ("Lait de coco", "plant_drink"), ("Crème de coco bio", "plant_drink"),
    ("Fromage blanc nature 0%MG - 1kg", "dessert"), ("Lait Ribot de Bretagne", "dessert"), ("Gluten de blé", "baguette"),
    ("Tofu soyeux", "veggie_patty"), ("Protéines de soja grosses", "veggie_patty"), ("Corned Beef", "ready_meal"),
    ("Mélange de fromages râpés Spécial pâtes", "pasta"), ("Coquillettes jambon emmental", "ham"), ("CMO Royale 400g Jambon - mozzarella", "ham"),
    ("Crêpes Jambon Emmental", "cakes"), ("Confiture de lait de Normandie", "jam"), ("Bioflan Non Sucre Au Praline", "sugar"),
    ("Oméga 3 Forté", "oil"), ("Huile de foie de morue", "oil"), ("Friands à la viande", "dough"), ("Brassé au lait de chèvre mûres", "fresh_goat_cheese"),
    ("Nuggets de poulet", "deli_poultry"), ("Elle & Vire Crème Anglaise Poche", "cream"), ("Steak Haché spécial burger", "burger_buns"),
    ("GARDEN GOURMET Sensational Burger", "burger_buns"), ("Chips sel de mer", "salt"), ("Citrons Confits", "candy"),
    ("Saucisses aux lentilles", "sausage"), ("FETA AOP GRECQUE", "mozzarella_fresh"), ("Danone veloute nature 125 g x 12", "soup"),
    ("Pommes paillasson", "compote"), ("Purée au lait entier", "milk"), ("CAFÉ CON LECHE", "ground_coffee"), ("Chili sin carne", "tomato_sauce"),
    ("Barres de céréales chocolat noir", "breakfast_cereal"), ("Barres de Céréales Chocolat, Noisettes et Raisins", "nuts"),
]
IS_TYPE = [  # (name, the type it must be)
    ("Barres de céréales chocolat noir", "cereal_bar"), ("NESTLE NESQUIK Barres de Céréales 8x25g", "cereal_bar"), ("Granola bar honey", "cereal_bar"),
    ("Perrier fines bulles", "water"), ("Badoit rouge", "water"), ("Evian", "water"), ("Coca-Cola", "soda"), ("Orangina", "soda"),
    ("Chips lentilles", "chips"), ("Spaghetti", "pasta"), ("Boisson avoine", "plant_drink"), ("Jambon blanc", "ham"), ("Knacki saucisses", "sausage"),
]


@pytest.mark.parametrize("name,bad", NOT_TYPE)
def test_never_this_type(name, bad):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") != bad


@pytest.mark.parametrize("name,good", IS_TYPE)
def test_is_this_type(name, good):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") == good


MORE_NOT = [("Quézac Intense", "soda"), ("Carola rouge", "soda"), ("Côté Brasserie", "chips"), ("Monster Munch goût Jambon Fromage", "ham"),
            ("MAGGI Gelée Madère", "jam"), ("Donuts de poulet", "deli_poultry"), ("Biscuits apéritifs", "sweet_biscuits"),
            ("Croissants jambon fromage", "viennoiserie"), ("Mini Viennois Thon", "fish_canned"), ("Gelée de groseille", "wine")]
MORE_IS = [("Pains au lait", "viennoiserie"), ("Vin rosé de Provence", "wine"), ("Quézac Intense", "water"), ("Sprite", "soda")]


@pytest.mark.parametrize("name,bad", MORE_NOT)
def test_never_this_type_2(name, bad):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") != bad


@pytest.mark.parametrize("name,good", MORE_IS)
def test_is_this_type_2(name, good):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") == good


ROUND3_NOT = [("Noisette enrobée chocolat lait", "nuts"), ("Ferrero couscous moyen sc 5x100g", "ready_meal"), ("Mix Croco, Oeuf et Cola", "soda"),
              ("Gâteau de riz au caramel", "cakes"), ("10 crêpes bolognaise mozarella", "cakes"), ("Salakis 100% Brebis", "fromage_blanc"),
              ("Lait en poudre écrémé", "milk"), ("Vinaigrette nature", "mayonnaise"), ("CMO 4 fromages - 390g", "hard_cheese"),
              ("Bioflan Non Sucre Au Praline", "sugar"), ("MAGGI Papillotes Poulet", "sauce"), ("Poulet Tikka et riz basmati", "rice"),
              ("Thé glacé saveur pêche", "tea"), ("NESCAFÉ Cappuccino Vanille", "instant_coffee"), ("Feuilleté jambon fromage", "dough"),
              ("PRESIDENT BURGER CHEDDAR EMMENTAL", "burger_buns"), ("Beyond Burger", "burger_buns"), ("Panettone Pur Beurre aux raisins", "dried_fruit"),
              ("Fécule de maïs Maïzena", "corn"), ("Corn Dog", "corn"), ("Édulcorant naturel 100%", "syrup")]
ROUND3_IS = [("Thé noir Earl Grey", "tea"), ("Riz basmati", "rice"), ("Maïs doux en grains", "corn"), ("Amandes décortiquées", "nuts"),
             ("Lait demi-écrémé", "milk"), ("Pâte feuilletée", "dough"), ("Sucre roux", "sugar")]


@pytest.mark.parametrize("name,bad", ROUND3_NOT)
def test_never_this_type_3(name, bad):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") != bad


@pytest.mark.parametrize("name,good", ROUND3_IS)
def test_is_this_type_3(name, good):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") == good


ROUND4_NOT = [("Biscuits Salés au Fromage de Chèvre", "fresh_goat_cheese"), ("Biscuits Salés au Fromage de Chèvre", "cheese"),
              ("10 crêpes bolognaise mozarella", "crackers"), ("Manchons de poulet à la mexicaine", "spirits"),
              ("Fresh Tea", "fresh_fruit"), ("Auchan instant douceur citron", "fresh_fruit"), ("Bioflan Non Sucre Au Praline", "flour")]


@pytest.mark.parametrize("name,bad", ROUND4_NOT)
def test_never_this_type_4(name, bad):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") != bad


ROUND5_NOT = [("Crème cuisine végétale avoine BIO", "beer"), ("NESTLE Lait Concentré Sucré", "cream"), ("Skyr Stracciatella", "mozzarella_fresh"),
              ("2 Mini-Calzones Jambon Mozzarella", "ham"), ("Mélange de fromages râpés Spécial pizza", "pizza"), ("Boisson Latte Gourmande", "ground_coffee"),
              ("Honey roasted nuts and sea salt", "salt"), ("Bille maïs enrobée chocolat lait", "corn"), ("Semoule au poulet", "chicken"),
              ("Grignottes de poulet Barbecue", "deli_poultry"), ("Noir noisettes entières", "nuts"), ("Thé vert glacé saveur citron vert", "fresh_fruit")]
ROUND5_IS = [("Maïs doux en grains", "corn"), ("Pizza margherita", "pizza"), ("Mozzarella", "mozzarella_fresh"), ("Noisettes", "nuts"), ("Café moulu pur arabica", "ground_coffee")]


@pytest.mark.parametrize("name,bad", ROUND5_NOT)
def test_never_this_type_5(name, bad):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") != bad


@pytest.mark.parametrize("name,good", ROUND5_IS)
def test_is_this_type_5(name, good):
    assert taxonomy.classify({"name": name, "categories": []}).get("type") == good


def test_english_muffins_are_buns_not_cakes():
    for n in ("English Muffins", "Muffins anglais", "Thomas' English Muffins"):
        assert taxonomy.classify({"name": n, "categories": []}).get("type") == "english_muffin"
    assert taxonomy.classify({"name": "Muffin chocolat", "categories": []}).get("type") == "cakes"
    assert taxonomy.classify({"name": "Madeleines", "categories": []}).get("type") == "cakes"
