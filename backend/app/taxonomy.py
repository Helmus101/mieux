"""Product taxonomy and the substitution rules. Two questions, kept apart from quality and price:
  classify(product) -> family / category / subcategory / product type / form / use   (rules over OFF category tags, name and ingredients)
  substitution(orig, cand) -> level 1-4 or None   (None = not a substitute, whatever the nutrition)
A hard mismatch of type, form or use rejects a candidate outright; no similarity score can compensate."""
import re
from typing import Any, Dict, List, Optional, Tuple

# type id -> (family, category, subcategory, form, primary use, tag regex, name regex). First matching rule wins: specific before general.
R = [
    # ---- bakery and cereals
    ("breadsticks", "cereals_bakery", "bread", "breadsticks", "stick", "snacking", r"breadsticks|grissini|gressins", r"grissini|gressin|breadstick"),
    ("burger_buns", "cereals_bakery", "bread", "buns", "bun", "sandwich_making", r"hamburger-buns|burger-buns|hot-dog-buns|bagels", r"burger|hot[- ]?dog|bagel"),
    ("brioche_toast", "cereals_bakery", "bread", "toast", "slice_crisp", "breakfast", r"toasted-brioche|brioche-toast", r"(toast|grill|biscott|tartine).*brioch|brioch.*(toast|grill|biscott|tartine)"),
    ("sliced_brioche", "cereals_bakery", "bread", "sliced_loaf", "slice_soft", "breakfast", r"sliced-brioche|brioche-bread", r"(tranch|pain de mie|mie).*brioch|brioch.*(tranch|pain de mie|mie)"),
    ("viennoiserie", "cereals_bakery", "pastry", "pastry", "pastry", "breakfast", r"viennoiseries|brioches|croissants|pains-au-chocolat|pains-aux-raisins", r"brioche|croissant|pain au chocolat|pain aux raisins"),
    ("rusks", "cereals_bakery", "bread", "rusk", "slice_crisp", "breakfast", r"rusks|biscottes", r"biscotte|grilletine|rusk"),
    ("toasted_bread", "cereals_bakery", "bread", "toast", "slice_crisp", "breakfast", r"toasts|toasted-bread|toasted-bread-rolls|pains-grill", r"pain grill|tartines?|toast|grill"),
    ("sandwich_bread", "cereals_bakery", "bread", "sliced_loaf", "slice_soft", "sandwich_making", r"sliced-breads|sandwich-breads|packaged-breads|pains-de-mie", r"pain de mie|pain.*tranch|tranch.*pain|sandwich"),
    ("baguette", "cereals_bakery", "bread", "loaf", "loaf", "meal", r"baguettes|pains-de-campagne|rye-breads|breads|sourdough", r"baguette|pain de campagne|pain (au|aux|de|complet|nature)|\bpain\b"),
    ("crackers", "cereals_bakery", "snack_cracker", "cracker", "cracker", "snacking", r"crackers|crispbreads|pretzels|rice-cakes|galettes", r"cracker|bretzel|pretzel|galette de riz|knäcke"),
    ("breakfast_cereal", "cereals_bakery", "cereal", "cereal", "cereal", "breakfast", r"breakfast-cereals|cereal-flakes|cornflakes|extruded-cereals", r"corn ?flakes|c[ée]r[ée]ales|pétales|petales|chocapic|special k"),
    ("muesli", "cereals_bakery", "cereal", "muesli", "cereal", "breakfast", r"mueslis|granola|oat-flakes|porridge", r"muesli|granola|porridge|flocons d.avoine"),
    ("pasta", "cereals_bakery", "pasta", "pasta", "pasta", "meal", r"pastas|spaghetti|macaroni|noodles", r"p[âa]tes|spaghetti|penne|fusilli|tagliatelle|macaroni|coquillette|nouilles"),
    ("rice", "cereals_bakery", "grain", "grain", "grain", "meal", r"\brices?\b(?!-based)|basmati", r"^riz\b|\briz (basmati|long|complet|thai)"),
    # ---- dairy
    ("plant_yogurt", "dairy_alt", "yogurt", "spoonable", "spoon", "breakfast", r"plant-based-(yogurts|desserts)|soy-yogurts|dairy-substitutes-yogurts", r"(soja|amande|coco|avoine).*(yaourt|dessert)|yaourt.*(soja|amande|coco)"),
    ("flavoured_yogurt", "dairy", "yogurt", "spoonable", "spoon", "dessert", r"flavoured-yogurts|fruit-yogurts|sweetened-yogurts|yogurts-with-fruits|dessert", r"(vanille|fruit|fraise|abricot|p[êe]che|coco|caramel|citron|cerise|banane|vanilla|aux fruits)"),
    ("plain_yogurt", "dairy", "yogurt", "spoonable", "spoon", "breakfast", r"yogurts|yoghurts|plain-yogurts|greek-yogurts|skyr|fermented-milks", r"yaourt|yogourt|yogurt|skyr|grec|nature"),
    ("fromage_blanc", "dairy", "fresh_cheese", "spoonable", "spoon", "breakfast", r"fromages-blancs|fresh-cheeses|petits-suisses|faisselle|quark", r"fromage blanc|petit suisse|faisselle|quark"),
    ("cheese", "dairy", "cheese", "cheese", "cheese", "meal", r"cheeses|fromages", r"fromage|camembert|emmental|comt[ée]|brie|gouda|mozzarella|chèvre|chevre"),
    ("milk", "dairy", "milk", "liquid", "drink", "breakfast", r"^en:milks$|whole-milks|semi-skimmed-milks|skimmed-milks|uht-milks|cow-milks", r"^lait\b|lait (demi|entier|écrém|ecrem|uht)"),
    ("cream", "dairy", "cream", "liquid", "cooking", "cooking", r"creams|cr[èe]mes-fra[iî]ches", r"cr[èe]me (fra[iî]che|liquide|enti[èe]re)|cr[èe]me fra"),
    ("butter", "dairy", "fat", "fat", "spread", "spread_cook", r"(?:^|\s)en:(?:butters|margarines)\b", r"^beurre\b|margarine"),
    # ---- drinks
    ("plant_drink", "drinks", "plant_drink", "liquid", "drink", "breakfast", r"plant-based-(milk|beverages)|milk-substitutes|rice-based-drinks|oat-based-drinks|soy-milks|almond-milks|hazelnut-based-drinks|plant-milks", r"boisson (v[ée]g[ée]tale|au riz|[àa] l.avoine|soja|amande|coco|avoine)|lait (d.|de )?(amande|avoine|soja|coco|riz)|bevande"),
    ("fruit_juice", "drinks", "juice", "liquid", "drink", "any", r"fruit-juices|fruit-nectars|juices|orange-juices", r"jus (de|d.)|nectar|pur jus"),
    ("soda", "drinks", "soda", "liquid", "drink", "any", r"sodas|carbonated-drinks|colas|sweetened-beverages|lemonades|energy-drinks", r"cola|limonade|soda|boisson gazeuse|orangina|fanta|sprite|energy"),
    ("water", "drinks", "water", "liquid", "drink", "any", r"waters|spring-waters|mineral-waters", r"^eau\b|eau (min[ée]rale|de source|gazeuse|plate)"),
    ("capsule_nespresso", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"nespresso", r"nespresso"),
    ("capsule_dolce_gusto", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"dolce-gusto", r"dolce ?gusto"),
    ("capsule_tassimo", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"tassimo", r"tassimo"),
    ("pods_senseo", "drinks", "coffee", "pod", "pod", "hot_drink", r"senseo|coffee-pods", r"senseo|dosettes? souples?|\bpods?\b"),
    ("capsule_other", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"coffee-capsules|(?:^|\s)en:capsules", r"capsules?|dosettes?"),
    ("coffee_beans", "drinks", "coffee", "beans", "beans", "hot_drink", r"coffee-beans|whole-bean|roasted-coffee-beans", r"\ben grains?\b|grains? de caf|\bbeans?\b"),
    ("instant_coffee", "drinks", "coffee", "instant", "instant", "hot_drink", r"instant-coffees|soluble-coffees", r"soluble|instantan|instant"),
    ("ground_coffee", "drinks", "coffee", "ground", "ground", "hot_drink", r"ground-coffees|(?:^|\s)en:coffees\b|filter-coffees|roasted-coffees", r"\bmoulu|ground coffee|caf[eé] moulu|\bcaf[eé]\b"),
    ("herbal_tea", "drinks", "infusion", "infusion", "infusion", "hot_drink", r"herbal-teas|infusions|tisanes|herbal-infusions", r"tisane|infusion"),
    ("tea", "drinks", "tea", "tea", "tea", "hot_drink", r"(?:^|\s)en:(?:teas|black-teas|green-teas|iced-teas)\b|tea-bags", r"\bth[eé]\b|\btea\b"),
    # ---- spreads and sweet
    ("chocolate_spread", "sweet", "spread", "spread", "spread", "breakfast", r"chocolate-spreads|hazelnut-spreads|cocoa-and-hazelnuts-spreads|sweet-spreads", r"p[âa]te [àa] tartiner|nutella|pasta cao|chocolate spread"),
    ("jam", "sweet", "spread", "spread", "spread", "breakfast", r"jams|marmalades|fruit-spreads|compotes", r"confiture|marmelade|compote|gel[ée]e"),
    ("peanut_butter", "sweet", "spread", "spread", "spread", "breakfast", r"peanut-butters|nut-butters", r"beurre de cacahu|peanut butter|pur[ée]e d.(amande|noisette)"),
    ("honey", "sweet", "spread", "spread", "spread", "breakfast", r"honeys", r"\bmiel\b"),
    ("chocolate_bar", "sweet", "chocolate", "bar", "bar", "snacking", r"chocolates|chocolate-bars|dark-chocolates|milk-chocolates", r"chocolat (noir|au lait|blanc)|tablette"),
    ("speculoos", "sweet", "biscuit", "biscuit", "biscuit", "snacking", r"speculoos|speculaas|sp[ée]culoos", r"^(?!.*(tartiner|spread|p[âa]te\\b|cr[èe]me|glace|ice cream|yaourt|yogurt|chocolat|boisson|drink|sirop|caf[ée]|latte|pomme|compote|dessert|fromage|c[ée]r[ée]ales?|muesli|granola|barre|poudre|mousse|flan|riz au lait))(?=.*(sp[ée]culoos|speculaas|biscoff|bastogne|des flandres|lotus))"),
    ("sweet_biscuits", "sweet", "biscuit", "biscuit", "biscuit", "snacking", r"biscuits|cookies|shortbread|sweet-biscuits|biscuits-and-cakes|butter-biscuits", r"biscuit|cookie|sabl[ée]|petit beurre|galette bretonne|palet"),
    ("cakes", "sweet", "cake", "cake", "cake", "snacking", r"cakes|madeleines|pound-cakes|pancakes|crepes|waffles|muffins", r"gâteau|gateau|madeleine|cake|cr[êe]pe|gaufre|muffin|quatre-quarts"),
    ("herbal_lozenge", "sweet", "candy", "lozenge", "lozenge", "throat", r"throat-lozenges|cough-drops|herbal-candies|lozenges|pastilles", r"ricola|valda|fisherman|halls\b|strepsils|pastilles? (pour la gorge|menthol|eucalyptus|aux plantes|au miel|\w+ miel)|bonbons? (aux )?(plantes|herbes|gorge|menthol|eucalyptus)|\bmenthol|eucalyptus|\bgorge\b|lozenge|cough"),
    ("chewing_gum", "sweet", "candy", "gum", "gum", "snacking", r"chewing-gums?|chewing gums?", r"chewing[- ]?gum|\btrident\b|hollywood|freedent"),
    ("licorice", "sweet", "candy", "licorice", "licorice", "snacking", r"liquorice|licorice|r[ée]glisse", r"r[ée]glisse|liquorice|licorice|amarelli"),
    ("gummies", "sweet", "candy", "gummy", "gummy", "snacking", r"gummies|jelly-candies|fruit-gums|marshmallows", r"gomm(e|es) (fruit|ours)|gummi|gummies|ourson|haribo|jelly|marshmallow|guimauve|fruits? gums?"),
    ("candy", "sweet", "candy", "candy", "candy", "snacking", r"candies|confectioneries|gummies|chewing-gum|lollipops", r"bonbon|gomme|r[ée]glisse|sucette"),
    # ---- savoury snacks, meals
    ("chips", "snacks", "chips", "chips", "chips", "snacking", r"chips|crisps|potato-crisps|tortilla-chips|puffs", r"chips|tortilla|croustill|soufflé|souffle"),
    ("nuts", "snacks", "nuts", "nuts", "nuts", "snacking", r"nuts|almonds|cashew|peanuts|pistachios|walnuts|hazelnuts|dried-fruits|seeds", r"amande|cajou|cacahu|pistache|noix|noisette|fruits secs|graines"),
    ("soup", "meals", "soup", "liquid", "soup", "meal", r"soups|veloutes|broths", r"soupe|velout[ée]|bouillon"),
    ("pizza", "meals", "pizza", "pizza", "pizza", "meal", r"pizzas|pizza-dough|quiches|tartes", r"pizza|quiche|tarte|flammekueche"),
    ("ready_meal", "meals", "ready_meal", "meal", "meal", "meal", r"meals|prepared-meals|ready-meals|sandwiches|salads", r"plat cuisin|lasagne|hachis|couscous|paella|sandwich|salade"),
    ("ham", "meat_fish", "charcuterie", "slices", "cold_cut", "meal", r"hams|cooked-hams|dry-hams|charcuteries|bacon|cured-meats", r"jambon|lardons|saucisson|charcuterie|bacon"),
    ("sausage", "meat_fish", "charcuterie", "sausage", "cook", "meal", r"sausages|merguez", r"saucisse|merguez|chipolata"),
    ("fish_canned", "meat_fish", "fish", "can", "cold_fish", "meal", r"canned-fish|tunas|sardines|mackerels|canned-tunas", r"thon|sardine|maquereau|saumon fum"),
    ("fruits_veg", "produce", "fruit_veg", "produce", "produce", "meal", r"fruits|vegetables|fresh-plant|plant-based-foods-and-beverages-fruits|canned-vegetables", r"l[ée]gumes|haricots verts|petits pois|tomates? (pel|concass)|carotte|pomme de terre"),
    ("legumes", "produce", "legumes", "legumes", "legumes", "meal", r"legumes|pulses|lentils|chickpeas|beans|pois-chiches", r"lentille|pois chiche|haricots (rouges|blancs)|f[èe]ves"),
    # ---- sauces, oils
    ("ketchup", "condiments", "sauce", "sauce", "sauce", "any", r"ketchups|tomato-ketchups", r"ketchup"),
    ("mayonnaise", "condiments", "sauce", "sauce", "sauce", "any", r"mayonnaises|dressings|vinaigrettes", r"mayonnaise|vinaigrette|mayo"),
    ("tomato_sauce", "condiments", "sauce", "sauce", "cooking_sauce", "meal", r"tomato-sauces|pasta-sauces|bolognese", r"sauce (tomate|bolognaise|pesto)|coulis"),
    ("mustard", "condiments", "sauce", "sauce", "sauce", "any", r"mustards", r"moutarde"),
    ("oil", "fats_oils", "oil", "oil", "oil", "cooking", r"vegetable-oils|olive-oils|sunflower-oils|rapeseed-oils|oils", r"huile"),
]
RULES = [(tid, fam, cat, sub, form, use, re.compile(tr, re.I), re.compile(nr, re.I)) for tid, fam, cat, sub, form, use, tr, nr in R]
_META = {tid: {"family": fam, "category": cat, "subcategory": sub, "form": form, "use": use} for tid, fam, cat, sub, form, use, *_ in R}

# Clusters of interchangeable types for one purchase decision, ordered by closeness (rank). Types in no common cluster never substitute each other.
CLUSTERS: Dict[str, Dict[str, int]] = {
    "breakfast_slices": {"rusks": 1, "toasted_bread": 2, "brioche_toast": 2, "sliced_brioche": 3, "sandwich_bread": 5},
    "table_bread": {"baguette": 1, "sandwich_bread": 2, "toasted_bread": 4},
    "sticks_and_crackers": {"breadsticks": 1, "crackers": 2},
    "buns": {"burger_buns": 1},
    "pastry_breakfast": {"viennoiserie": 1, "sliced_brioche": 3, "cakes": 5},
    "cereals": {"breakfast_cereal": 1, "muesli": 2},
    "pasta_grains": {"pasta": 1, "rice": 3},
    "yogurt": {"plain_yogurt": 1, "fromage_blanc": 2, "flavoured_yogurt": 3, "plant_yogurt": 5},
    "milk": {"milk": 1, "plant_drink": 3},
    "plant_drinks": {"plant_drink": 1},
    "juice": {"fruit_juice": 1},
    "soda": {"soda": 1},
    "water": {"water": 1},
    "nespresso_capsules": {"capsule_nespresso": 1},   # capsule systems are not interchangeable: a Nespresso capsule does not fit a Dolce Gusto machine
    "dolce_gusto_capsules": {"capsule_dolce_gusto": 1}, "tassimo_discs": {"capsule_tassimo": 1}, "senseo_pods": {"pods_senseo": 1}, "other_capsules": {"capsule_other": 1},
    "coffee_ground_beans": {"ground_coffee": 1, "coffee_beans": 3},   # beans need a grinder: a reasonable substitute at best, never capsules
    "instant_coffee": {"instant_coffee": 1}, "tea": {"tea": 1}, "herbal_tea": {"herbal_tea": 1},
    "spreads_sweet": {"chocolate_spread": 1, "peanut_butter": 3, "jam": 3, "honey": 4},
    "biscuits": {"sweet_biscuits": 1, "cakes": 2},
    "speculoos": {"speculoos": 1, "sweet_biscuits": 3},   # other speculoos first; any sweet biscuit only as a broader alternative; never crackers, spreads or sweets
    "chocolate": {"chocolate_bar": 1},
    "candy": {"candy": 1, "gummies": 2, "licorice": 3}, "herbal_lozenge": {"herbal_lozenge": 1}, "chewing_gum": {"chewing_gum": 1},
    "gummies": {"gummies": 1, "licorice": 2},
    "chips": {"chips": 1, "crackers": 3, "nuts": 4},
    "nuts": {"nuts": 1},
    "cheese": {"cheese": 1},
    "cream": {"cream": 1}, "butter": {"butter": 1}, "oil": {"oil": 1},
    "soup": {"soup": 1}, "pizza": {"pizza": 1}, "ready": {"ready_meal": 1, "pizza": 3},
    "cold_cuts": {"ham": 1, "sausage": 3}, "fish": {"fish_canned": 1},
    "produce": {"fruits_veg": 1, "legumes": 2}, "legumes": {"legumes": 1},
    "sauces": {"ketchup": 1, "mayonnaise": 1, "mustard": 2, "tomato_sauce": 3},
}
LABELS = {1: "almost_identical", 2: "very_similar", 3: "reasonable", 4: "broader"}


def classify(p: Dict[str, Any]) -> Dict[str, Any]:
    """Structured classification from the category tags, then the name. 'unclassified' keeps the leaf tag so same-leaf products still match."""
    tags = " ".join(p.get("categories") or [])
    name = (p.get("name") or "")
    # name beats tags for the specific form (a toasted brioche is tagged as breads and brioches), tags beat the name for the general kind
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if nr.search(name) and tid in ("brioche_toast", "sliced_brioche", "breadsticks", "burger_buns", "capsule_nespresso", "capsule_dolce_gusto", "capsule_tassimo", "pods_senseo", "coffee_beans", "instant_coffee", "herbal_lozenge", "chewing_gum", "licorice", "speculoos"):
            return {"type": tid, **_META[tid], "source": "name", "confidence": "high", "reason": "name matches the specific form: " + nr.pattern[:40]}
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if tr.search(tags):
            return {"type": tid, **_META[tid], "source": "tags", "confidence": "high" if nr.search(name) else "medium", "reason": "category tags match: " + tr.pattern[:40]}
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if nr.search(name):
            return {"type": tid, **_META[tid], "source": "name", "confidence": "low", "reason": "name only, no category tag agrees"}
    leaf = (p.get("categories") or [None])[-1]
    return {"type": None, "family": None, "category": None, "subcategory": None, "form": None, "use": None, "leaf": leaf, "source": "none", "confidence": "none", "reason": "unclassified: only the exact same leaf category is accepted as a substitute"}


def level_between(a: str, b: str) -> Optional[int]:
    """1 same type; 2-4 by distance in the closest cluster that holds both; None if no cluster holds both."""
    if a == b:
        return 1
    best = None
    for members in CLUSTERS.values():
        if a in members and b in members:
            d = abs(members[a] - members[b])
            lv = 2 if d <= 1 else 3 if d == 2 else 4
            best = lv if best is None else min(best, lv)
    return best


def substitution(orig: Dict[str, Any], cand: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Level 1-4 and why, or None when the candidate is not a substitute (different type/form/use). Independent of nutrition and price."""
    co, cc = classify(orig), classify(cand)  # always computed fresh: a rule change must reach products that are already cached
    if co["type"] and cc["type"]:
        lv = level_between(co["type"], cc["type"])
        if lv is None:
            return None
        vo, vc = variant(orig, co["type"]), variant(cand, cc["type"])
        diff = [vo, vc] if co["type"] == cc["type"] and vo and vc and vo != vc else None
        if diff and co["type"] in _HARD_VARIANT_TYPES and "standard" not in diff:
            return None    # hazelnuts lead to hazelnuts, not to almonds or mixed fruit
        return {"level": lv, "label": LABELS[lv], "type": cc["type"], "same_type": co["type"] == cc["type"], "variant_diff": diff}
    # at least one side unclassified: only the same specific category (leaf tag) is accepted, as 'almost identical'
    lo, lc = (orig.get("categories") or [None])[-1], (cand.get("categories") or [None])[-1]
    if lo and lo == lc:
        return {"level": 1, "label": LABELS[1], "type": cc["type"], "same_type": True}
    return None


# Variants inside one product type: a real difference the shopper should know about, disclosed as a trade-off (never a reason to hide the product).
_VARIANTS = {
    "plain_yogurt": [("greek", r"\bgrec|greek|skyr|\bgrecque")],
    "baguette": [("wholemeal", r"complet|int[ée]gral|wholemeal|whole[- ]?wheat|seigle|c[ée]r[ée]ales|graines")],
    "sandwich_bread": [("wholemeal", r"complet|int[ée]gral|wholemeal|whole[- ]?wheat|seigle|c[ée]r[ée]ales|graines")],
    "oil": [("olive", r"olive|oliva")],
    "nuts": [("hazelnut", r"noisette|hazelnut"), ("almond", r"amande|almond"), ("walnut", r"\bnoix\b(?! de (coco|cajou|p[ée]can))|walnut"), ("peanut", r"cacahu|peanut|arachide"),
             ("cashew", r"cajou|cashew"), ("pistachio", r"pistache|pistachio"), ("pecan", r"p[ée]can|pecan"), ("coconut", r"noix de coco|coconut"),
             ("dried_fruit", r"fruits? secs?|raisin|abricot|datte|figue|cranberr|pruneau|dried[- ]fruit"), ("seeds", r"graines|seeds|tournesol|courge|s[ée]same|lin\b|chia"),
             ("mixed", r"m[ée]lange|mix|cocktail|assorti")],
    "milk": [("skimmed", r"[ée]cr[ée]m|skimmed"), ("whole", r"entier|whole")],
}


def variant(p: Dict[str, Any], type_id: Optional[str]) -> Optional[str]:
    """Which variant of its type this product is (e.g. greek / plain yogurt), or None when the type has no variants. Looks at the name and the category tags."""
    rules = _VARIANTS.get(type_id or "")
    if not rules:
        return None
    text = ((p.get("name") or "") + " " + " ".join(p.get("categories") or [])).lower()
    for name, rx in rules:
        if re.search(rx, text):
            return name
    return "standard"


# Types where a different variant is a different product, not a trade-off: hazelnuts are not almonds, almonds are not raisins.
_HARD_VARIANT_TYPES = {"nuts"}


# Words that find a product type by name in a full-text index (OR, accent-free), so a competing brand is found whatever it calls its product.
# Used only to widen the candidate pool; compatibility is still decided by substitution().
TYPE_TERMS: Dict[str, List[str]] = {
    "speculoos": ["speculoos", "spéculoos", "speculaas", "biscoff"],
    "herbal_lozenge": ["pastilles gorge", "ricola", "valda", "bonbons plantes menthol"],
    "chocolate_spread": ["pâte à tartiner"],
    "fish_canned": ["thon", "sardines", "maquereau", "saumon conserve"],
    "butter": ["beurre"], "baguette": ["baguette", "pain de campagne"], "sandwich_bread": ["pain de mie"],
    "plain_yogurt": ["yaourt nature", "yaourt grec", "skyr"], "milk": ["lait demi-écrémé", "lait entier", "lait écrémé", "lait uht"],
    "cheese": ["emmental", "gruyère", "comté", "camembert", "mozzarella", "fromage râpé"],
    "ham": ["jambon", "lardons"], "soup": ["soupe", "velouté"], "pizza": ["pizza"], "chips": ["chips"], "tea": ["thé", "infusion"],
    "nuts": [],
}


def search_terms(p: Dict[str, Any]) -> List[str]:
    return TYPE_TERMS.get(classify(p).get("type") or "", [])
