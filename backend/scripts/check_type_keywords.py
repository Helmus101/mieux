"""Consistency check of the type index over the whole local Open Food Facts copy: for each strong product word, every product whose NAME
starts with it (or is made of it) must be in the expected type(s). Prints the violations by count, with samples.

    cd backend && .venv/bin/python scripts/check_type_keywords.py            # all keywords
After scripts/build_type_index.py. A keyword that is a dish ingredient ("jambon" in a pizza) is matched only at the START of the name.
"""
import os, sqlite3, sys, collections

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))
# (name prefix words as FTS phrase, expected types)
CHECKS = [
    ("cornichons", {"pickles"}), ("pickles", {"pickles"}), ("câpres", {"pickles"}), ("saumon fumé", {"smoked_fish"}), ("truite fumée", {"smoked_fish"}),
    ("yaourt nature", {"plain_yogurt", "flavoured_yogurt"}), ("skyr", {"plain_yogurt", "flavoured_yogurt", "fromage_blanc"}), ("fromage blanc", {"fromage_blanc"}),
    ("lait demi", {"milk"}), ("lait entier", {"milk"}), ("beurre doux", {"butter"}), ("beurre demi", {"butter"}), ("margarine", {"butter"}),
    ("crème fraîche", {"cream"}), ("emmental", {"hard_cheese"}), ("camembert", {"soft_ripened_cheese"}), ("mozzarella", {"mozzarella_fresh"}),
    ("jambon", {"ham"}), ("saucisson", {"dry_sausage"}), ("lardons", {"lardons"}), ("blanc de poulet", {"deli_poultry", "chicken"}),
    ("thon", {"fish_canned"}), ("sardines", {"fish_canned"}), ("maquereaux", {"fish_canned"}), ("surimi", {"surimi"}),
    ("spaghetti", {"pasta"}), ("coquillettes", {"pasta"}), ("penne", {"pasta"}), ("riz basmati", {"rice"}), ("lentilles", {"legumes"}), ("pois chiches", {"legumes"}),
    ("pain de mie", {"sandwich_bread"}), ("baguette", {"baguette"}), ("biscottes", {"rusks"}), ("croissants", {"viennoiserie"}), ("brioche", {"viennoiserie", "sliced_brioche"}),
    ("madeleines", {"cakes"}), ("english muffins", {"english_muffin"}), ("bagels", {"burger_buns"}),
    ("muesli", {"muesli"}), ("flocons d'avoine", {"muesli", "breakfast_cereal"}), ("corn flakes", {"breakfast_cereal"}), ("barres de céréales", {"cereal_bar"}), ("barre protéinée", {"protein_bar"}),
    ("chocolat noir", {"chocolate_bar"}), ("pâte à tartiner", {"chocolate_spread"}), ("nutella", {"chocolate_spread"}), ("biscuits", {"sweet_biscuits", "speculoos", "crackers", "cereal_bar", "rusks"}),
    ("confiture", {"jam"}), ("miel", {"honey"}), ("compote", {"compote"}), ("jus d'orange", {"fruit_juice"}), ("jus de pomme", {"fruit_juice"}),
    ("eau minérale", {"water"}), ("coca-cola", {"soda"}), ("limonade", {"soda"}), ("thé vert", {"tea"}), ("thé noir", {"tea"}), ("café moulu", {"ground_coffee"}), ("café soluble", {"instant_coffee"}),
    ("huile d'olive", {"oil"}), ("huile de colza", {"oil"}), ("vinaigre", {"vinegar"}), ("moutarde", {"mustard"}), ("mayonnaise", {"mayonnaise"}), ("ketchup", {"ketchup"}),
    ("sel", {"salt"}), ("sucre", {"sugar"}), ("houmous", {"dip"}), ("pesto", {"pesto"}), ("soupe", {"soup"}), ("velouté", {"soup"}),
    ("pizza", {"pizza"}), ("lait d'amande", {"plant_drink"}), ("boisson avoine", {"plant_drink"}), ("tofu", {"tofu"}),
    ("cacahuètes", {"nuts"}), ("amandes", {"nuts"}), ("noisettes", {"nuts"}), ("chips", {"chips"}), ("pop-corn", {"popcorn"}),
    ("bière", {"beer"}), ("vin rouge", {"wine"}), ("whisky", {"spirits"}), ("glace", {"ice_cream"}),
]


def main():
    db = sqlite3.connect(DB)
    types = {c: t for c, t in db.execute("select code, type from off_type")}
    total_bad = total = 0
    for phrase, ok in CHECKS:
        q = '"' + phrase.replace('"', ' ') + '"'
        try:
            rows = db.execute("select code, text from off_names where off_names match ?", (q,)).fetchall()
        except sqlite3.OperationalError:
            continue
        starts = phrase.lower().replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("ç", "c").replace("î", "i").replace("û", "u").replace("ô", "o")
        n = bad = 0
        samples = collections.Counter()
        for code, text in rows:
            t = (text or "").lower()
            norm = t.replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("ç", "c").replace("î", "i").replace("û", "u").replace("ô", "o")
            if not norm.startswith(starts):
                continue                      # only names that START with the word: "pizza" inside a longer dish name is another product
            ty = types.get(code)
            if ty is None:
                continue
            n += 1
            if ty not in ok:
                bad += 1
                samples[(ty, text[:34])] += 1
        total += n
        total_bad += bad
        if n and bad / n > 0.02:
            print(f"{phrase!r:24} {bad:5}/{n:<6} ({100 * bad / n:4.1f}%) wrong; e.g. " + " | ".join(f"{t}:{x}" for (t, x), _ in samples.most_common(4)))
    print(f"\n{total_bad} of {total} keyword-named products are not in an expected type ({100 * total_bad / max(1, total):.2f}%)")


if __name__ == "__main__":
    main()
