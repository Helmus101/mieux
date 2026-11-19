"""Product taxonomy and the substitution rules. Two questions, kept apart from quality and price:
  classify(product) -> family / category / subcategory / product type / form / use   (rules over OFF category tags, name and ingredients)
  substitution(orig, cand) -> level 1-4 or None   (None = not a substitute, whatever the nutrition)
A hard mismatch of type, form or use rejects a candidate outright; no similarity score can compensate."""
import re
from typing import Any, Dict, List, Optional, Tuple

# type id -> (family, category, subcategory, form, primary use, tag regex, name regex). First matching rule wins: specific before general.
# IMPORTANT: Chocolate confectionery (tablets) are NOT snack bars. Cakes are NOT snack bars. Biscuits are NOT snack bars.
# A product containing chocolate or nuts is not automatically a snack bar - the purchasing purpose matters.
R = [
    # ---- bakery and cereals
    ("breadsticks", "cereals_bakery", "bread", "breadsticks", "stick", "snacking", r"breadsticks|grissini|gressins", r"grissini|gressin|breadstick|(?:pizza|salt(?:ed)?|sel|pretzel|bretzel|ap[ée]ro|snack|cracker)[ -]?sticks?\b|\bsticks? (?:de |au |à la )?(?:pizza|pain|bretzel|ap[ée]ritif|sel)|b[âa]tonnets? (?:sal[ée]s?|croustillants|ap[ée]ritif|de pain)"),
    ("burger_buns", "cereals_bakery", "bread", "buns", "bun", "sandwich_making", r"hamburger-buns|burger-buns|hot-dog-buns|bagels", r"burger|hot[- ]?dog|bagel"),
    ("english_muffin", "cereals_bakery", "bread", "buns", "bun", "sandwich_making", r"english-muffins", r"english muffins?|muffins? anglais|muffins? [àa] toaster"),
    ("brioche_toast", "cereals_bakery", "bread", "toast", "slice_crisp", "breakfast", r"toasted-brioche|brioche-toast", r"(toast|grill|biscott|tartine).*brioch|brioch.*(toast|grill|biscott|tartine)"),
    ("sliced_brioche", "cereals_bakery", "bread", "sliced_loaf", "slice_soft", "breakfast", r"sliced-brioche|brioche-bread", r"(tranch|pain de mie|mie).*brioch|brioch.*(tranch|pain de mie|mie)"),
    ("viennoiserie", "cereals_bakery", "pastry", "pastry", "pastry", "breakfast", r"viennoiseries|brioches|croissants|pains-au-chocolat|pains-aux-raisins", r"brioche|croissant|pains? au chocolat|pains? aux raisins|pains? au lait|chaussons? aux pommes|chocolatines?|escargots? aux raisins"),
    ("rusks", "cereals_bakery", "bread", "rusk", "slice_crisp", "breakfast", r"rusks|biscottes", r"biscotte|grilletine|rusk"),
    # Bare "grill" (grilled) alone must never classify a product as toast: "Pistaches grillées", "Poulet grillé" and
    # countless other grilled foods have nothing to do with toasted bread when there is no category tag to rule it out.
    ("toasted_bread", "cereals_bakery", "bread", "toast", "slice_crisp", "breakfast", r"toasts|toasted-bread|toasted-bread-rolls|pains-grill", r"pain grill|tartines?\b|\btoast(?:s|ed)?\b"),
    ("sandwich_bread", "cereals_bakery", "bread", "sliced_loaf", "slice_soft", "sandwich_making", r"sliced-breads|sandwich-breads|packaged-breads|pains-de-mie", r"pain de mie|pain.*tranch|tranch.*pain|sandwich"),
    ("baguette", "cereals_bakery", "bread", "loaf", "loaf", "meal", r"baguettes|pains-de-campagne|rye-breads|(?<![a-z])breads\b|sourdough", r"baguette|pain de campagne|pain (au|aux|de|complet|nature)|\bpain\b(?!\s+d[ée]pices?)"),
    ("crackers", "cereals_bakery", "snack_cracker", "cracker", "cracker", "snacking", r"crispbreads|pretzels|rice-cakes|(?<!-)crackers?\b|galettes", r"cracker|bretzel|pretzel|galettes? (?:de |au |aux )?(?:riz|maïs|blé|sarrasin|quinoa|céréales?)\b|knäcke|\bcrisp(?:bread)?s?\b"),
    ("breakfast_cereal", "cereals_bakery", "cereal", "cereal", "cereal", "breakfast", r"breakfast-cereals|cereal-flakes|cornflakes|extruded-cereals", r"corn ?flakes|c[ée]r[ée]ales|pétales|petales|chocapic|special k"),
    ("muesli", "cereals_bakery", "cereal", "muesli", "cereal", "breakfast", r"mueslis|granola|oat-flakes|porridge|cereal-clusters", r"muesli|granola|porridge|flocons d.avoine|cruesly|crunchy|clusters?"),
    ("asian_noodles", "cereals_bakery", "pasta", "asian_noodles", "pasta", "meal", r"instant-noodles?|ramen|udon|soba|rice-noodles?|asian-noodles?|rice-vermicelli|noodle-soups?|cup-noodles?",
     r"ramen|udon|\bsoba\b|instant noodles?|noodles? (?:instant|bowl|cup|saveur)|cup noodles?|nouilles? (?:instantan[ée]es?|chinoises?|asiatiques?|de riz|sautées?|saveur|udon|soba|ramen|japonaises?|thaï)|nouilles?.{0,24}instantan|nouilles? (?:poulet|boeuf|b[œo]euf|crevette|légumes?)|nouilles?[^,]{0,24}instantan|\bpho\b|pad thai|mie goreng|yakisoba|buldak|indomie|nissin|samyang|vermicelles? de riz"),
    ("pasta", "cereals_bakery", "pasta", "pasta", "pasta", "meal", r"pastas|spaghetti|macaroni|noodles", r"p[âa]tes?|spaghetti|penne|fusilli|tagliatelle|macaroni|coquillette|nouilles?|vermicel|gnocchi|ravioli|tortellini|tortelloni|cannelloni|lasagnes? (?:s[èe]ches?|plaques?)|farfalle|rigatoni|linguine|torsades|c[oô]quillettes|capellini|tagliolini|pappardelle|orecchiette|conchiglie|ditalini|fideos|spaetzle|bucatini|fettuccine"),
    ("rice_pudding", "dairy", "dessert", "milk_dessert", "spoon", "dessert", r"rice-puddings?|milk-desserts?", r"\briz au lait\b|rice pudding|cr[èe]me de riz|cr[èe]me riz"),
    ("rice", "cereals_bakery", "grain", "grain", "grain", "meal", r"\brices?\b(?!-based|-pudding|-cakes?|-flours?)|basmati", r"^riz\b(?!\s+au\s+lait)|\briz (basmati|long|complet|thai)"),
    # ---- pantry and condiments (granular types so staples like pesto or soy sauce get their own alternatives)
    ("cocoa_powder", "sweet", "cocoa", "powder", "powder", "drink_mix", r"cocoa-powders|instant-chocolate-powders|chocolate-powders", r"cacao (en poudre|maigre|sucr|soluble)|poudre de cacao|chocolat en poudre|banania|nesquik|benco|ovomaltine"),
    ("soy_sauce", "condiments", "sauce", "soy_sauce", "liquid", "seasoning", r"soy-sauces|soya-sauces", r"sauce soja|soy sauce|shoyu|tamari"),
    ("stock_cube", "condiments", "seasoning", "stock_cube", "cube", "seasoning", r"bouillon-cubes?|stock-cubes?|dehydrated-[a-z-]*bouillons?|bouillons?-en-poudre|fonds?-de-(?:veau|volaille|poisson|boeuf)|cubes-de-bouillon|bouillons?-deshydrates?",
     r"bouillons?\s+(?:en\s+)?(?:cubes?|poudre|d[ée]shydrat|paillettes|granul|kub|tablettes?)|cubes?\s+(?:de\s+)?bouillon|bouillon\s+cubes?|stock\s+cubes?|\bkub\b|fonds?\s+de\s+(?:veau|volaille|poisson|b[œo]euf)|\bcubes?\s+(?:de\s+)?(?:l[ée]gumes|poule|b[œo]euf|volaille|poisson)|\d+\s*cubes?\b|bouillon\s+(?:de\s+)?(?:l[ée]gumes?|volaille|poule|b[œo]euf|boeuf|poisson|vegan|vegetal)(?!.*(?:\d\s?(?:cl|ml|l)\b|brique|pr[êe]t|liquide|velout))|(?:vegan\s+)?bouillon\s+powder"),
    ("pesto", "condiments", "sauce", "pesto", "jar", "meal", r"(?:^|\s)en:(?:green-|red-)?pestos?(?:\s|$)", r"pesto"),
    ("dip", "condiments", "dip", "dip", "tub", "snacking", r"(?:^|\s)en:(?:dips|hummus|houmous|taramas?|tzatziki|guacamoles?)(?:\s|$)|fr:(?:houmous|taramas?|tzatziki)", r"houm[ou]{1,2}s|hummus|tarama|tzatziki|guacamole|ktipiti|baba ghan|mouhamara|dip\b"),
    ("tapenade", "condiments", "sauce", "tapenade", "jar", "meal", r"(?:^|\s)en:(?:tapenades?|antipasti|olive-spreads?)(?:\s|$)", r"tapenade|caviar d.aubergine|cr[èe]me d.olive|cr[èe]me de poivron|antipasti|sp[ée]cialit[ée] (?:[àa]|aux?) (?:la |l.)?(?:tomate|olive|poivron|aubergine)"),
    ("fried_onions", "pantry", "condiment", "fried_onions", "jar", "seasoning", r"(?:^|\s)en:fried-onions(?:\s|$)", r"oignons?[^a-zà-ÿ]{0,15}frits?|frits?[^a-zà-ÿ]{0,15}oignons?|onions?[^a-zà-ÿ]{0,15}fried|fried[^a-zà-ÿ]{0,15}onions?|r[öo]st\w*zwiebel\w*|zwiebel\w*r[öo]st\w*"),
    ("sugar", "pantry", "sugar", "sugar", "granulated", "baking", r"(?:^|\s)en:(?:white-|cane-|brown-|powdered-|icing-)?sugars?(?:\s|$)", r"^sucre|\bsucre (blanc|roux|semoule|en poudre|glace|de canne)|\bsugar\b"),
    ("salt", "pantry", "salt", "salt", "granulated", "seasoning", r"(?:^|\s)en:(?:salts?|sea-salts?|table-salts?|fleur-de-sel)(?:\s|$)", r"^sel\b|\bsel (fin|gros|marin|de mer|gris|fleur|de gu[ée]rande|de table|rose|de l'himalaya)|\bgros sel\b|\bfleur de sel\b|\bsea salt\b|\btable salt\b"),
    ("spices", "pantry", "spice", "spice", "powder", "seasoning", r"(?:^|\s)en:(?:spices?|seasonings?|herbs-and-spices|dried-herbs|peppers|paprikas?|cinnamons?|cumin|curry-powders?|spice-mixes?)(?:\s|$)", r"\b[ée]pices?\b|\bspices?\b|paprika|cumin|curry (en poudre|powder)|\bpoivre\b|\bpepper\b|cannelle|\bcinnamon\b|muscade|nutmeg|safran|saffron|origan|oregano|\bthym\b|\bthyme\b|basilic|basil|herbes de provence|\bpiment\b|chili powder|garam masala|\bcurcuma\b|turmeric"),
    ("syrup", "pantry", "sweetener", "syrup", "liquid", "sweetener", r"agave-syrups|maple-syrups", r"sirop d.agave|sirop d.[ée]rable|agave syrup|maple syrup"),
    ("flour", "pantry", "flour", "flour", "powder", "baking", r"flours|wheat-flours|cereal-flours|rice-flours|maize-flours|chestnut-flours", r"\bfarine\b|\bflour\b|\bsemoule\b|\bsemolina\b"),
    ("smoked_fish", "fish", "fish", "smoked_fish", "slice", "meal", r"smoked-fishes|smoked-trouts|smoked-salmons", r"saumon fum|truite fum|smoked (salmon|trout)|poisson fum"),
    ("surimi", "fish", "fish", "surimi", "stick", "meal", r"surimi", r"surimi"),
    ("veggie_patty", "meat_alt", "meat_alternative", "patty", "patty", "meal", r"vegetarian-patties|vegan-patties|patties-from-soy|meat-analogues", r"steak (v[ée]g|de soja|de bl[ée])|burger v[ée]g|galette v[ée]g|v[ée]g[ée]tal.*(steak|burger)|vegetarian (burger|patty)"),
    ("kefir", "dairy", "yogurt", "kefir", "drinkable", "drink", r"kefirs?", r"k[ée]fir"),
    ("flan", "dairy", "dessert", "flan", "spoon", "dessert", r"flans|creme-desserts", r"\bflan\b|cr[èe]me dessert"),
    ("hot_sauce", "condiments", "sauce", "hot_sauce", "liquid", "seasoning", r"hot-sauces|chili-sauces", r"sauce piquante|hot sauce|tabasco|sriracha|harissa"),
    # ---- snack bars (STRICT: individual bar format for snacking, not confectionery tablets or cakes)
    # Must match individual_bar format AND snacking use case explicitly
    ("fruit_nut_bar", "snacks", "snack_bars", "fruit_and_nut_bar", "individual_bar", "snacking", r"snack-bars|fruit-and-nut-bars|fruit-and-nut|barres-fruits-secs|barres aux fruits secs", r"barre aux fruits( secs)?|barres? (aux )?fruits secs|noix.*fruit( secs)?|fruit.*noix|amande.*cranberr|cranberr.*amande|mélange.*fruits secs(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|barre.*noix de coco(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))"),
    ("cereal_bar", "snacks", "snack_bars", "cereal_bar", "individual_bar", "snacking", r"cereal-bars|granola-bars|breakfast-bars", r"barre c[ée]r[ée]ale(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|barre granola(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|barre de c[ée]r[ée]ales(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|granola bar(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|cereal bar(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|barre.*c[ée]r[ée]al(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))"),
    ("protein_bar", "snacks", "snack_bars", "protein_bar", "individual_bar", "snacking", r"protein-bars|protein-shakes-and-bars", r"barre prot[ée]in(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|protein bar(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|barre prot[ée]in(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|barre.*prot[ée]in(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|proteine.*bar(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))"),
    ("sports_energy_bar", "snacks", "snack_bars", "sports_energy_bar", "individual_bar", "sports_energy", r"sports-energy-bars|energy-bars|sports-bars", r"energy bar(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|barre sport(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|sport bar(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|energy bar(?!.*(chocolat|tablet|gateau|biscuit|cake|dessert|glace))|iso star|isostar|barre d[ée]tente|barre energ[ée]tique"),
    # ---- dairy
    ("plant_yogurt", "dairy_alt", "yogurt", "spoonable", "spoon", "breakfast", r"plant-based-(yogurts|desserts)|soy-yogurts|dairy-substitutes-yogurts", r"(soja|amande|coco|avoine).*(yaourt|dessert)|yaourt.*(soja|amande|coco)"),
    # A flavour word alone (vanille, coco, fruit...) must never classify a product as yogurt without a category tag:
    # "Boisson riz coco" is a plant drink, not a yogurt, and has no tag to rule this out when only the name is checked.
    ("flavoured_yogurt", "dairy", "yogurt", "spoonable", "spoon", "dessert", r"flavoured-yogurts|fruit-yogurts|sweetened-yogurts|yogurts-with-fruits|drinkable-yogurts",
     r"(?:yaourt|yogourt|yogurt).{0,25}(?:vanille|fruit|fraise|abricot|p[êe]che|coco|caramel|citron|cerise|banane|vanilla)|(?:vanille|fruit|fraise|abricot|p[êe]che|coco|caramel|citron|cerise|banane|vanilla).{0,25}(?:yaourt|yogourt|yogurt)|skyr.{0,25}(?:vanille|fruit|fraise|framboise|myrtille|abricot|p[êe]che|coco|caramel|citron|cerise|banane|mangue|pomme|ananas|passion|cassis|vanilla)"),
    # Bare "nature" or "grec" alone must never classify a product as yogurt: "nature" means "plain" for almost any French
    # grocery item (lardons nature, riz nature, jambon nature all have empty category tags in practice), and "grec" appears
    # in unrelated names too (salade grecque). Only an explicit yogurt word anchors this rule.
    ("plain_yogurt", "dairy", "yogurt", "spoonable", "spoon", "breakfast", r"yogurts|yoghurts|plain-yogurts|greek-yogurts|skyr|fermented-milks", r"yaourt|yogourt|yogurt|skyr"),
    ("fromage_blanc", "dairy", "fresh_cheese", "spoonable", "spoon", "breakfast", r"fromages-blancs|fresh-cheeses|petits-suisses|faisselle|quark", r"fromage blanc|petit suisse|faisselle|quark"),
    ("cream_cheese", "dairy", "cheese", "spreadable_cheese", "tub", "spread_cook", r"cheese-spreads|cream-cheeses|spreadable-cheeses|fromages-[àa]-tartiner|labneh", r"labn[eé]h?\b|carr[ée] frais|philadelphia|cream cheese|fromage (frais )?[àa] tartiner|[àa] tartiner.*(ail|fines herbes|nature)|formaggio fresco|spalmabile|kiri\b|st[- ]?m[ée]range|boursin|apericube|vache qui rit|tartare"),
    # A cheese's texture and style decide what it is actually used for (grated into a gratin, spread on a cracker, melted,
    # eaten cold in slices): an Emmental and a Roquefort are both "cheese" but are not realistic substitutes for each other.
    # Each style gets its own type; the generic 'cheese' row below stays only as a catch-all for what matches none of them.
    ("blue_cheese", "dairy", "cheese", "blue", "soft_strong", "meal", r"blue-cheeses", r"roquefort|bleu d.?auvergne|fourme d.?ambert|gorgonzola|bleu de bresse|st[- ]?agur|cabrales|bleu des? causses"),
    ("soft_ripened_cheese", "dairy", "cheese", "soft_ripened", "soft", "meal", r"soft-cheeses|washed[- ]rind-cheeses|camembert|brie-cheeses", r"camembert|\bbrie\b|coulommiers|pont[- ]l.[ée]v[êe]que|munster|reblochon|[ée]poisses|maroilles|chaource|livarot|vacherin|st[- ]?marcellin|langres"),
    ("fresh_goat_cheese", "dairy", "cheese", "goat", "soft", "meal", r"goat-cheeses|goats-cheeses", r"(?:fromage de |bûche |crottin de )?ch[èe]vres?\b(?!\s+chaud)|crottin(?: de chavignol)?|picodon|rocamadour|valen[çc]ay"),
    ("mozzarella_fresh", "dairy", "cheese", "fresh_pasta", "soft", "meal", r"mozzarellas?|fresh-cheeses|burratas?", r"mozzarella|burrata|ricotta|feta\b|buffala|stracciatella"),
    # Short names need word boundaries: "edam" is inside "edamamé", "gouda" inside "goudale" - neither is a cheese.
    ("hard_cheese", "dairy", "cheese", "hard", "hard", "meal", r"hard-cheeses|semi-hard-cheeses", r"emmental|comt[ée]s?\b|gruy[èe]res?\b|parmesan|parmigiano|cheddar|\bgouda\b|beaufort|appenzell|raclette\b|\btomme?\b|abondance|cantal|mimolette|\bedam\b|manchego|pecorino|\bswiss cheese\b|\bprovolone\b|\bmonterey jack\b|colby|\bhavarti\b|pepper jack|jarlsberg|\bemmentaler?\b|\bgrana padano\b"),
    ("cheese", "dairy", "cheese", "cheese", "cheese", "meal", r"cheeses|fromages", r"fromage|camembert|emmental|comt[ée]s?\b|\bbrie\b|\bgouda\b|mozzarella|ch[èe]vres?\b"),
    ("eggs", "dairy", "eggs", "eggs", "eggs", "cooking", r"eggs|oeufs", r"\bu?[oœ]e?ufs?\b(?!.*(chocolat|p[âa]ques|plat|mayonnaise|brouill))"),
    ("milk", "dairy", "milk", "liquid", "drink", "breakfast", r"^en:milks$|whole-milks|semi-skimmed-milks|skimmed-milks|uht-milks|cow-milks", r"^lait\b|lait (demi|entier|écrém|ecrem|uht)|^(?:whole|skim(?:med)?|(?:1|2|reduced[- ]fat|low[- ]fat|fat[- ]free|lactose[- ]free|organic|semi[- ]skimmed) ?%?) milk\b|^milk\b(?! ?(?:chocolate|bar|shake|powder|thistle))"),
    ("cream", "dairy", "cream", "liquid", "cooking", "cooking", r"(?:^|\s)en:(?:creams|fresh-creams|whipping-creams|double-creams|cr[èe]mes-fra[iî]ches)(?:\s|$)", r"cr[èe]me (fra[iî]che|liquide|enti[èe]re)|cr[èe]me fra"),
    ("butter", "dairy", "fat", "fat", "spread", "spread_cook", r"(?:^|\s)en:(?:butters|margarines)\b|matieres-grasses-vegetales", r"^beurre\b|^butter\b(?! ?(?:cookies?|popcorn|beans?|chicken|cups?|biscuits?|croissants?|puff))|^(?:salted|unsalted|sweet cream|cultured) butter\b|margarine|\bflora\b|\bbecel\b|\bproactiv\b|v[ée]g[ée]tal doux|plant.?based butter"),
    # ---- drinks
    ("plant_drink", "drinks", "plant_drink", "liquid", "drink", "breakfast", r"plant-based-milks|milk-substitutes|rice-based-drinks|oat-based-drinks|soy-milks|almond-milks|hazelnut-based-drinks|plant-milks|coconut-milks", r"boisson (v[ée]g[ée]tale|au riz|[àa] l.avoine|soja|amande|coco|avoine)|lait (d.|de )?(amande|avoine|soja|coco|riz)|bevande"),
    ("fruit_juice", "drinks", "juice", "liquid", "drink", "any", r"fruit-juices|fruit-nectars|juices|orange-juices", r"\bjus\b|nectar|pur jus|tropico|capri.?sun|oasis\b|boisson aux fruits|fruit shoot|smoothie|cocktail (?:de )?fruits?|cocktail multifruits?"),
    ("soda", "drinks", "soda", "liquid", "drink", "any", r"sodas|carbonated-drinks|colas|lemonades|energy-drinks", r"\bcola\b|\bcoca.?cola\b|pepsi|schweppes|7[- ]?up|mountain dew|dr\.? pepper|red bull|fritz-?kola|limonade|\bsoda\b|boissons? gazeuses?|orangina|fanta|sprite|energy drink|ginger ale|cream soda|root beer|ginger beer|boissons? [ée]nerg[ée]tisantes?"),
    ("water", "drinks", "water", "liquid", "drink", "any", r"waters|spring-waters|mineral-waters", r"^eau\b|eau (min[ée]rale|de source|gazeuse|plate)|^(?:perrier|badoit|salvetat|la salvetat|s\.? ?pellegrino|san pellegrino|quezac|rozana|vichy c[ée]lestins|st[- ]yorre|saint[- ]yorre|qu[ée]zac|carola|ste? marguerite|sainte[- ]marguerite|oulm[eè]s|contrex|evian|volvic|vittel|cristaline|h[ée]par|courmayeur|wattwiller|thonon)\b(?!.*(?:saveur|aromatis|citron|framboise|p[êe]che|fraise|menthe|juicy|th[ée]\b))"),
    # Alcohol: a beer, a wine and a spirit are three different purchases and never substitute each other.
    ("beer", "drinks", "beer", "beer", "liquid", "drink", r"beers|craft-beers|non-alcoholic-beers|ales|lagers|radlers", r"bi[èe]re|\bbeer\b|pale ale|\bipa\b|stout|lager|panach[ée]|grimbergen|heineken|leffe"),
    ("wine", "drinks", "wine", "wine", "liquid", "drink", r"wines|red-wines|white-wines|rose-wines|sparkling-wines|champagnes", r"\bvin\b|\bwine\b|\bros[ée]s?\b|champagne|prosecco|cr[ée]mant|bordeaux|bourguignon|sauvignon|merlot"),
    ("spirits", "drinks", "spirits", "spirits", "liquid", "drink", r"spirits|vodkas|whiskies|whisky|rums|gins|liqueurs|brandies|pastis|tequilas", r"vodka|whisk(?:y|ies)|rhum|\brum\b|\bgin\b|liqueur|pastis|calvados|cognac|armagnac|tequila"),
    # A cordial to dilute ("sirop de citron") is a drink, not a cough syrup.
    ("drink_syrup", "drinks", "syrup", "cordial", "liquid", "drink", r"syrups|drink-syrups|cordials|fruit-syrups", r"^(?!.*\bau sirop\b)(?!.*\btoux\b).*\bsirops?\b|\bcordial\b|\bdiluant\b"),
    ("capsule_nespresso", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"nespresso", r"nespresso"),
    ("capsule_dolce_gusto", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"dolce-gusto", r"dolce ?gusto"),
    ("capsule_tassimo", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"tassimo", r"tassimo"),
    ("pods_senseo", "drinks", "coffee", "pod", "pod", "hot_drink", r"senseo|coffee-pods", r"senseo|dosettes? souples?|\bpods?\b"),
    ("capsule_other", "drinks", "coffee", "capsule", "capsule", "hot_drink", r"coffee-capsules|(?:^|\s)en:capsules", r"capsules?|dosettes?"),
    ("coffee_beans", "drinks", "coffee", "beans", "beans", "hot_drink", r"coffee-beans|whole-bean|roasted-coffee-beans", r"(?:caf[ée]|coffee|espresso|caff[èe])\b.{0,25}\b(?:en grains?|grains?|in grani|beans?)\b|\b(?:en grains?|grains?|in grani|beans?)\b.{0,25}\b(?:caf[ée]|coffee|espresso|caff[èe])\b"),
    ("instant_coffee", "drinks", "coffee", "instant", "instant", "hot_drink", r"instant-coffees|soluble-coffees", r"soluble|caf[eé]\s+instant\w*|instant\w*\s+(?:de\s+|d.)?caf[eé]|\binstant coffee\b"),
    ("ground_coffee", "drinks", "coffee", "ground", "ground", "hot_drink", r"ground-coffees|(?:^|\s)en:coffees\b|filter-coffees|roasted-coffees", r"\bmoulu|ground coffee|caf[eé] moulu|\bcaf[eé]\b|\bespressos?\b"),
    ("herbal_tea", "drinks", "infusion", "infusion", "infusion", "hot_drink", r"herbal-teas|infusions|tisanes|herbal-infusions", r"tisane|infusion"),
    # Bare "the" (no accent) is the ordinary English word "the", found in all kinds of unrelated brand names
    # ("Carrefour The Market"); bare "tea" alone is thin too. Require the accented French word or a real tea phrase.
    ("tea", "drinks", "tea", "tea", "tea", "hot_drink", r"(?:^|\s)en:(?:teas|black-teas|green-teas|iced-teas)\b|tea-bags", r"\bth[ée]\b(?= (?:vert|noir|blanc|glac|rouge|bleu|menthe|earl|aromatis|infus|[àa] la|au |aux |bio|citron|p[êe]che|jasmin|oolong|matcha|rooibos|\w+ \d))|^th[ée]\b|green tea|black tea|iced tea|\btea bags?\b"),
    # ---- spreads and sweet
    ("chocolate_spread", "sweet", "spread", "spread", "spread", "breakfast", r"chocolate-spreads|hazelnut-spreads|cocoa-and-hazelnuts-spreads|chocolate-and-hazelnut-spreads|pates-a-tartiner-au-chocolat|pates-a-tartiner-aux-noisettes|pates-a-tartiner-au-cacao|produits-a-tartiner-sucres|pates-a-tartiner(?!-vegetal)", r"p[âa]te [àa] tartiner|nutella|pasta cao|chocolate spread"),
    # Compote is a fruit dessert (often for babies), never a spread: it gets its own small category before the jam rule can claim it.
    ("compote", "produce", "fruit", "compote", "spoon", "dessert", r"compotes?|fruit-purees?|apple-compotes?|apple-sauces?", r"\bcompotes?\b|applesauce|pur[ée]e de (pomme|fruit)|compote (de|d.)(pomme|fruit|p[êe]che|abricot|pomme)"),
    ("jam", "sweet", "spread", "spread", "spread", "breakfast", r"jams|marmalades|fruit-spreads|fruit-and-vegetable-preserves|fruit-preserves", r"confiture|confettura|mermelada|marmelade|compote|gel[ée]e|konfit[üu]re|confitura"),
    ("peanut_butter", "sweet", "spread", "spread", "spread", "breakfast", r"peanut-butters|nut-butters", r"beurre (de |d.)(cacahu|amande|noisette|cajou)|peanut butter|(almond|cashew|hazelnut) butter|pur[ée]e (d.|de )?(amandes?|noisettes?|cajou|noix de cajou|cacahu[eè]tes?|pistaches?|noix de p[ée]can|s[ée]same)|cr[èe]me d.amandes?\b(?!.*(dessert|glac))|tahin"),
    ("honey", "sweet", "spread", "spread", "spread", "breakfast", r"honeys", r"\bmiel\b"),
    ("ice_cream", "sweet", "dessert", "ice_cream", "frozen", "dessert", r"ice-creams|frozen-desserts|sorbets|ice-cream-tubs|ice-cream-cones", r"\bglaces?\b|sorbet|ice cream|cr[èe]me glac[ée]e|esquimau"),
    ("dessert", "sweet", "dessert", "dessert", "spoon", "dessert", r"(?:^|\s)en:(?:desserts|dairy-desserts|egg-desserts)(?:\s|$)", r"\bdesserts?\b|\bmousse\b|panna cotta|\btyramisu\b|\btiramisu\b|riz au lait|\bpudding\b"),
    # ---- chocolate confectionery (tablets, bars for confectionery use - NOT snack bars)
    # IMPORTANT: Chocolate tablets are confectionery, not snack bars, even if they contain nuts or fruit
    ("chocolate_bar", "sweet", "chocolate", "bar", "bar", "snacking", r"chocolates|chocolate-bars|dark-chocolates|milk-chocolates", r"chocolat (noir|au lait|blanc)(?!.*(barre|energy|sport|protein|c[ée]r[ée]ale|granola))|tablette"),
    ("speculoos", "sweet", "biscuit", "biscuit", "biscuit", "snacking", r"speculoos|speculaas|sp[ée]culoos", r"^(?!.*(tartiner|spread|p[âa]te\\b|cr[èe]me|glace|ice cream|yaourt|yogurt|chocolat|boisson|drink|sirop|caf[ée]|latte|pomme|compote|dessert|fromage|c[ée]r[ée]ales?|muesli|granola|barre|poudre|mousse|flan|riz au lait))(?=.*(sp[ée]culoos|speculaas|biscoff|bastogne|des flandres|lotus))"),
    ("sweet_biscuits", "sweet", "biscuit", "biscuit", "biscuit", "snacking", r"biscuits|cookies|shortbread|sweet-biscuits|butter-biscuits", r"biscuit|cookie|sabl[ée]|petit beurre|galette bretonne|palet"),
    ("cakes", "sweet", "cake", "cake", "cake", "snacking", r"cakes|madeleines|pound-cakes|pancakes|crepes|waffles|muffins", r"gâteau|gateau|madeleine|cake|cr[êe]pe|gaufre|muffin|quatre-quarts"),
    ("herbal_lozenge", "sweet", "candy", "lozenge", "lozenge", "throat", r"throat-lozenges|cough-drops|herbal-candies|lozenges|pastilles", r"ricola|valda|fisherman|halls\b|strepsils|pastilles? (pour la gorge|menthol|eucalyptus|aux plantes|au miel|\w+ miel)|bonbons? (aux )?(plantes|herbes|gorge|menthol|eucalyptus)|\bmenthol|eucalyptus|\bgorge\b|lozenge|cough"),
    ("chewing_gum", "sweet", "candy", "gum", "gum", "snacking", r"chewing-gums?|chewing gums?", r"chewing[- ]?gum|\btrident\b|hollywood|freedent"),
    ("licorice", "sweet", "candy", "licorice", "licorice", "snacking", r"liquorice|licorice|r[ée]glisse", r"r[ée]glisse|liquorice|licorice|amarelli"),
    ("gummies", "sweet", "candy", "gummy", "gummy", "snacking", r"gummies|jelly-candies|fruit-gums|marshmallows", r"gomm(e|es) (fruit|ours)|gummi|gummies|ourson|haribo|jelly|marshmallow|guimauve|fruits? gums?"),
    ("candy", "sweet", "candy", "candy", "candy", "snacking", r"candies|confectioneries|gummies|chewing-gum|lollipops|caramels", r"bonbon|gomme|r[ée]glisse|sucette|mentos|dragées?|chewy|caramels? mous|\bcaramel\b|p[âa]tes? de fruits"),
    # ---- savoury snacks, meals
    ("chips", "snacks", "chips", "chips", "chips", "snacking", r"chips|crisps|potato-crisps|tortilla-chips|puffs", r"\bchips\b|\bcrisps\b|chips? (?:de|au|aux|à la)|tortilla chips|nachos"),
    ("nuts", "snacks", "nuts", "nuts", "nuts", "snacking", r"(?<!with-)nuts|almonds|cashew|peanuts|pistachios|walnuts|hazelnuts|seeds", r"(?!.*\bhuiles?\b)(?:amande|cajou|cacahu|pistache|noix|noisette|pignons?|fruits secs|graines)"),
    ("dried_fruit", "snacks", "dried_fruit", "dried_fruit", "dried", "snacking", r"(?:^|\s)en:(?:dried-fruits?|dried-(?:goji|apricots?|cranberries?|prunes?|dates?|figs?|mangoes?|pineapples?|apples?|bananas?|berries|coconut|fruit-mixes?)|raisins?|sultana-raisins)(?:\s|$)", r"raisins?[^a-zà-ÿ]{0,12}(?:secs?|sultanines?)|sultanines?\b|(?:abricots?|dattes?|figues?|ananas|mangues?|pommes?|myrtilles?|bananes?)[^a-zà-ÿ]{0,12}(?:secs?|s[èeé]ch[ée]?e?s?)|pruneaux?\b|craisins?\b|cranberries?[^a-zà-ÿ]{0,12}(?:secs?|dried|s[èeé]ch[ée]?e?s?)|baies? de goji|\bgoji\b|airelles?\b|fruits? secs?\b"),
    ("soup", "meals", "soup", "liquid", "soup", "meal", r"soups|veloutes|broths", r"soupe|velout[ée]|bouillon"),
    # Raw dough to bake and top at home is not a substitute for a finished, ready-to-eat pizza: different preparation, different use.
    ("pizza_dough", "cereals_bakery", "dough", "pizza_dough", "raw_dough", "cooking_ingredient", r"pizza-dough|pizza-bases|pizza-shells", r"p[âa]te à pizza|fond(?:s)? de pizza|base(?:s)? (?:à |pour )?pizza|pizza dough"),
    # Raw pastry to roll at home is its own purchase (not a finished cake, tart or pizza).
    ("dough", "cereals_bakery", "dough", "pastry_dough", "raw_dough", "cooking_ingredient", r"pie-dough|pastry-dough|shortcrust-pastry|puff-pastry|brick-pastry|filo-pastry", r"p[âa]tes? (feuillet|bris|sabl|lev|à tarte|à croissant|à choux|phyllo|filo|brick)|puff pastry|shortcrust|p[âa]te [àa] (?:tout )?faire"),
    # A tart is its own bakery purchase: a fruit tart is not a cake, and a tarte fine is not a pizza.
    ("tart", "sweet", "cake", "tart", "tart", "snacking", r"(?:^|\s)en:(?:tarts|fruit-tarts|pies|tartlets)(?:\s|$)", r"tartes?\b|tartelettes?|\bpie\b"),
    ("pizza", "meals", "pizza", "pizza", "pizza", "meal", r"pizzas|quiches|tarte-flambes?", r"pizza|quiche|flammekueche|tarte flamb"),
    ("ready_meal", "meals", "ready_meal", "meal", "meal", "meal", r"meals|prepared-meals|ready-meals|sandwiches|salads", r"plat cuisin|lasagne|hachis|couscous|paella|sandwich|salade|ratatouille|\btian\b|l[ée]gumes? (?:cuisin[ée]s?|saut[ée]s?|gratin[ée]s?|proven[çc]aux)|po[êe]l[ée]e (?:de|aux) l[ée]gumes"),
    ("ham", "meat_fish", "charcuterie", "slices", "cold_cut", "meal", r"hams|cooked-hams|dry-hams|charcuteries|bacon|cured-meats", r"jambon|lardons|saucisson|charcuterie|bacon|\bham\b|gammon"),
    ("sausage", "meat_fish", "charcuterie", "sausage", "cook", "meal", r"sausages|merguez", r"saucisse|merguez|chipolata"),
    ("dry_sausage", "meat_fish", "charcuterie", "dry_sausage", "slice", "snacking", r"dry-sausages|saucissons?|salamis?", r"^\s*(?:mini )?(?:saucissons?|rosette|j[ée]sus|figatelli|lonzo|salami|chorizo|coppa|pepperoni|fuet|sobrasada|saucisse s[èe]che)"),
    ("lardons", "meat_fish", "charcuterie", "lardons", "cook", "meal", r"lardons|smoked-lardons|plain-lardons|bacon", r"^\s*(?:lardons?|allumettes? (?:fum[ée]e?s?|nature|de porc|sup[ée]rieures?)|bacon|poitrine (?:fum[ée]e|s[ée]ch[ée]e))\b"),
    ("tofu", "meat_alt", "meat_alternative", "tofu", "block", "meal", r"tofus?|plain-tofu|smoked-tofu|tofu-", r"\bto(?:fu|fou)\b"),
    ("popcorn", "snacks", "chips", "popcorn", "chips", "snacking", r"popcorn", r"pop[- ]?corn|ma[ïi]s [àa] [ée]clater"),
    # Meat and poultry: each animal is its own small category (a chicken breast is not a beef steak); pâtés and terrines are
    # their own charcuterie purchase. Only the same animal ever substitutes another cut of it.
    # Cooked, ready-to-eat poultry (deli slices: "blanc de poulet", "filet rôti", "aiguillettes rôti") is charcuterie,
    # not a raw cut: it substitutes other cooked poultry slices, never a raw chicken breast, thigh or drumstick. OFF files
    # it under the same "chickens"/"poultry" tags as raw birds, so the prepared/cooked tags are the deciding signal.
    ("deli_poultry", "charcuterie", "charcuterie", "poultry_slices", "slices", "ready_to_eat",
     r"prepared-poultry|prepared-chicken|prepared-turkey|cooked-chicken|cooked-poultry|cooked-turkey|poultry-hams|charcuterie-de-volaille|reconstituted-chicken",
     r"(?=.*\b(?:poulet|dinde|volaille|chicken|turkey|canard|duck)\b)(?=.*\b(?:tranch[ée]e?s?|r[ôo]ti[es]?|cuits?(?:es?)?|cuisin[ée]s?|[ée]touff[ée]e?s?)\b)"),
    ("chicken", "meat_fish", "poultry", "poultry_cut", "cut", "meal", r"chickens|chicken-breasts|chicken-thighs|chicken-drumsticks|chicken-wings|chicken-legs|poultry|fr:aiguillettes-de-poulet", r"\bpoulet\b|\bchicken\b|volaille|aiguillette"),
    ("turkey", "meat_fish", "poultry", "poultry_cut", "cut", "meal", r"turkeys|turkey-cutlets|turkey-breasts|turkey-thighs|turkey-drumsticks", r"\bdinde\b|\bturkey\b|escalope de dinde"),
    ("duck", "meat_fish", "poultry", "poultry_cut", "cut", "meal", r"ducks|duck-breasts|duck-legs|duck-fillets|magret", r"\bcanard\b|\bduck\b|magret"),
    ("beef", "meat_fish", "red_meat", "meat_cut", "cut", "meal", r"(?:^|\s)en:(?:beef|beef-cuts|beef-steaks|ground-beef|minced-beef|beef-roasts)(?:\s|$)", r"\bb(?:oe|œ)uf\b|\bbeef\b|steak hach|viande hach"),
    ("pork", "meat_fish", "red_meat", "meat_cut", "cut", "meal", r"(?:^|\s)en:(?:pork|pork-cuts|pork-roasts|pork-chops|pork-tenderloin|pork-loin)(?:\s|$)", r"\bporc\b|\bpork\b|\bcochon\b"),
    ("veal", "meat_fish", "red_meat", "meat_cut", "cut", "meal", r"(?:^|\s)en:(?:veal|veal-cuts|veal-escalopes)(?:\s|$)", r"\bveau\b|\bveal\b"),
    ("lamb", "meat_fish", "red_meat", "meat_cut", "cut", "meal", r"(?:^|\s)en:(?:lamb|lamb-cuts|mutton|gigots)(?:\s|$)", r"\bagneau\b|\blamb\b|\bmouton\b|gigot"),
    ("pate_terrine", "meat_fish", "charcuterie", "pate", "spread", "meal", r"country-terrines|terrines|rillettes|duck-rillettes|pates-de-campagne|pates-en-croute|foie-gras|pate-de-campagne", r"rillettes?|terrines?|p[âa]t[ée] (?:de campagne|de foie|de t[êe]te|de canard|de lapin|de gibier|du chef|breton|en cro[ûu]te|de volaille)|p[âa]t[ée] [àa] la|\bp[âa]t[é]\b(?!.{0,25}\b(?:pommes?|pomme de terre|pommes de terre|fruits?|poires?)\b)|foie gras"),
    ("fish_canned", "meat_fish", "fish", "can", "cold_fish", "meal", r"canned-fish|tunas|sardines|mackerels|canned-tunas", r"thon|sardine|maquereau|saumon fum"),
    # Specific vegetable forms before the generic bucket below: a jarred grilled/marinated vegetable, a smooth cooked purée and
    # raw/frozen produce are not interchangeable (different preparation, different use), so each gets its own type.
    ("grilled_vegetables", "produce", "fruit_veg", "grilled", "jar", "antipasti", r"grilled-vegetables|antipasti|marinated-vegetables|roasted-peppers|roasted-vegetables", r"poivrons? grill[ée]s?|l[ée]gumes? grill[ée]s?|aubergines? grill[ée]es?|courgettes? grill[ée]es?|antipasti|l[ée]gumes? marin[ée]s?|poivrons? r[ôo]tis?"),
    ("vegetable_puree", "produce", "fruit_veg", "puree", "puree", "meal", r"vegetable-purees|pur[ée]es-de-legumes|vegetable-puree", r"pur[ée]e de (?:brocoli|carotte|courgette|potiron|panais|c[ée]leri|patates? douces?|petits? pois|choux?[ -]fleur|l[ée]gumes?)"),
    ("mushrooms", "produce", "fruit_veg", "mushroom", "mushroom", "cooking_ingredient", r"mushrooms|canned-mushrooms|dried-mushrooms|fresh-mushrooms|fungi", r"champignons?|c[eè]pes?|girolles?|morilles?|pleurotes?|shiitak[ei]|portobello|chanterelles?"),
    ("potatoes", "produce", "vegetable", "potato", "fresh", "meal", r"(?:^|\s)en:(?:potatoes?|potato-products|fresh-potatoes)(?:\s|$)", r"pommes? de terre|patates?\b|\bpotato(?:es)?\b"),
    # Maïs/corn is its own small category: corn flakes, popcorn and corn chips are other products (rejected by name below).
    ("corn", "produce", "vegetable", "corn", "canned", "meal", r"(?:^|\s)en:(?:corn|canned-corn|canned-sweet-corn|sweet-corn)(?:\s|$)", r"\bmaïs\b|sweet corn|\bcorn\b"),
    # Fresh fruit is its own purchase: an apple is not a cabbage, and not a lemonade either (the name guard below keeps
    # juice, jam, compote, syrup, frozen and cooked versions out). Different fruits are different variants, never substitutes.
    ("fresh_fruit", "produce", "fruit_veg", "fruit", "fresh", "snacking", r"(?:^|\s)en:(?:fresh-fruits?|fruits?|berries|apples|bananas|oranges|citrus|grapes|pears|peaches|apricots|plums|cherries|melons|watermelons|pineapples|mangoes|kiwis|strawberries|raspberries|blueberries|blackberries|currants|lemons|avocados)(?:\s|$)",
     r"^(?!.*\b(?:jus|nectar|sirop|confiture|confit|chutney|compote|s[èeé]ch|surgel|conserve|au sirop|chips|crisps|yaourt|glace|tarte|g[âa]teau|boisson|p[ée]tillant|sauce|vinaigre|ar[ôo]me|parfum|saveur|eau|financiers?|biscuits?|cakes?|muffins?|sorbets?|curds?|bonbons?|gel[ée]es?|p[âa]tes? de fruits|smoothies?|yaourts?|desserts?|m[ée]langes?|poudres?)\b).*\b(?:pommes?|bananes?|oranges?|citrons?|ananas|fraises?|framboises?|myrtilles?|poires?|p[êe]ches?|abricots?|raisins?|mangues?|kiwis?|melons?|past[èe]ques?|cl[ée]mentines?|mandarines?|prunes?|cerises?|figues?|dattes?|avocats?|groseilles?)\b"),
    ("fruits_veg", "produce", "fruit_veg", "produce", "produce", "meal", r"(?:^|\s)en:(?:vegetables|canned-vegetables|fresh-vegetables|vegetable-based-foods)(?:\s|$)", r"l[ée]gumes|haricots verts|petits pois|tomates? (pel|concass)|carotte|pomme de terre"),
    ("legumes", "produce", "legumes", "legumes", "legumes", "meal", r"(?:^|\s)en:(?:legumes|canned-legumes|dried-legumes|pulses|lentils|chickpeas|beans|kidney-beans|haricot-beans|fava-beans|baked-beans|pois-chiches)(?:\s|$)", r"lentilles?|pois chiches?|haricots? (?:rouges?|blancs?|cocos?)|f[èe]ves"),   # haricots verts are fresh vegetables, not pulses
    # Olives are their own small category: a jar of green olives substitutes another jar of olives, never olive oil (the name
    # starts with "huile") and never a pizza that merely lists olives among its ingredients.
    ("olives", "produce", "olives", "olives", "jar", "snacking", r"(?:^|\s)en:(?:olives?|marinated-olives|green-olives|black-olives|pitted-olives|stuffed-olives|kalamata-olives|whole-olives)(?:\s|$)", r"^(?!.*\b(?:huile|oil|olio)\b)(?:les?\s+)?(?:olives?|aceitunas?)\b"),
    # ---- sauces, oils
    ("ketchup", "condiments", "sauce", "sauce", "sauce", "any", r"ketchups?|tomato-ketchups?", r"ketchup"),
    ("mayonnaise", "condiments", "sauce", "sauce", "sauce", "any", r"mayonnaises|dressings|vinaigrettes", r"mayonnaise|vinaigrette|mayo"),
    ("tomato_sauce", "condiments", "sauce", "sauce", "cooking_sauce", "meal", r"tomato-sauces|pasta-sauces|bolognese", r"sauce (tomate|bolognaise|pesto)|coulis|pur[ée]e de tomates?|passata|polpa di pomodoro|sugo"),
    ("mustard", "condiments", "sauce", "sauce", "sauce", "any", r"mustards", r"moutarde"),
    ("pickles", "condiments", "condiment", "pickles", "jar", "seasoning", r"capers?|gherkins?|cornichons?|pickles?(?![a-z])|pickled-(?!herring|fish|eggs?|meat|sausages?|salmon|mackerel|anchov)[a-z-]+|capucines?", r"c[âa]pres?\b|capers?\b|cornichons?|gherkins?|\bpickles?\b|oignons? (?:grelots? )?au vinaigre|oignons? grelots?|capucines? au vinaigre"),
    ("vinegar", "condiments", "condiment", "vinegar", "liquid", "seasoning", r"vinegars|balsamic-vinegars|balsamic-vinegars-of-modena|wine-vinegars|apple-cider-vinegars", r"vinaigre|vinegar|balsamique"),
    ("protein_powder", "supplements", "supplement", "powder", "powder", "sports_energy", r"protein-powders|whey-proteins|protein-supplements", r"whey|isolat|casein|cas[ée]ine|prot[ée]ine.{0,12}(?:poudre|powder)|protein powder"),
    ("supplement", "supplements", "supplement", "supplement", "capsule", "health", r"dietary-supplements|food-supplements|vitamins|minerals|spirulina|herbal-supplements", r"compl[ée]ment alimentaire|\bsuppl[ée]ment\b|vitamines?\b|magn[ée]sium|collag[èe]ne|spiruline|om[ée]ga.?3|\bgelules?\b|\bcapsules?\b"),
    # Generic sauces last among the sauces: a marinade, a curry sauce or a nems sauce is still a sauce, never a "meal".
    ("sauce", "condiments", "sauce", "sauce", "sauce", "seasoning", r"(?:^|\s)en:(?:sauces|meal-sauces|cooking-sauces|vegetable-sauces|olive-sauces|sauce)(?:\s|$)", r"\bsauces?\b|\bsalsa\b|\bchutney\b|\brelish\b|\bmarinade\b|\bcondiment\b"),
    ("oil", "fats_oils", "oil", "oil", "oil", "cooking", r"vegetable-oils|olive-oils|sunflower-oils|rapeseed-oils|oils", r"huile|\b(?:olive|sunflower|canola|rapeseed|vegetable|avocado|sesame|coconut|peanut|grapeseed|corn|walnut) oil\b"),
]
# English product names (US market). Added to each type's name regex, so a product whose Open Food Facts record has no usable category tag is still typed.
_EN_NAMES = {
    "fruit_juice": r"\b(?:apple|orange|grape|cranberry|pineapple|prune|tomato|grapefruit|pomegranate|cherry|mango|lemon|lime|carrot|vegetable|fruit) juice\b|\b100% juice\b",
    "soda": r"\blemon[- ]lime\b|\bsoda pop\b|\blemonade\b(?! mix)|\borange soda\b|\bgrape soda\b|\bdiet (?:coke|pepsi|cola)\b|\bsparkling (?:flavou?red )?(?:drink|beverage)s?\b",
    "water": r"\b(?:sparkling|mineral|spring|purified|distilled|alkaline|seltzer)(?: mineral| spring)? water\b|\bseltzer\b|\bclub soda\b",
    "eggs": r"^\s*(?:large |medium |organic |cage[- ]free |free[- ]range |brown |white )*eggs?\b(?! (?:nog|noodles?|rolls?|salad|substitute|white powder))",
    "cream": r"\bhalf (?:and|&) half\b|\bheavy (?:whipping )?cream\b|\bwhipping cream\b|\blight cream\b|\bcoffee creamer\b|\bcreamer\b",
    "cream_cheese": r"\bcream cheese\b",
    "fromage_blanc": r"\bcottage cheese\b|\bquark\b|\bricotta\b(?! (?:ravioli|stuffed))",
    "hard_cheese": r"\bshredded (?:cheddar|mozzarella|parmesan|cheese|mexican|italian)\b|\bcheese slices\b|\bsliced (?:cheddar|swiss|provolone|cheese)\b|\bcheese (?:block|stick|cubes)\b|\bstring cheese\b",
    "plain_yogurt": r"\bplain (?:greek )?yogh?urt\b|^\s*greek yogh?urt\b|^\s*yogh?urt\b(?! (?:covered|coated|raisins|pretzels|chips|bites?))",
    "plant_drink": r"\b(?:almond|oat|soy|coconut|rice|cashew|hemp|pea|macadamia|hazelnut) milk\b",
    "honey": r"^\s*(?:organic |raw |pure |wildflower |clover |manuka )*honey\b(?! (?:nut|bunches|graham|roasted|mustard|bbq|barbecue|ham|wheat|bun))",
    "jam": r"\b(?:strawberry|raspberry|grape|apricot|blackberry|blueberry|peach|cherry|fruit) (?:jam|jelly|preserves?|spread)\b|^\s*(?:jam|jelly|marmalade|preserves)\b",
    "chocolate_bar": r"\bchocolate bars?\b|\b(?:dark|milk|white) chocolate\b(?! (?:chips?|chunks?|covered|coated|cake|chip|syrup|milk|drink|almonds|raisins|pretzels))",
    "candy": r"\bgumm(?:y|ies)\b|\bjelly beans\b|\bhard candy\b|\blollipops?\b|\bcandy (?:canes?|corn)\b|\bmarshmallows?\b|\bcaramels?\b(?! (?:sauce|popcorn|apple|latte|macchiato|syrup|creamer))|\btaffy\b|\bsour (?:patch|worms|belts)\b",
    "sweet_biscuits": r"\bcookies?\b(?! (?:dough|butter|mix|crumbs?))|\bshortbread\b|\bwafers?\b|\bgraham crackers\b",
    "cakes": r"\bbrownies?\b|\bcupcakes?\b|\bpound cake\b|\bwaffles?\b|\bpancakes?\b(?! (?:mix|syrup))|\bmuffins?\b(?<!english muffins)|\bdonuts?\b|\bdoughnuts?\b|\bsnack cakes?\b|\bcoffee cake\b",
    "breakfast_cereal": r"\bcheerios\b|\bfrosted flakes\b|\bfroot loops\b|\bcocoa puffs\b|\blucky charms\b|\bcap'?n crunch\b|\brice krispies\b|\bcorn flakes\b|\boatmeal\b|\brolled oats\b|\binstant oats\b|\bbreakfast cereal\b|\braisin bran\b|\bwheaties\b",
    "sandwich_bread": r"\b(?:white|whole wheat|whole grain|multigrain|sourdough|rye|sandwich|potato|honey wheat|wheat) bread\b|\bsliced bread\b",
    "burger_buns": r"\bhamburger buns?\b|\bhot dog buns?\b|\bbrioche buns?\b|\bslider buns?\b",
    "rice": r"^\s*(?:white|brown|jasmine|basmati|long[- ]grain|wild|arborio|sushi|instant|parboiled|converted)? ?rice\b(?! (?:cakes?|crackers?|milk|noodles?|pudding|krispies|vinegar|paper|chips|flour))",
    "legumes": r"\b(?:black|pinto|kidney|navy|garbanzo|cannellini|white|refried|baked|lima|great northern) beans\b|\bchickpeas\b|\blentils\b|\bsplit peas\b",
    "corn": r"\b(?:canned|whole kernel|sweet|cream style|frozen) corn\b|\bcorn kernels\b",
    "fruits_veg": r"\bgreen beans\b|\bfrozen (?:broccoli|spinach|peas|carrots|vegetables|mixed vegetables|cauliflower|corn|green beans)\b|\bmixed vegetables\b|\bcanned (?:vegetables|peas|carrots|beets|tomatoes|green beans)\b|\bdiced tomatoes\b|\bcrushed tomatoes\b",
    "mustard": r"\b(?:yellow|dijon|honey|spicy brown|deli|stone ground) mustard\b|^\s*mustard\b",
    "mayonnaise": r"\branch dressing\b|\bitalian dressing\b|\bcaesar dressing\b|\bsalad dressing\b|\bthousand island\b|\bblue cheese dressing\b|\bballsamic vinaigrette\b|\bvinaigrette dressing\b|\bfrench dressing\b",
    "pork": r"\bpork (?:chops?|loin|tenderloin|ribs|shoulder|roast|belly)\b|\bbaby back ribs\b",
    "sausage": r"\bhot dogs?\b(?! buns?)|\bfrankfurters?\b|\bwieners?\b|\bbratwurst\b|\bsausage (?:links|patties)\b|\bbreakfast sausage\b|\bitalian sausage\b|\bkielbasa\b|\bcorn dogs?\b",
    "fish_canned": r"\bcanned (?:tuna|salmon|sardines|mackerel)\b|\b(?:chunk|solid|albacore|light) (?:white )?tuna\b|\btuna (?:in|packed in) (?:water|oil)\b|\btuna pouch\b|^\s*tuna\b|^\s*sardines\b",
    "tofu": r"\btofu\b|\btempeh\b",
    "ice_cream": r"\bpopsicles?\b|\bice pops?\b|\bfrozen yogh?urt\b|\bgelato\b|\bice cream (?:bars?|sandwich(?:es)?|cones?|cups?)\b|\bsorbet\b",
    "chips": r"\bpotato chips\b|\btortilla chips\b|\bcorn chips\b|\bpita chips\b|\bkettle (?:cooked )?chips\b|\bcheese puffs\b|\bcheese curls\b|\bpork rinds\b",
    "popcorn": r"\bpopcorn\b|\bpretzels?\b",
    "nuts": r"\b(?:almonds?|walnuts?|pecans?|cashews?|pistachios?|macadamias?|hazelnuts?|brazil nuts?|mixed nuts|peanuts?)\b(?! (?:butter|milk|oil|flour|sauce))|\btrail mix\b",
    "dried_fruit": r"\b(?:dried|sweetened dried) (?:cranberries|mango|apricots?|cherries|blueberries|apples?|figs|dates|pineapple|fruit|bananas?|plums)\b|\braisins\b|\bcraisins\b|\bprunes\b",
    "soup": r"\b(?:chicken noodle|tomato|vegetable|cream of \w+|clam chowder|minestrone|lentil|split pea|french onion|broccoli cheddar) soup\b|^\s*soup\b|\bchowder\b|\bbisque\b",
    "ready_meal": r"\bchili\b(?! (?:sauce|powder|oil|crisp|flakes|garlic))|\bburritos?\b|\benchiladas?\b|\btamales?\b|\bpot pie\b|\bmac(?:aroni)? (?:and|&|n') cheese\b|\bmeatloaf\b|\bpot roast\b|\bstuffed (?:peppers|shells)\b|\bfrozen (?:dinner|meal|entree)s?\b|\bhot pockets?\b|\bcorn dogs?\b|\bpierogi\b|\bpot stickers?\b|\bdumplings\b|\begg rolls?\b",
    "potatoes": r"\bfrench fries\b|\btater tots\b|\bhash browns?\b|\bwaffle fries\b|\bcurly fries\b|\bmashed potatoes\b|\bpotato wedges\b",
    "chicken": r"\bchicken (?:breasts?|thighs?|wings?|drumsticks?|tenders?|nuggets?|strips?|legs?|fillets?|cutlets?)\b|\bwhole chicken\b|\brotisserie chicken\b|\bfish sticks\b",
    "turkey": r"\bground turkey\b|\bturkey (?:breast|burgers?|bacon|sausage|slices|deli)\b|\bdeli turkey\b",
    "ham": r"\b(?:sliced|deli|honey|black forest|smoked|spiral) ham\b|^\s*ham\b|\bprosciutto\b|\bcanadian bacon\b|\bspam\b",
    "dry_sausage": r"\bpepperoni\b|\bsalami\b|\bsummer sausage\b|\bbeef (?:stick|sticks)\b|\bsoppressata\b",
    "supplement": r"\bmulti[- ]?vitamins?\b|\bomega[- ]3\b|\bfish oil\b|\bprobiotics?\b|\bcreatine\b|\bcollagen\b|\bmelatonin\b|\bvitamin [a-ek]\b|\bpre[- ]workout\b",
    "protein_powder": r"\bprotein (?:powder|shake|drink)\b|\bwhey\b|\bmeal replacement\b",
    "coffee_beans": r"\bwhole bean coffee\b|\bcoffee beans\b|\bwhole beans?\b",
    "ground_coffee": r"\bground coffee\b|\bdrip coffee\b|\bbreakfast blend\b|\bdark roast\b|\bmedium roast\b|\blight roast\b|^\s*coffee\b(?! (?:creamer|cake|ice|liqueur|mate|syrup|filters?|mug|candy|beans?))",
    "cocoa_powder": r"\bhot cocoa\b|\bhot chocolate\b|\bcocoa (?:mix|powder)\b|\bunsweetened cocoa\b|\bchocolate milk mix\b|\bswiss miss\b",
    "sugar": r"\b(?:granulated|powdered|brown|cane|confectioners'?|caster|coconut) sugar\b|^\s*sugar\b(?! (?:cookies?|snap|free|cereal|wafers?))",
    "flour": r"\b(?:all[- ]purpose|bread|cake|self[- ]rising|whole wheat|almond|coconut|oat|rice|corn) flour\b|^\s*flour\b",
    "vinegar": r"\b(?:apple cider|white|red wine|balsamic|rice|malt|distilled|white wine) vinegar\b|^\s*vinegar\b",
    "ketchup": r"\bketchup\b|\bcatsup\b",
    "hot_sauce": r"\bhot sauce\b|\bsriracha\b|\btabasco\b|\bbuffalo sauce\b|\bchili sauce\b",
    "sauce": r"\bbbq sauce\b|\bbarbecue sauce\b|\bsoy sauce\b|\bteriyaki\b|\bworcestershire\b|\bhoisin\b|\bsteak sauce\b|\bcocktail sauce\b|\btartar sauce\b|\balfredo\b|\benchilada sauce\b|\bgravy\b|\bsalsa\b",
    "tomato_sauce": r"\bmarinara\b|\bpasta sauce\b|\bspaghetti sauce\b|\btomato sauce\b|\btomato paste\b|\bpizza sauce\b|\bvodka sauce\b",
    "pizza": r"\bfrozen pizza\b|\b(?:pepperoni|cheese|supreme|meat lovers|margherita|hawaiian) pizza\b|^\s*pizza\b",
    "tea": r"\btea bags?\b|\b(?:black|green|white|oolong|chai|earl grey|english breakfast) tea\b|\bsweet tea\b",
    "herbal_tea": r"\b(?:chamomile|peppermint|herbal|rooibos|hibiscus|ginger) tea\b",
    "beer": r"\b(?:ipa|pilsner|lager|stout|porter|hefeweizen|pale ale|light beer|amber ale|craft beer)\b|\bhard seltzers?\b",
    "wine": r"\b(?:cabernet|merlot|chardonnay|pinot (?:noir|grigio)|sauvignon blanc|riesling|zinfandel|moscato|malbec|rose wine|red wine|white wine|sparkling wine|champagne|prosecco)\b",
    "spirits": r"\b(?:vodka|whiskey|whisky|bourbon|tequila|rum|gin|brandy|cognac|scotch)\b(?! (?:sauce|barrel|glaze))",
    "pesto": r"\bpesto\b",
    "dip": r"\bguacamole\b|\bhummus\b|\bspinach dip\b|\bqueso dip\b|\bonion dip\b|\bsalsa dip\b",
    "pickles": r"\bdill pickles?\b|\bpickle (?:spears|chips|slices)\b|\bsweet pickles?\b|\bpickled (?:jalape\w+|beets|onions|cucumbers)\b|^\s*pickles\b",
    "olives": r"^\s*(?:green |black |kalamata |pitted |stuffed |sliced )*olives\b",
    "compote": r"\bapplesauce\b|\bfruit cups?\b|\bfruit cocktail\b|\bmandarin oranges\b",
    "flan": r"\bpudding cups?\b|\bgelatin\b|\bjell-?o\b|\bcustard\b",
    "crackers": r"\bsaltines?\b|\bcrackers\b(?! (?:crumbs))|\britz\b|\bcheez-?its?\b|\bgoldfish\b|\brice crackers\b|\bwheat thins\b|\btriscuits?\b",
    "cereal_bar": r"\bgranola bars?\b|\bcereal bars?\b|\bbreakfast bars?\b|\bchewy bars?\b|\bfruit (?:snacks?|leather|bars?)\b|\bnature valley\b",
    "protein_bar": r"\bprotein bars?\b|\bprotein snacks?\b|\bclif\b|\bquest bars?\b|\bkind bars?\b|\bluna bars?\b",
    "sports_energy_bar": r"\benergy bars?\b",
    "dough": r"\bpie crust\b|\bcrescent rolls?\b|\bbiscuit dough\b|\bcookie dough\b|\bpuff pastry\b|\bphyllo\b|\bfilo\b",
    "pizza_dough": r"\bpizza (?:dough|crust)\b",
    "english_muffin": r"\benglish muffins?\b",
    "baguette": r"\bbaguettes?\b|\bciabatta\b|\bfrench bread\b|\bitalian bread\b",
    "breadsticks": r"\bbreadsticks?\b",
    "viennoiserie": r"\bcroissants?\b|\bdanish\b|\bcinnamon rolls?\b|\bsweet rolls?\b",
}
RULES = []
for tid, fam, cat, sub, form, use, tr, nr in R:
    if tid in _EN_NAMES:
        nr = nr + "|" + _EN_NAMES[tid]
    RULES.append((tid, fam, cat, sub, form, use, re.compile(tr, re.I), re.compile(nr, re.I)))

_META = {tid: {"family": fam, "category": cat, "subcategory": sub, "form": form, "use": use} for tid, fam, cat, sub, form, use, *_ in R}

# Clusters of interchangeable types for one purchase decision, ordered by closeness (rank). Types in no common cluster never substitute each other.
# STRICT: Only products that serve the same purchasing purpose can be in the same cluster.
# Removed overly broad relationships: cakes are not breakfast pastry substitutes, biscuits are not cake substitutes.
CLUSTERS: Dict[str, Dict[str, int]] = {
    "breakfast_slices": {"rusks": 1, "toasted_bread": 2, "brioche_toast": 2, "sliced_brioche": 3, "sandwich_bread": 5},
    "table_bread": {"baguette": 1, "sandwich_bread": 4},   # sliced sandwich bread is not a baguette
    "sticks_and_crackers": {"breadsticks": 1, "crackers": 2},
    "buns": {"burger_buns": 1, "english_muffin": 1},
    "pastry_breakfast": {"viennoiserie": 1, "sliced_brioche": 3},  # REMOVED: cakes are not breakfast pastry substitutes
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
    "biscuits": {"sweet_biscuits": 1},  # REMOVED: cakes are not biscuit substitutes
    "speculoos": {"speculoos": 1, "sweet_biscuits": 3},   # other speculoos first; any sweet biscuit only as a broader alternative; never crackers, spreads or sweets
    "chocolate": {"chocolate_bar": 1},  # Chocolate confectionery is separate from snack bars
    "candy": {"candy": 1, "gummies": 2, "licorice": 3}, "herbal_lozenge": {"herbal_lozenge": 1}, "chewing_gum": {"chewing_gum": 1},
    "gummies": {"gummies": 1, "licorice": 2},
    "chips": {"chips": 1, "crackers": 3},   # nuts are not a substitute for crackers or chips (they were level 2 via the rank distance)
    "nuts": {"nuts": 1},
    "cheese": {"cheese": 1}, "cream_cheese": {"cream_cheese": 1},   # spreadable fresh cheeses (labneh, cream cheese, Carré Frais) only substitute each other; never mozzarella or emmental
    "blue_cheese": {"blue_cheese": 1}, "soft_ripened_cheese": {"soft_ripened_cheese": 1}, "fresh_goat_cheese": {"fresh_goat_cheese": 1},
    "mozzarella_fresh": {"mozzarella_fresh": 1}, "hard_cheese": {"hard_cheese": 1},   # each cheese style only substitutes its own style, never another
    "eggs": {"eggs": 1}, "cream": {"cream": 1}, "butter": {"butter": 1}, "oil": {"oil": 1},
    "snack_bars": {
        "fruit_nut_bar": 1,
        "cereal_bar": 2,
        "protein_bar": 3,
        "sports_energy_bar": 4,
    },  # Snack bars are their own cluster - chocolate tablets, cakes, biscuits are NOT in this cluster

    "soup": {"soup": 1}, "pizza": {"pizza": 1}, "ready": {"ready_meal": 1, "pizza": 3},
    "pizza_dough": {"pizza_dough": 1},   # raw dough to top at home, never interchangeable with a finished pizza
    "cold_cuts": {"ham": 1, "dry_sausage": 2, "sausage": 3}, "fish": {"fish_canned": 1},
    "deli_poultry": {"deli_poultry": 1},   # cooked sliced poultry is its own purchase: never a raw bird, never a ham
    "poultry": {"chicken": 1, "turkey": 2, "duck": 4},   # another bird is related, not the same purchase
    "red_meat": {"beef": 1, "veal": 2, "pork": 4, "lamb": 4},
    "pate": {"pate_terrine": 1},
    "beer": {"beer": 1}, "wine": {"wine": 1}, "spirits": {"spirits": 1}, "vinegar": {"vinegar": 1},
    "protein_powder": {"protein_powder": 1}, "ice_cream": {"ice_cream": 1},
    "salt": {"salt": 1}, "spices": {"spices": 1}, "potatoes": {"potatoes": 1}, "flour": {"flour": 1}, "corn": {"corn": 1},
    "fresh_fruit": {"fresh_fruit": 1},
    "dough": {"dough": 1, "pizza_dough": 2}, "tart": {"tart": 1, "cakes": 3},
    "drink_syrup": {"drink_syrup": 1}, "supplement": {"supplement": 1}, "dessert": {"dessert": 1, "ice_cream": 2},
    "sauces": {"sauce": 1},   # a generic sauce is another generic sauce; ketchup, mayonnaise and tomato sauce keep their own clusters
    "rice_pudding": {"rice_pudding": 1},   # riz au lait is a milk dessert, never a rice grain and never a flan
    "compote": {"compote": 1},             # a fruit dessert, never a spread
    "legumes": {"legumes": 1},   # fruit and pulses are different purchases: no shared cluster
    "olives": {"olives": 1},   # green, black or stuffed: all olives, one small category
    "ketchup": {"ketchup": 1}, "mayonnaise": {"mayonnaise": 1},
    "mustard": {"mustard": 1}, "tomato_sauce": {"tomato_sauce": 1},
}
LABELS = {1: "almost_identical", 2: "very_similar", 3: "reasonable", 4: "broader"}

_BROAD_LEAFS = {
    "en:groceries", "en:foods", "en:plant-based-foods-and-beverages", "en:meals",
    "en:snacks", "en:sweet-snacks", "en:salty-snacks", "en:sauces", "en:condiments",
    "en:dairies", "en:beverages", "fr:epicerie", "en:canned-foods", "en:fats",
    "en:fruits-and-vegetables-based-foods",
    "en:spreads", "en:cereals-and-potatoes", "en:desserts",
}


# A preserve/jam tag on a product whose name names no fruit at all is a tagging error, not a jam.
_JAM_WORDS = re.compile(r"confiture|confettura|marmellata|mermelada|confitura|konfit[üu]re|marmelade|jam\b|conserve|preserve|compote|gel[ée]e|pur[ée]e|fruit|fraise|framboise|myrtille|m[ûu]re|cassis|abricot|pruneau|pomme|poire|figue|orange|citron|agrume|melon|p[êe]che|cerise|banane|coing|rhubarbe", re.I)

_CHEESE_TYPES = {"cheese", "blue_cheese", "soft_ripened_cheese", "fresh_goat_cheese", "mozzarella_fresh", "hard_cheese"}


def _classify(p: Dict[str, Any]) -> Dict[str, Any]:
    """Structured classification with improved priority: specific category tags first, then explicit name signals, then broad tags, then fallback name matches.
    Classification confidence is now explicitly tracked. Low-confidence products should not enter strict rankings."""
    tags = " ".join(p.get("categories") or [])
    name = (p.get("name") or "")
    brand = (p.get("brand") or "")
    generic_name = (p.get("generic_name") or "")

    # The per-rule vetoes below depend only on the product, not on the rule: they used to re-run the same regexes
    # once per rule per pass (five full sweeps of RULES, ~800 regex searches per product). They are computed once
    # here; each pass then costs a dict lookup per rule plus the pass's own tag/name test.
    cheese_dish = _not_a_cheese(name)
    flavoured_yogurt = bool(_FLAVOURED_YOGURT.search(name))
    drink_name = bool(_DRINK_NAME.search(name))
    dish_name = bool(_DISH_CONTEXT.search(name))
    legume_drink = bool(_DRINK_NAME.search(re.sub(r"\bvin\s+(?:blanc|rouge|ros[ée])\b|\bjus\b", " ", name, flags=re.I)))
    not_nuts_tag = bool(_NOT_NUTS_TAG.search(tags))
    nuts_tag = bool(_NUTS_TAG.search(tags))
    raw_ready = bool(_READY_RAW_TAG.search(tags))
    dish_tag = bool(_READY_DISH_TAG.search(tags))
    deli_tag = bool(_DELI_TAG.search(tags))
    _rej: Dict[str, bool] = {}
    _nr_name: Dict[str, bool] = {}
    _nr_gen: Dict[str, bool] = {}
    _tr_hit: Dict[str, bool] = {}

    def _rejects(tid: str) -> bool:
        if tid not in _rej:
            r = _TYPE_REJECTS.get(tid)
            _rej[tid] = bool(r and r.search(name))
        return _rej[tid]

    def _guard(tid: str, fam: Optional[str]) -> bool:
        """The vetoes every pass shares (False = this rule cannot claim the product). Same checks, same order of
        outcomes as the inline blocks this replaces - only the regex work is hoisted out of the per-rule loop."""
        if tid in _CHEESE_TYPES and cheese_dish:
            return False   # a crêpe, pizza or sandwich that names its cheese is a prepared dish, not a cheese
        if tid == "plain_yogurt" and flavoured_yogurt:
            return False   # a flavoured yogurt is not a plain one, even when the tag list only says "yogurts"
        # _ingredient_not_standalone, with its name-level regexes already computed once above.
        if fam != "drinks":
            if tid in ("fish_canned", "legumes"):
                # Preserved foods are packed IN a liquid or sauce: only a real beverage word disqualifies them.
                if legume_drink or (tid == "legumes" and dish_name):
                    return False   # a drink, or a pulse named inside a prepared dish, is not the ingredient
            elif drink_name or ((fam in _DISH_FAMILIES or tid in _EXTRA_COMPONENT_TYPES) and dish_name):
                return False   # a drink or a dish named after this ingredient is that drink or dish, not the ingredient
        if _rejects(tid):
            return False   # the name rules this type out (a pâté is not pasta, a sausage is not a ham)
        if tid == "nuts" and not_nuts_tag and not nuts_tag:
            return False   # quinoa, lentils and semolina carry a "seeds" tag but are cereals and pulses, never nuts
        if tid == "dried_fruit" and _NOT_DRIED_TAGS.search(tags) and "en:dried-fruits" not in tags:
            return False   # a compote, purée or dish that names a fruit is not the dried fruit itself
        if tid == "ready_meal" and _LEAF_SALAD.search(name) and not _SALAD_DISH.search(name):
            return False   # a bag of mâche, rocket or mixed leaves is fresh produce, not a prepared dish
        if tid == "ready_meal" and raw_ready and not dish_tag:
            return False   # dry couscous, quinoa and bagged salads carry "en:meals" but are not prepared dishes
        if tid in ("chicken", "turkey", "duck") and deli_tag:
            return False   # cooked deli poultry is charcuterie, not a raw bird - even under shared "chickens"/"poultry" tags
        return True

    def _nr(tid: str, nr) -> bool:
        if tid not in _nr_name:
            _nr_name[tid] = bool(nr.search(name))
        return _nr_name[tid]

    def _ng(tid: str, nr) -> bool:
        if tid not in _nr_gen:
            _nr_gen[tid] = bool(nr.search(generic_name))
        return _nr_gen[tid]

    def _tr(tid: str, tr) -> bool:
        if tid not in _tr_hit:
            _tr_hit[tid] = bool(tr.search(tags))
        return _tr_hit[tid]

    # Machine systems and forms named in the product name win over a generic tag: a Nespresso capsule does not fit a Dolce Gusto machine, sliced brioche is not a pastry.
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if not _guard(tid, fam):
            continue
        if tid in ("capsule_nespresso", "capsule_dolce_gusto", "capsule_tassimo", "pods_senseo", "sliced_brioche", "brioche_toast", "stock_cube", "asian_noodles") and nr.search(name):
            return {"type": tid, **_META[tid], "source": "name_specific", "confidence": "high", "reason": f"machine system named in the product name: {nr.pattern[:30]}"}

    # The product's HEAD word, at the very start of its name, decides its type when it is unambiguous: "Miel de thym" is honey (not a spice),
    # "Huile d'olive au basilic" oil (not a herb), "Moutarde au miel" mustard (not honey). Found by checking every product named by such a word.
    for _rx, _tid, _veto in _HEAD_FIRST:
        if _rx.search(name) and not (_veto and _veto.search(name)):
            if _tid == "plain_yogurt" and flavoured_yogurt:
                _tid = "flavoured_yogurt"
            return {"type": _tid, **_META[_tid], "source": "name_head", "confidence": "high", "reason": f"the name starts with the product word: {_rx.pattern[:30]}"}

    # "Granola" is also LU's chocolate-chip biscuit brand: a Granola from LU, or any "granola" that the tags call a biscuit, is a biscuit, not oat muesli
    # (it used to be offered oatmeal as its alternative).
    if re.search(r"\bgranola\b", name, re.I) and (re.search(r"(?:^|,\s*)(?:lu|granola)(?:\s*,|$)", brand.strip(), re.I) or re.search(r"biscuits?|cookies|sweet-snacks|biscuits-and-cakes", tags)) \
            and not re.search(r"\bbarres?\b|\bbars?\b", name, re.I) and not re.search(r"-bars|breakfast-cereals|:muesli|:granola(?:s)?(?:\s|$)|cereal-flakes|:mueslis", tags):
        return {"type": "sweet_biscuits", **_META["sweet_biscuits"], "source": "name_specific", "confidence": "high", "reason": "Granola is a biscuit (LU) or tagged as one"}

    # A product tagged as gherkins/pickled cucumbers is a pickle even when its name says nothing ("Original"): the generic tags it also carries
    # (vegetables, preserves) used to win and gave it endives and other vegetables as alternatives.
    if _GHERKIN_TAG.search(tags) and not _GHERKIN_DISH.search(name):
        return {"type": "pickles", **_META["pickles"], "source": "tags_specific", "confidence": "high", "reason": "tagged as gherkins / pickled cucumbers"}

    # A name that says "barre(s) de céréales" / "barre céréalière" is a cereal bar whatever its coating (chocolate, nuts) or its tags
    # (they often say breakfast cereals or nuts): without this, a chocolate cereal bar was typed as a cereal or a nut and got muesli or fruit bread as alternatives.
    if _CEREAL_BAR_NAME.search(name) and not _PROTEIN_BAR_NAME.search(name):
        return {"type": "cereal_bar", **_META["cereal_bar"], "source": "name_specific", "confidence": "high", "reason": "the name says cereal bar"}

    # Priority 1: High-specificity product type tags + name agreement (highest confidence)
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if not _guard(tid, fam):
            continue
        if _tr(tid, tr) and _nr(tid, nr):
            if tid == "jam" and not _JAM_WORDS.search(name):
                continue   # 'preserves' tag on barley and lentils: a tagging error, never a jam
            return {"type": tid, **_META[tid], "source": "tags_and_name", "confidence": "high", "reason": f"specific category tag '{tr.pattern[:30]}' and name '{nr.pattern[:30]}' agree"}

    # Priority 2: Explicit product-name and generic-name signals for specific forms (high confidence)
    specific = ("dip", "peanut_butter", "tapenade", "brioche_toast", "sliced_brioche", "breadsticks", "burger_buns", "english_muffin", "dry_sausage", "lardons", "tofu", "popcorn", "capsule_nespresso", "capsule_dolce_gusto", "capsule_tassimo", "pods_senseo", "coffee_beans", "instant_coffee", "herbal_lozenge", "chewing_gum", "licorice", "speculoos",
                "cream_cheese", "chips", "soup", "fruit_juice", "fruit_nut_bar", "cereal_bar", "protein_bar", "sports_energy_bar", "grilled_vegetables", "vegetable_puree", "pizza_dough", "mushrooms", "rice_pudding", "corn", "asian_noodles", "stock_cube", "pickles",
                "blue_cheese", "soft_ripened_cheese", "fresh_goat_cheese", "mozzarella_fresh", "hard_cheese", "olives", "ham", "muesli", "legumes", "fried_onions", "dried_fruit")
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if not _guard(tid, fam):
            continue
        if tid in specific and _nr(tid, nr):
            return {"type": tid, **_META[tid], "source": "name_specific", "confidence": "high", "reason": f"name matches specific form: {nr.pattern[:40]}"}

    # Priority 3: Broad category tags with supporting name evidence (medium confidence)
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if not _guard(tid, fam):
            continue
        if _tr(tid, tr):
            if tid == "jam" and not _JAM_WORDS.search(name):
                continue   # 'preserves' tag on barley and lentils: a tagging error, never a jam
            if _nr(tid, nr) or _ng(tid, nr):
                return {"type": tid, **_META[tid], "source": "tags_with_name", "confidence": "medium", "reason": f"category tag '{tr.pattern[:30]}' with supporting name evidence"}
            return {"type": tid, **_META[tid], "source": "tags_only", "confidence": "medium", "reason": f"category tag '{tr.pattern[:30]}' only (no name support)"}

    # Priority 4: Name-only matches for general types (low confidence - may be ambiguous)
    for tid, fam, cat, sub, form, use, tr, nr in RULES:
        if not _guard(tid, fam):
            continue
        if _nr(tid, nr) or _ng(tid, nr):
            # Reject generic "bar" matches without context
            if tid in ("fruit_nut_bar", "cereal_bar", "protein_bar", "sports_energy_bar"):
                # Only accept if name clearly indicates snack bar format, not just any bar
                if not re.search(r"barre|bar", name, re.I):
                    continue
            return {"type": tid, **_META[tid], "source": "name_only", "confidence": "low", "reason": f"name only, no category tag agrees: {nr.pattern[:40]}"}

    # Priority 5: no rule describes this product, but it still belongs to a category. The most specific Open Food Facts tag
    # that is not a generic shelf becomes its small category ("cat:en:..."): a product nothing else describes still finds
    # its own kind, and never a whole aisle.
    leaf = next((t for t in reversed(p.get("categories") or []) if t not in _GENERIC_LEAF and t not in _BROAD_LEAFS), None)
    if leaf:
        return {"type": _CATEGORY_TYPE + leaf, "family": None, "category": leaf, "subcategory": None, "form": None,
                "use": None, "leaf": leaf, "source": "category_only", "confidence": "medium",
                "reason": f"no type rule matched: the category '{leaf}' is the small category"}
    return {"type": UNCATEGORISED, "family": None, "category": "en:uncategorised", "subcategory": None, "form": None,
            "use": None, "leaf": None, "source": "none", "confidence": "none",
            "reason": "no rule and no usable category tag: uncategorised, so only a shared distinctive name word can match"}


_CEREAL_BAR_NAME = re.compile(r"\bbarres?\s+(?:de\s+|aux\s+(?:\d+\s+)?)?c[ée]r[ée]al(?:es?|i[eè]res?)\b|\bbarres?\s+c[ée]r[ée]ali[eè]res?\b|\b(?:cereal|granola)\s+bars?\b|\bbarres?\s+(?:de\s+)?granola\b", re.I)
_PROTEIN_BAR_NAME = re.compile(r"prot[ée]in", re.I)
_GHERKIN_TAG = re.compile(r"(?:^|\s)(?:en|fr):(?:[a-z-]*gherkins?[a-z-]*|pickled-cucumbers?|pickled-vegetables|pickled-(?:onions?|cabbages?|carrots?|cauliflowers?|beetroots?|peppers?|chillies|capers)|cornichons?[a-z-]*)(?:\s|$)")
_GHERKIN_DISH = re.compile(r"sandwich|club|p[âa]t[ée]|mayonnaise|moutarde|mustard|sauce|soupe|salade|burger|hot ?dog|rosette|jambon|joues|saucisson|chips|biscuit|craquantes|tartare|aspic|wrap|pizza|quiche", re.I)
_HEAD_FIRST = [(re.compile(p, re.I), t, re.compile(v, re.I) if v else None) for p, t, v in (
    (r"^\s*miel\b", "honey", r"pops\b|c[ée]r[ée]ales|kellogg|chocolat|biscuit|belvita|nougat|pain d|moutarde|vinaigre|barres?\b"),
    (r"^\s*huiles?\b", "oil", r"foie de morue|om[ée]ga|capsules?"),
    (r"^\s*moutardes?\b", "mustard", None), (r"^\s*vinaigres?\b", "vinegar", None),
    (r"^\s*confitures?\b(?! (?:de|au) lait)", "jam", None), (r"^\s*gel[ée]es? (?!royale|d.aloe|d.alo[èe]s)", "jam", None), (r"^\s*ketchup\b", "ketchup", None),
    (r"^\s*(?:thon|sardines?|maquereaux)\b", "fish_canned", r"tartare|\bfrais\b|\bfresh\b|pav[ée]s?\b|steaks?\b|crudit|salade|sandwich|pizza|surgel|chocolat|plat |burger|[ée]gren"),
    (r"^\s*madeleines?\b", "cakes", None), (r"^\s*soupes?\b", "soup", r"\bpho\b|nouilles|vermicelles?|ramen|wonton|miso"),
    (r"^\s*(?:saucissons?|rosette)\b", "dry_sausage", None), (r"^\s*lardons?\b", "lardons", None),
    (r"^\s*(?:tofu|tofou)\b", "tofu", None), (r"^\s*pop[- ]?corn\b", "popcorn", None),
    (r"^\s*(?:amandes?|noix(?: de (?:cajou|p[ée]can|macadamia|grenoble|br[ée]sil))?|noisettes?|cacahu[èe]tes?|pistaches?|pignons?)\b", "nuts", r"enrob|chocolat|caramel|sucr|pralin|yaourt|farine|poudre|lait|p[âa]te|beurre|cr[èe]me|huile|jambon|mousse|saumon|boisson|biscuit|g[âa]teau|tablette|\bbarres?\b|nougat|drag[ée]es|fourr|conf"),
    (r"^\s*(?:comt[ée]|emmental|gruy[èe]re|parmesan|parmigiano|cheddar|gouda|beaufort|cantal|mimolette|edam|raclette)\b", "hard_cheese", r"sabl[ée]|biscuit|cracker|cocktail|sandwich|pizza|quiche|tarte|gratin|burger|croissant|saucisson|jambon"),
    (r"^\s*skyr\b", "plain_yogurt", r"granola|c[ée]r[ée]ales|salt|barre|muesli"),
    (r"^\s*farines?\b", "flour", None), (r"^\s*(?:infusions?|tisanes?)\b", "herbal_tea", None),
    (r"^\s*m[uü]e?sli\b", "muesli", None),
    (r"^\s*th[ée]s? (?:vert|noir|blanc|rouge|oolong|matcha|earl|ceylan|jasmin|menthe|gingembre)\b", "tea", r"glac[ée]|\bice\b"),
    (r"^\s*olives?\b", "olives", r"huile|oil|spray|mayo|sauce|pistou|tapenade|pizza|pain|biscuit|cake"),
    (r"^\s*sels?\b(?! de bain)", "salt", None), (r"^\s*sucres?\b(?! d.orge| d’orge| glace)", "sugar", None), (r"^\s*pickles?\b", "pickles", None),
    (r"^\s*sorbets?\b", "ice_cream", None), (r"^\s*dattes?\b", "dried_fruit", r"fourr|p[âa]te d|chocolat"),
    (r"^\s*mousses? (?:pur |de |d.)?(?:canard|foie|saumon|truite|poisson|c[èe]pes?|volaille)", "pate_terrine", None))]
_NOT_DRIED_TAGS = re.compile(r"(?:^|\s)en:(?:compotes?|apple-compotes|fruit-compotes|purees|fruit-purees|desserts|meals|plant-based-meals|dishes)(?:\s|$)|fr:compotes")
_LEAF_SALAD = re.compile(r"\b(?:m[âa]che|roquette|laitue|batavia|mesclun|jeunes? pousses?|feuilles? de ch[êe]ne|romaine|[ée]pinards?|lollo|scarole|frisée)\b", re.I)
_SALAD_DISH = re.compile(r"poulet|thon|saumon|jambon|crevettes?|[oœ]eufs?|fromage|ch[èe]vre|lardons?|taboul|\briz\b|p[âa]tes|quinoa|lentilles|c[ée]r[ée]ales|surimi|pizza|quiche|sandwich|wrap|compos[ée]e|repas|\bbol\b|bowl|c[ée]sar|vinaigrette|croûtons|croutons", re.I)
_CLASS_CACHE: Dict[Any, Dict[str, Any]] = {}


# A prepared dish that merely *contains* a cheese is not a cheese: it is a meal, and never a substitute for a block, a slice
# or a grated bag. Plural forms matter too - "Cordons bleus au Comté" and "Röstis de légumes et cheddar" are dishes.
_CHEESE_DISH = re.compile(
    r"cr[êe]pes?|galettes?|pizzas?|quiches?|sandwichs?|burgers?|gratins?|lasagn\w*|ravioli|tortellini|croques?|tartes?|"
    r"feuillet[ée]s?|cordons?[ -]bleus?|nuggets?|salades?|tartiflette|raclette (kit|pour)|jambon|poulet|saumon|p[âa]tes|paninis?|"
    r"wraps?|bagels?|soupes?|velout[ée]s?|b[ée]chamel|sauces?|carr[ée]s? de (bl[ée]|pomme)|risotto|quinotto|croquettes?|"
    r"beignets?|flan sal[ée]|r[ôöo]stis?|pav[ée]s? (au|aux|de|à)|boulettes?|bouch[ée]es?|po[êe]l[ée]es?|samoussas?|\bnems?\b|"
    r"accras?|aligot|tacos?|cakes? sal[ée]s?|muffins?|omelettes?|tortillas?|frittatas?|goug[èe]res?|cannellonis?|parmentiers?|hachis|"
    r"rigatonis?|pennes?|spaghettis?|tagliatelles?|fusillis?|macaronis?|gnocchis?|farfalles?|linguines?|pesto|pur[ée]es?|chips?|crisps?|"
    r"[ée]cras[ée]s?|pommes? de terre|pan[ée]s?\b|crackers?|souffl[ée]s?|boulgour|quinoa|poivronnade|croqs?\b|l[ée]gumes?\b|carpaccio|"
    r"yaourts?|yogourts?|yogurts?|glaces?",
    re.I)
# A product only FLAVOURED with a cheese ("Lay's saveur emmental") is not that cheese.
_CHEESE_FLAVOUR = re.compile(
    r"(saveur|go[ûu]t|ar[ôo]me|parfum)[^,.;]{0,20}"
    r"(emmental|comt[ée]s?\b|gruy[èe]res?\b|parmesan|cheddar|\bgouda\b|roquefort|camembert|\bbrie\b|mozzarella|ch[èe]vres?\b|feta\b|ricotta)",
    re.I)


# A drink is not the ingredient its name mentions ("limonade artisanale pomme aux épices", "boisson chocolatée").
# Coffee, tea, wine and beer are deliberately absent: they are flavors and ingredients as often as drinks
# ("glace au café", "coq au vin", "poulet à la bière" are foods, not beverages), and no ingredient type would
# claim them anyway - the drink guard only misfires on them.
_DRINK_NAME = re.compile(r"\b(?:boissons?|limonades?|jus|sodas?|cocktails?|smoothies?|nectars?|p[ée]tillants?|eaux?)\b", re.I)
# Raw ingredients and produce: when the name reads as a prepared dish that merely contains them, the dish wins.
_DISH_FAMILIES = {"meat_fish", "produce", "pantry", "dairy"}
_EXTRA_COMPONENT_TYPES = {"honey", "salt", "sugar", "flour", "spices", "oil", "butter", "milk", "nuts"}
# A word that makes this type impossible in its own right: a pâté is charcuterie (not pasta), a sausage is not a ham,
# and chocolate chips are not crisps.
# A "seeds" tag also marks cereals and pulses, which are not nuts.
# Anchored to real legume/cereal/pulse tags: the parent "legumes-and-their-products" also covers peanuts, which ARE nuts.
_NOT_NUTS_TAG = re.compile(r"(?:^|\s)en:(?:legumes?|pulses?|lentils?|chickpeas?|cereals?|quinoa|semolina|wheat|rice|buckwheat|barley|oats?|rye|corns?|maize)(?:\s|$)", re.I)
# A positive nut/peanut tag outranks a legume or cereal parent: OFF files peanuts under both.
_NUTS_TAG = re.compile(r"(?:^|\s)en:(?:nuts|peanuts?|almonds?|cashew-nuts?|pistachios?|walnuts?|hazelnuts?|nuts-and-their-products|roasted-nuts|salted-nuts)(?:\s|$)", re.I)
# Words that make a product something other than fresh fruit, whatever fruit tag it carries: juice, jam, compote, syrup,
# frozen or cooked versions, and anything baked or flavoured with the fruit.
_NOT_FRESH = re.compile(
    r"\b(?:jus|nectar|sirop|confiture|confit|chutney|compote|s[èeé]ch|secs?\b|surgel|conserve|au sirop|chips|crisps|yaourt|glace|"
    r"tarte|g[âa]teau|g[âa]teaux|boisson|p[ée]tillant|sauce|vinaigre|ar[ôo]me|parfum|saveur|eau|financiers?|biscuits?|cakes?|"
    r"muffins?|sorbets?|curds?|bonbons?|gel[ée]es?|poudres?|smoothies?|desserts?|m[ée]langes?)\b", re.I)
_TYPE_REJECTS = {
    "fresh_fruit": _NOT_FRESH,   # a jar of blueberries in syrup is not fresh fruit, whatever its "blueberries" tag says
    "ham": re.compile(r"saucissons?|saucisses?|salami|chorizo|lardons?|bacon|pancetta|rillettes?|p[âa]t[èéêe]\b|volaille|dinde|poulet", re.I),
    "pasta": re.compile(r"\bp[âa]t[èéêe]\b|charcut|p[âa]tes? de fruits", re.I),
    "chips": re.compile(r"chips? cookies?|chocolate chips?|chips? au chocolat|p[ée]pites? de chocolat", re.I),
    "fruits_veg": re.compile(r"pur[ée]es?|grill|marin|r[ôo]ti|oignons?[^a-zà-ÿ]{0,15}frits?|frits?[^a-zà-ÿ]{0,15}oignons?|onions?[^a-zà-ÿ]{0,15}fried|fried[^a-zà-ÿ]{0,15}onions?|r[öo]st\w*zwiebel\w*", re.I),   # a purée, a grilled vegetable or fried onions are other preparations
    "corn": re.compile(r"flakes?|chips?|pop[ -]?corn|flocons?|cereals?|muesli|granola|salad|soupe?|soup|glace|ice cream|g[âa]teaux?|biscuits?|galettes?|cr[êe]pes?|gaufres?", re.I),   # corn flakes, popcorn, corn cakes and corn snacks are not corn
    # A coffee is not a dessert or a dairy product: "glace au café" and "yaourt café" are those products, not coffee.
    "coffee_beans": re.compile(r"glaces?|ice cream|sorbet|yaourts?|yogurts?|mousse|g[âa]teaux?|cakes?|desserts?", re.I),
    "ground_coffee": re.compile(r"glaces?|ice cream|sorbet|yaourts?|yogurts?|mousse|g[âa]teaux?|cakes?|desserts?", re.I),
    "instant_coffee": re.compile(r"glaces?|ice cream|sorbet|yaourts?|yogurts?|mousse|g[âa]teaux?|cakes?|desserts?", re.I),
    # A dairy dessert is not automatically a spoon dessert: a vanilla yogurt is a yogurt.
    "dessert": re.compile(r"yaourts?|yogurts?|glaces?|sorbet", re.I),
    # Peanuts and tree nuts are sold as nuts, not pulses, whatever parent "legumes" tag they carry.
    "legumes": re.compile(r"cacahu[èe]tes?|peanuts?|noix|almonds?|pistaches?|pignons?|noisettes?|graines", re.I),
    # A poultry rillettes or pâté is a spread, not slices.
    "deli_poultry": re.compile(r"rillettes?|terrines?|p[âa]t[ée]\b|p[âa]t[ée]s? (?:de|à|en)", re.I),
    # A "barre granola" is a snack bar, not a box of muesli.
    "muesli": re.compile(r"\bbarres?\b", re.I),
    # A galette or wafer made of rice is a crisp, not a grain of rice; rice flour and rice drinks are not rice either.
    "rice": re.compile(r"galettes?|crisp|wafers?|reiswaffeln|farine|flocons?|pudding|au lait|boisson|drink|sirop", re.I),
    # Dried fruit inside a biscuit, cake, bar or dish is that product, not a pack of dried fruit.
    "dried_fruit": re.compile(r"pur[ée]e|orge\b|tajine|couscous|boulgour|semoule|poulet|porc\b|lapin|agneau|canard|farci|biscuits?|cookies?|sabl[ée]s?|cakes?|g[âa]teaux?|muffins?|muesli|\bbarres?\b|\bpain\b|brioche|crackers?|tartes?|confiture|compote|\bjus\b|nectar|glaces?|sorbet|vin\b|bi[èe]re|p[âa]t[ée]s? de fruits|croustilles?|chips|m[ée]lange.*noix", re.I),
    # "Pois chiches très peu de jus" is chickpeas canned in juice, not a juice.
    "fruit_juice": re.compile(r"pois chiches?|lentilles?|haricots?|l[ée]gumes?|conserves?|au jus|dans son jus|ma[ïi]s\b", re.I),
}
# Name-level exclusions found by auditing alternatives for the 1,000 most-scanned products (scripts/audit_alternatives.py): a name that
# says the product is something else keeps it out of the type, so it neither gets nor is offered as that type's alternatives.
_MORE_REJECTS = {
    "vinegar": r"oignons?|cornichons?|l[ée]gumes?|c[âa]pres|piments?|vinaigrettes?|assaisonnements?",
    "wine": r"saumon|pav[ée]s?|poisson|truite",
    "duck": r"frites?|pommes? de terre",
    "spices": r"^\s*(?:noix de cajou|amandes?|noisettes?|cacahu|th[ée]s? (?:vert|noir)|gel[ée]e|sorbet)",
    "honey": r"pops\b|c[ée]r[ée]ales|kellogg|chocolat|biscuit|pain d.[ée]pices|nougat|bonbon|moutarde|vinaigre|\bbarres?\b",
    "pickles": r"couscous|joues?|rosette|lay'?s|craquantes|saveur|chips|sandwich|jambon|saucisson|p[âa]t[ée]|bacon|porc|burger",
    "chicken": r"conserve|en bo[iî]te|semoule|\briz\b|basquaise",
    "pizza": r"sp[ée]cial pizza|r[âa]p[ée]s?\b|^\s*(?:sauce|p[âa]te|garniture|[ée]pices?|fromage)\b.{0,12}pizza",
    "potatoes": r"pur[ée]e|flocons|gratin|chips|frites|dauphine|r[öo]sti|galette",
    "plain_yogurt": r"[àa] boire|\bdrink|drinkable|brass[ée] [àa] boire",

    "flour": r"\bflan\b|bioflan|oignon|l[ée]gumes?|poulet|boeuf|bœuf|saumon|poisson",
    "fresh_fruit": r"truite|saumon|poisson|cabillaud|thon\b|poulet|filets? de|pav[ée]s? de|crevette|instant douceur|\bth[ée]\b|\btea\b|kombucha|skyr|bulles|boisson|cocktail|aloe|[ée]corce|\bpet\b|maytea|fuzetea|ice ?tea|th[ée] glac",
    "spirits": r"poulet|manchons?|mexicaine",
    "crackers": r"bolognaise|cr[êe]pes?",
    "syrup": r"[ée]dulcor",
    "corn": r"f[ée]cule|ma[ïi]zena|soufl[ée]s|cracky|corn dog|tartine|semoule|[ée]clater|enrob|boules?|\bpains?\b|bowl|grill|baguette",
    "dried_fruit": r"panettone",
    "instant_coffee": r"cappuccino|latte",
    "tea": r"glac[ée]|\bice\b|\bpet\b|fuze|kombucha|fresh tea",
    "rice": r"poulet|basquaise|tikka|lentilles|m[ée]lange",
    "hard_cheese": r"\bcmo\b|pizza|sabl[ée]s?|palets? ",
    "mayonnaise": r"vinaigrette|rouille|c[ae]e?sar|carsar",
    "fromage_blanc": r"salakis|\bfeta\b",
    "nuts": r"enrob|chocolat|\bchoco|kar[ée]\b|crocks|\bnoir\b|\blait\b|b[âa]tonnets",
    "fish_canned": r"\bfrais\b|\bfresh\b|\bsteaks?\b|pav[ée]s?\b|surgel|viennois|sandwich|wraps?|salades?",
    "viennoiserie": r"\bthon\b|jambon|fromage|pr[ée]paration",
    "soda": r"\beaux?\b|\bwater\b|perrier|badoit|salvetat|pellegrino|vichy|quezac|rozana|oulm[eè]s|energy|monster|red ?bull|powerade|nocco|gatorade|isotoni|qu[ée]zac|marguerite|carola|kombucha|(?:finement|fortement) p[ée]tillante|haribo|croco|\boeufs?\b|bonbons?",
    "water": r"juicy|\bjus\b|\bcoco\b|k[ée]fir|\bth[ée]\b|kombucha|saveurs?\b|aromatis|citron|framboise|p[êe]che|fraise|menthe|pamplemousse|essentiel",
    "sweet_biscuits": r"\bflan\b|\btartes?\b|\bbarres?\b|sal[ée]s?\b|ap[ée]ritifs?|fromage|bbq|^\s*(?:flocons?|porridge|muesli)\b|galettes? (?:[ée]peautre|de riz|lentilles|pois|sarrasin)",
    "chocolate_bar": r"carob|caroube|pulver|poudre|p[âa]te [àa] tartiner|boisson|\bdrink\b",
    "muesli": r"cacahu|peanut|\bbeurre\b|\bcream\b|cr[èe]me|\bfava\b|snack|galettes?|bissli|bbq|barbecue",
    "breakfast_cereal": r"hemp|chanvre|graines? de|\bseeds?\b",
    "plant_drink": r"cr[èe]me|crema|\bcream\b|lait de coco|coconut milk|cuisine",
    "chips": r"\bfrites?\b|allumettes|pommes? noisettes|surgel|mc ?cain|c[ôo]t[ée] (?:brasserie|comptoir|resto)",
    "cream_cheese": r"tartares? (?:de|d['’])|saumon|algues?|escarg|noix de coco|\bthon\b|saumon|crevettes?|surimi",
    "dessert": r"fromage blanc|ribot|macarons?|prot[ée]in|skyr|k[ée]fir|lait ferment|activia|bifidus|saint agur|cacao noir|au sirop|corne de gazelle",
    "baguette": r"gluten de bl[ée]|farine",
    "veggie_patty": r"\btofu\b|prot[ée]ines? de|gros vrac",
    "ready_meal": r"corned|sprats|\bmoules\b|maquereaux?|sardines?|\bthon\b|mac[ée]doine|brochettes|couscous (?:moyen|fin|grain)|graine",
    "pasta": r"^\s*sauces?\b|bolognaise|carbonara|konjac|shirataki|fromages? r[âa]p|r[âa]p[ée]s?\b|emmental|p[âa]tes? [àa] (?:tartiner|sandwich|pizza|tarte|cr[êe]pes?|g[âa]teau)|p[âa]te? (?:feuillet|bris|sabl)",
    "ham": r"petits pots|\bbols?\b|coquillettes|pizzas?|\bcmo\b|pi[ée]montaise|salades?|croques?|monster munch|\bchips\b|salad|paniers?|fromage|emmental|calzones?|croissants?",
    "cakes": r"jambon|emmental|champignons?|fromages?|l[ée]gumes|lentilles|saucisson|panciotti|galettes? (?:de|aux|[àa] base|[ée]peautre)|\bflan\b|g[âa]teau de (?:riz|semoule)|bolognaise|\bbarres?\b|prot[ée]in|english|anglais",
    "jam": r"confiture (?:de|au) lait|maggi|mad[èe]re",
    "sugar": r"\bflan\b|desserts?|cr[èe]me|go[ûu]ter|[ée]dulcor|stevia|bioflan|s[iy]?rop|yacon",
    "oil": r"om[ée]ga|capsules?|foie de morue|pur[ée]e|cr[èe]me de|\bforte\b",
    "cheese": r"fromage (?:frais|blanc)|viande|instant douceur|fromage fruits|aux fruits|biscuits?|crackers?|ap[ée]ritifs?|sabl[ée]s?|palets? ",
    "dough": r"friands?|petits fours|viande|jambon|saucisses?|saumons?|fromage|emmental|paniers?",
    "fresh_goat_cheese": r"brass[ée]|yaourts?|fromage blanc|seitan|lardons|viande|\bcroc|involtini|biscuits?",
    "deli_poultry": r"nuggets?|pan[ée]s?\b|tenders|pommes? de terre|cordons?|beignets?|donuts?|manchons?|cuisses?|mexicaine|pilons?|grignottes|sticks",
    "cream": r"anglaise|[ée]pinards|mascarpone|biscoff|lait concentr",
    "burger_buns": r"steak|hach[ée]|raclette|leerdammer|sensational|\bmeat\b|pollo|frites|v[ée]g[ée]|garden gourmet|hamburger|cheddar|emmental|bbq|\bmg\b|montagnarde|beyond|coeur de burger|instant burger",
    "salt": r"\bchips\b|goma|\bnuts\b|anchois|\bnoix\b",
    "stock_cube": r"ap[ée]ricube",
    "candy": r"citrons? confits|sp[ée]cialit[ée] v[ée]g[ée]tale|\bbarres?\b|pulver|caroube|carob",
    "beer": r"levure|pommes? de terre|pur[ée]e|cr[èe]me|cuisine",
    "sausage": r"lentilles|saucissons?|s[èe]ches?\b|viande s[ée]ch[ée]e|prot[ée]ines de pois",
    "mozzarella_fresh": r"\bfeta\b|ricotta|[ée]pinards|\bcmo\b|fromages\b|fingers|r[âa]p[ée]e?s?\b|skyr|stracciatella|girasoli|v[ée]g[ée]tal",
    "peanut_butter": r"cookies?|\bcups?\b|biscuits?|crackers?|pretzels?|\bbars?\b|cereals?|ice cream|\bfilled\b|sandwich|granola|balls?\b|bites?\b",
    "supplement": r"yaourts?|\bbarres?\b|shaker",
    "fruit_nut_bar": r"\bpains?\b",
    "soup": r"danone|velout[ée] nature|papillotes",
    "compote": r"paillasson|pommes? de terre",
    "milk": r"toilette|corporel|body|d[ée]maquillant|hydratant|nettoyant|pur[ée]e|\bcoco\b|coconut|poudre|concentr[ée]|lait d.(?:amande|avoine|soja|riz|noisette|coco)|lait (?:de )?(?:amande|avoine|soja|riz|noisette)|poudre|concentr",
    "ground_coffee": r"con leche|instant|soluble|lyophilis|latte|cappuccino|\bsticks?\b|boisson|glac[ée]|iced|\bice\b|cold brew|frapp[ée]|liqueur",
    "sauce": r"anglaise|papillotes|soja cuisine",
    "tomato_sauce": r"\bchili\b",
    "cereal_bar": r"\brepas\b",
}
for _t, _pat in _MORE_REJECTS.items():
    _old = _TYPE_REJECTS.get(_t)
    _TYPE_REJECTS[_t] = re.compile((_old.pattern + "|" if _old else "") + _pat, re.I)
# English-language names (the US market): a prepared product that merely names its main ingredient is not that ingredient.
_EN_REJECTS = {
    "chicken": r"broth|stock|soup|bouillon|noodles?|ramen|seasoning|flavou?red",
    "beef": r"jerky|broth|stock|stew|soup|bouillon|seasoning|ramen|noodles?|ravioli|burrito|bourguignon|gravy",
    "lardons": r"\bbits\b|bacos|crumbles?|bacon[- ]flavou?red|bacon[- ]wrapped",
    "burger_buns": r"^\s*(?:hot ?dogs?|franks?|wieners?|hamburger patt\w+|patties|burgers?)\b(?!.*\bbuns?\b)|\bpatt(?:y|ies)\b(?!.*\bbuns?\b)",
    "salt": r"caramels?|chocolates?|chips|vinegar|pretzels?|nuts|almonds|popcorn|crackers?|seasoning blend",
    "pizza": r"\b(?:sauce|dough|crust|seasoning|rolls?|cutters?|stone)\b",
    "pasta": r"^\s*(?:pasta )?sauces?\b|pasta sauce|pasta salad|pasta bake|salad",
    "cakes": r"syrup|sirop|\bmix\b|rice cakes?|\bcakes? mix",
    "beer": r"root beer|ginger beer|birch beer|beer bread|beer cheese|beer batter",
    "oil": r"spray cooking|cooking spray|olive oil spray|mayo",
    "sweet_biscuits": r"\bbutter(?:ed)? (?:popcorn|beans)",
    "chips": r"sour cream (?:&|and) onion dip|\bdip\b",
    "tea": r"green beans?|green peas|tea tree",
}
for _t, _pat in _EN_REJECTS.items():
    _old = _TYPE_REJECTS.get(_t)
    _TYPE_REJECTS[_t] = re.compile((_old.pattern + "|" if _old else "") + _pat, re.I)
# OFF's broad "en:meals" tag also lands on dry couscous, quinoa and bagged salads. A ready meal needs a tag that names a
# prepared dish; raw grain/produce tags without one keep the product out of ready_meal.
_READY_DISH_TAG = re.compile(
    r"prepared-(?!vegetables\b|potatoes\b|fruits?\b)|-\w*dishes\b|meals-with|canned-meals|plant-based-meals|microwave-meals|"
    r"frozen-meals|lasagn\w*|pizzas?\b|quiches?\b|sandwiches\b|burgers?\b|cannelloni|ravioli|stews?|casseroles?|"
    r"tarts?\b|pies?\b|pot-au-feu| ready-meals|prepared-meals", re.I)
_READY_RAW_TAG = re.compile(
    r":couscous\b|:quinoa\b|cereal-grains|cereal-semolinas|wheat-semolinas|durum-wheat|cereals-and-their-products|"
    r":seeds\b|:rice\b|:flour\b|fruits-and-vegetables-based-foods|vegetables-based-foods|fresh-fruits?|fresh-vegetables|:pulses\b", re.I)
# Cooked poultry sold as charcuterie ("blanc de poulet", "filet rôti"): the tags that make a bird product deli, not raw.
# Poultry-specific on purpose - the broad "prepared-meats"/"charcuteries-cuites" tags also cover ham and pâté.
_DELI_TAG = re.compile(
    r"prepared-poultry|prepared-chicken|prepared-turkey|cooked-chicken|cooked-poultry|cooked-turkey|poultry-hams|"
    r"charcuterie-de-volaille|reconstituted-chicken", re.I)
# A flavoured yogurt is not a plain one, whatever generic "yogurts" tag it carries.
_FLAVOURED_YOGURT = re.compile(
    r"vanille|vanilla|chocolat|chocolate|schoko|stracciatella|fraise|framboise|myrtille|fruit|miel|honey|caramel|p[ée]pite|cookie|sp[ée]culoos|coco|"
    r"citron|p[êe]che|peach|abricot|banane|mangue|noisette|amande|cr[èe]me glac[ée]e|sucr[ée]|"
    r"pfirsich|maracuja|erdbeer|kirsche|himbeer|apfel|zitrone", re.I)


# A prepared dish that merely contains an ingredient (a galette jambon, a tarte au chocolat). Unlike _CHEESE_DISH this
# leaves out the ingredients that are also dish-sounding on their own: "Filets de poulet" and "Purée de carotte" stay
# poultry and produce.
_DISH_CONTEXT = re.compile(
    r"cr[êe]pes?|galettes?|pizzas?|quiches?|sandwichs?|burgers?|gratins?|lasagn\w*|ravioli|tortellini|croques?|tartes?|"
    r"tartelettes?|feuillet[ée]s?|cordons?[ -]bleus?|nuggets?|salades?|tartiflette|raclette (kit|pour)|p[âa]tes\b|paninis?|"
    r"wraps?|bagels?|tartinables?|sauces?|carr[ée]s? de|risotto|quinotto|croquettes?|beignets?|flan sal[ée]|"
    r"r[ôöo]stis?|pav[ée]s? (au|aux|de|à)|boulettes?|bouch[ée]es?|po[êe]l[ée]es?|samoussas?|\bnems?\b|accras?|aligot|"
    r"tacos?|cakes? sal[ée]s?|muffins?|omelettes?|tortillas?|frittatas?|goug[èe]res?|cannellonis?|parmentiers?|hachis|"
    r"rigatonis?|pennes?|spaghettis?|tagliatelles?|fusillis?|macaronis?|gnocchis?|farfalles?|linguines?|pesto|moussaka|ratatouille|\btian\b|couscous|paella",
    re.I)


def _ingredient_not_standalone(tid: str, family: str, name: str) -> bool:
    """A drink named after an ingredient is a drink, and a dish named after an ingredient is a dish: neither is that
    ingredient for substitution purposes (a lemonade aux épices is not a spice, a galette jambon is not a ham)."""
    if family == "drinks":
        return False
    if tid in ("fish_canned", "legumes"):
        # Preserved foods are packed IN a liquid or sauce: "sardines au jus", "maquereaux au vin blanc",
        # "pois chiches très peu de jus" are still the food, not a drink or a dish.
        # Only a real beverage word (boisson, soda, ...) disqualifies them - packing liquids do not.
        stripped = re.sub(r"\bvin\s+(?:blanc|rouge|ros[ée])\b|\bjus\b", " ", name, flags=re.I)
        if _DRINK_NAME.search(stripped):
            return True
        # A pulse named inside a prepared dish ("couscous de pois chiches", "... façon moussaka") is the dish, not the pulse.
        return tid == "legumes" and bool(_DISH_CONTEXT.search(name))
    if _DRINK_NAME.search(name):
        return True
    if (family in _DISH_FAMILIES or tid in _EXTRA_COMPONENT_TYPES) and _DISH_CONTEXT.search(name):
        return True
    return False


def _not_a_cheese(name: str) -> bool:
    """A prepared dish, or a product merely flavoured with a cheese, must never be classified as a cheese."""
    return bool(_CHEESE_DISH.search(name) or _CHEESE_FLAVOUR.search(name))


def classify(p: Dict[str, Any]) -> Dict[str, Any]:
    """Memoised _classify: the result depends only on categories, name, brand and generic name, and one request classifies each candidate many times (once per pair compared)."""
    key = (tuple(p.get("categories") or ()), p.get("name") or "", p.get("brand") or "", p.get("generic_name") or "")
    hit = _CLASS_CACHE.get(key)
    if hit is None:
        if len(_CLASS_CACHE) > 100_000:
            _CLASS_CACHE.clear()
        hit = _CLASS_CACHE[key] = _classify(p)
    return dict(hit)


_HEAD_SKIP = {"les", "des", "une", "the", "and", "with", "pour", "dans", "aux", "nos", "notre", "mon", "mes", "ses", "son", "sa"}


# First words that name a cut, a form or a whole aisle, not a product: sharing one says nothing about being a substitute.
_GENERIC_HEADS = set("filet filets confit boisson boissons legumes légumes legume légume plat plats sauce sauces préparation preparation melange mélange assortiment duo trio cocktail pate pâte tranche tranches cuisse cuisses aile ailes escalope escalopes pavé pave pavés morceaux dés des mini maxi spécialité specialite produit gamme coffret lot pack panier salade salades garniture accompagnement green black red white sweet hot cold sea energy sour salted spicy wild".split())


def _load_cat_groups() -> Dict[str, str]:
    try:
        import json, os
        with open(os.path.join(os.path.dirname(__file__), "data", "cat_groups.json")) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 - optional table (scripts/build_cat_groups.py); without it the old rules apply
        return {}


_CAT_GROUPS = _load_cat_groups()


def _group(t: Optional[str]) -> Optional[str]:
    """The named type a product belongs to: itself when a rule typed it, the dominant named type of its category tag otherwise."""
    if not t:
        return None
    if not str(t).startswith(_CATEGORY_TYPE):
        return t
    return _CAT_GROUPS.get(t)


def _head_word(p: Dict[str, Any]) -> Optional[str]:
    """The product's head noun: the FIRST word of its name that is not an article or a filler.
    It must be the first word on both sides, so a brand ("SOJASUN myrtilles") or a flavour never stands in for the product."""
    for w in re.split(r"[^a-zà-ÿ0-9]+", (p.get("name") or "").lower()):
        if len(w) > 2 and w not in _HEAD_SKIP and w not in _UNTYPED_STOP:
            return w
    return None


def _category_alternative(type_id: Optional[str], same_type: bool, co: Dict[str, Any], cc: Dict[str, Any]) -> Dict[str, Any]:
    """Two products the taxonomy relates only by category or by the same head noun: a real but broader alternative (level 2)."""
    return {"level": 2, "label": LABELS[2], "type": type_id, "same_type": same_type, "variant_diff": None,
            "confidence": "medium", "orig_confidence": co["confidence"], "cand_confidence": cc["confidence"],
            "form_match": True, "use_match": True}


def is_category_only(p: Dict[str, Any]) -> bool:
    """True when the product is typed by its category tag rather than by a type rule (every product has one or the other)."""
    return str(classify(p).get("type") or "").startswith(_CATEGORY_TYPE)


def is_uncategorised(p: Dict[str, Any]) -> bool:
    """True when no rule and no usable category tag describes the product (its category is the explicit 'uncategorised')."""
    return classify(p).get("type") == UNCATEGORISED


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


# A product no rule describes is typed by its category: "cat:" + the most specific non-generic Open Food Facts tag.
# Every product therefore has a category; one with no usable tag at all gets the explicit "uncategorised" one and can then
# only match another uncategorised product by a shared distinctive name word (never by category alone).
_CATEGORY_TYPE = "cat:"
UNCATEGORISED = _CATEGORY_TYPE + "en:uncategorised"
_GENERIC_LEAF = {"en:groceries", "en:foods", "en:beverages", "en:plant-based-foods", "en:plant-based-foods-and-beverages", "fr:autres-produits", "en:dietary-supplements", "en:meals", "en:snacks", "en:sauces", "en:condiments", "en:frozen-foods", "en:meats", "en:plant-based-foods-and-beverages-fruits", "en:fruits-and-vegetables-based-foods"}
_UNTYPED_STOP = set("avec sans pour dans plus bio extra fins fine fines france francais française français origine nature naturel naturelle format maxi mini grand grande petit petite recette original originale traditionnel traditionnelle selection sélection qualité saveur gout goût premium light cuit cuite cuits cuites cuisine cuisiné cuisinée cuisinés cuisinées préparé préparée préparés préparées cooked prepared".split())


def _dish_stem(w: str) -> str:
    """Plural tolerance for dish matching: 'aubergines' and 'aubergine' are the same ingredient."""
    return w[:-1] if len(w) > 3 and w.endswith("s") else w


_UT_CACHE: Dict[tuple, set] = {}


def _untyped_tokens(p: Dict[str, Any]) -> set:
    key = (p.get("name") or "", p.get("brand") or "")
    hit = _UT_CACHE.get(key)
    if hit is not None:
        return hit
    if len(_UT_CACHE) > 100_000:
        _UT_CACHE.clear()
    brand = {w for w in re.split(r"[^a-zà-ÿ0-9]+", (p.get("brand") or "").lower()) if w}
    hit = _UT_CACHE[key] = {w for w in re.split(r"[^a-zà-ÿ]+", (p.get("name") or "").lower()) if len(w) > 3 and w not in _UNTYPED_STOP and w not in brand}
    return hit


def _untyped_substitute(orig: Dict[str, Any], cand: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Two products the taxonomy has no type for (a rarely classified kind of food): they substitute each other when they share a specific category and a name word,
    or most of their distinctive name words. Never a type-less product for a typed one."""
    ot, ct = _untyped_tokens(orig), _untyped_tokens(cand)
    shared = ot & ct
    if not shared:
        return None
    ol = [c for c in (orig.get("categories") or []) if c not in _GENERIC_LEAF]
    cl = [c for c in (cand.get("categories") or []) if c not in _GENERIC_LEAF]
    same_leaf = bool(ol and cl and ol[-1] == cl[-1])
    close = len(shared) / max(1, min(len(ot), len(ct))) >= 0.67
    if ol and cl and not (same_leaf or set(ol[-2:]) & set(cl[-2:])):
        return None             # both are categorised and the categories differ
    if not (same_leaf or close):
        return None
    return {"level": 2, "label": LABELS[2], "type": None, "same_type": False, "variant_diff": None, "confidence": "medium", "orig_confidence": "medium", "cand_confidence": "medium", "form_match": True, "use_match": True}


# Not groceries at all (cosmetics, household, pet food): never an alternative to food, and never matched on a shared head word.
_NONFOOD = re.compile(r"\b(?:toilette|massage|karit[ée]|shea|corporel|body|shampoo?ing|shampoing|d[ée]maquillant|savon|dentifrice|d[ée]odorant|parfum(?:é)? d'ambiance|"
                      r"m[ée]nager|m[ée]nag[èe]re|lessive|d[ée]tergent|vaisselle|nettoyant|javel|adoucissant|bain|solaire|pour (?:chiens?|chats?|animaux)|"
                      r"chiens?|chats?|croquettes? (?:pour|chien|chat)|litière|aliment complet pour|cat food|dog food|pet food|bath|sunscreen|soap)\b", re.I)
# Plant-based/vegan versions of an animal product are a different product (the other side is the real thing, or vice versa).
_PLANT_MARK = re.compile(r"v[ée]g[ée]tal|v[ée]g[ée]talien|vegan|veggie|v[ée]g[ée]tarien|plant[- ]based|sans viande|sans lait|substitut|simili", re.I)
_ANIMAL_TYPES = {"ham", "chicken", "deli_poultry", "sausage", "dry_sausage", "pate_terrine", "butter", "cream", "cheese", "hard_cheese", "soft_ripened_cheese",
                 "mozzarella_fresh", "fresh_goat_cheese", "cream_cheese", "mayonnaise", "plain_yogurt", "flavoured_yogurt", "milk", "duck", "fish_canned", "smoked_fish", "burger_patty"}


def substitution(orig: Dict[str, Any], cand: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """HARD COMPATIBILITY GATE: Level 1-4 and why, or None when the candidate is not a substitute.
    Independent of nutrition and price. Enforces strict rules:
    - Low-confidence classifications are rejected from strict rankings
    - Incompatible product forms or purchasing purposes are rejected
    - Level 3/4 products can enter closest tab but not price/quality/value rankings
    """
    if _NONFOOD.search(orig.get("name") or "") or _NONFOOD.search(cand.get("name") or ""):
        return None
    co, cc = classify(orig), classify(cand)  # always computed fresh: a rule change must reach products that are already cached
    # A product typed only by its category ("cat:..."): the category itself is the small category. Two products of the same
    # specific category are alternatives; such a product never substitutes one that a real type rule describes, nor the
    # reverse. Different categories still need a shared distinctive name word, exactly like two untyped products.
    cat_o = str(co.get("type") or "").startswith(_CATEGORY_TYPE)
    cat_c = str(cc.get("type") or "").startswith(_CATEGORY_TYPE)
    if cat_o or cat_c:
        if cat_o and cat_c and co["type"] == cc["type"] and co["type"] != UNCATEGORISED:   # "uncategorised" is not a category
            return _category_alternative(cc["type"], True, co, cc)
        # Otherwise the two sides are described differently (a rule on one side, a tag or nothing on the other). The
        # product's head noun - the first distinctive word of its name, which is how grocery names are built - is then
        # the smallest category they provably share: "Myrtilles sauvages au sirop" and "Myrtilles sauvages".
        go, gc = _group(co["type"]), _group(cc["type"])
        if go and gc and go != gc:      # both sides resolve to a named group and the groups differ: never alternatives
            return None
        hw = _head_word(orig)
        if hw and hw == _head_word(cand) and hw not in _GENERIC_HEADS:
            ol = [c for c in (orig.get("categories") or []) if c not in _GENERIC_LEAF]
            cl = [c for c in (cand.get("categories") or []) if c not in _GENERIC_LEAF]
            # both categorised and the categories differ: "Filet de crocodile" is not "Filet de poulet"
            # same OFF category tree: the specific side's own category (or its parent) is among the other's categories
            if ol and cl and (set(ol[-3:]) & set(cl) or set(cl[-3:]) & set(ol)):
                return _category_alternative(cc["type"], False, co, cc)
        if cat_o != cat_c and UNCATEGORISED in (co["type"], cc["type"]) and not (orig.get("categories") or cand.get("categories")):
            return None     # a typed product and one with no category to compare: a shared first word ("green tea", "green beans") proves nothing
        return _untyped_substitute(orig, cand)
    if not co["type"] and not cc["type"]:
        return _untyped_substitute(orig, cand)

    # HARD GATE: Reject low-confidence classifications, with one exception: two products whose names independently
    # named the exact same specific type still agree with each other, even without a supporting category tag (common
    # for a product with thin or non-canonical Open Food Facts data - a missing category must not mean zero
    # alternatives when the name alone already says plainly what it is). Capped below at level 2: name alone never
    # earns "almost identical". Either side fully unclassified, or the two sides naming different types, still rejects.
    name_only_agreement = False
    if co["confidence"] in ("none", "low") or cc["confidence"] in ("none", "low"):
        if co["confidence"] == "none" or cc["confidence"] == "none" or co["type"] != cc["type"]:
            return None
        name_only_agreement = True

    # HARD GATE: a plant-based imitation never stands in for the animal product (or the reverse) when the name says so on one side only
    if co["type"] in _ANIMAL_TYPES or cc["type"] in _ANIMAL_TYPES:
        if bool(_PLANT_MARK.search(orig.get("name") or "")) != bool(_PLANT_MARK.search(cand.get("name") or "")):
            return None

    # HARD GATE: Both must have a valid type
    if not co["type"] or not cc["type"]:
        return None

    # HARD GATE: Check form and use compatibility
    if co["form"] != cc["form"] and co["use"] != cc["use"]:
        # Different form AND different use case = not a substitute
        return None

    # Check type compatibility via clusters
    lv = level_between(co["type"], cc["type"])
    if lv is None:
        return None  # No cluster relationship exists - completely incompatible types
    if name_only_agreement:
        lv = max(lv, 2)   # name alone, with no category tag on either side, never reaches "almost identical"

    # Two ready meals share an aisle, not a dish: without a shared ingredient word or a shared specific category tag
    # they are only a broad alternative (level 4), never "very similar" - a lasagne is not a substitute for ratatouille.
    if lv <= 2 and co["type"] == cc["type"] == "ready_meal":
        stems_o = {_dish_stem(w) for w in _untyped_tokens(orig)}
        stems_c = {_dish_stem(w) for w in _untyped_tokens(cand)}
        leaf_o = {t for t in (orig.get("categories") or []) if t not in _GENERIC_LEAF}
        leaf_c = {t for t in (cand.get("categories") or []) if t not in _GENERIC_LEAF}
        if not (stems_o & stems_c) and not (leaf_o & leaf_c):
            lv = 4

    # Variant handling
    vo, vc = variant(orig, co["type"]), variant(cand, cc["type"])
    diff = [vo, vc] if co["type"] == cc["type"] and vo and vc and vo != vc else None
    if diff and co["type"] in _HARD_VARIANT_TYPES and "standard" not in diff:
        return None    # hazelnuts lead to hazelnuts, not to almonds or mixed fruit
    if co["type"] == cc["type"] in _HARD_VARIANT_TYPES and ((vo or "standard") == "standard") != ((vc or "standard") == "standard"):
        lv = min(4, lv + 2)   # one side names its variant, the other is generic: related products, never the same one

    # Nut-specific handling
    if co["type"] == cc["type"] == "nuts":
        po, pc = nut_prep(orig), nut_prep(cand)
        if po["shell"] != pc["shell"]:
            return None     # in-shell nuts are sold by the weight of the shell: not a like-for-like price or a substitute for shelled ones
        odd = [k for k in ("roast", "salt") if po[k] and pc[k] and po[k] != pc[k]]
        if odd:
            lv = min(4, lv + 1)     # raw vs roasted, plain vs salted: still nuts, but no longer the same product
            diff = diff or [po[odd[0]], pc[odd[0]]]

    if diff and co["type"] == cc["type"] == "plant_drink":
        lv = min(4, lv + 2)   # a different base (rice vs oat vs soy vs almond) is a real difference in taste, texture and
        # cooking behaviour - a genuine but broader alternative, not "almost identical", and not excluded outright either

    # Build structured explanation
    explanation = {
        "level": lv,
        "label": LABELS[lv],
        "type": cc["type"],
        "same_type": co["type"] == cc["type"],
        "variant_diff": diff,
        "confidence": min(co["confidence"], cc["confidence"]),  # Lower of the two
        "orig_confidence": co["confidence"],
        "cand_confidence": cc["confidence"],
        "form_match": co["form"] == cc["form"],
        "use_match": co["use"] == cc["use"],
    }

    return explanation


# Variants inside one product type: a real difference the shopper should know about, disclosed as a trade-off (never a reason to hide the product).
_VARIANTS = {
    "smoked_fish": [("salmon", r"saumon|salmon"), ("trout", r"truite|trout"), ("herring", r"hareng|herring"), ("mackerel", r"maquereau|mackerel"), ("haddock", r"haddock|églefin|eglefin"), ("swordfish", r"espadon|swordfish")],
    "butter": [("margarine", r"margarine|tartine(?:r|s)?\b|matière grasse|spread"), ("clarified", r"beurre clarifi|ghee")],
    "spirits": [("whisky", r"whisk|bourbon|scotch"), ("rum", r"\brhum\b|\brum\b"), ("vodka", r"vodka"), ("gin", r"\bgin\b"), ("liqueur", r"liqueur|cr[èe]me de|amaretto|limoncello|cointreau|baileys"), ("brandy", r"cognac|armagnac|brandy|calvados")],
    "deli_poultry": [("turkey", r"dinde|turkey"), ("chicken", r"poulet|chicken|volaille"), ("nuggets", r"nuggets?|aiguillettes?|panée?s?|cordon bleu")],
    "tapenade": [("tomato", r"tomates?|tomato"), ("eggplant", r"aubergines?|eggplant"), ("bell_pepper", r"poivrons?|pepper"), ("olive_tap", r"olives?|tapenade (?:verte|noire)")],
    "pickles": [("caper", r"c[âa]pres?\b|capers?\b|capucines?"), ("gherkin", r"cornichons?|gherkins?|\bpickles?\b"), ("onion", r"oignons?|onions?|grelots?")],
    "fruits_veg": [("veg_mix", r"m[ée]lange|macédoine|jardini[èe]re|po[êe]l[ée]e|ratatouille|l[ée]gumes? pour|mix de l[ée]gumes|\bmix\b"),
                   ("tomato", r"tomate|tomato|passata|polpa"), ("carrot", r"carotte|carrot"), ("green_bean", r"haricots? verts?|green-beans|green beans"),
                   ("bean", r"haricot|\bbeans?\b|flageolet|lingot"), ("pea", r"petits? pois|\bpois\b|\bpeas?\b"), ("spinach", r"[ée]pinard|spinach"),
                   ("leek", r"poireau|leek"), ("zucchini", r"courgette|zucchini"), ("eggplant", r"aubergine|eggplant"), ("bell_pepper", r"poivron|bell-pepper"),
                   ("cabbage", r"\bchou\b|\bchoux\b|chou-fleur|brocoli|cabbage|cauliflower|broccoli"), ("beet", r"betterave|beet"), ("onion", r"oignon|onion|[ée]chalote"),
                   ("corn", r"ma[ïi]s|sweetcorn|sweet-corn"), ("artichoke", r"artichaut|artichoke"), ("asparagus", r"asperge|asparagus"), ("fennel", r"fenouil|fennel"),
                   ("celery", r"c[ée]leri|celery")],
    "tomato_sauce": [("ketchup", r"ketchup"), ("bolognese", r"bolognaise|bolognese|b[œo]uf|viande")],
    "mozzarella_fresh": [("feta", r"\bfeta\b"), ("ricotta", r"ricotta"), ("burrata", r"burrata|stracciatella")],
    "mayonnaise": [("vinaigrette", r"vinaigrette|assaisonnement|sauce salade")],
    "tea": [("iced_tea", r"ice[d ]?-?tea|th[ée]s? glac|iced-teas|sweetened-beverages|soft-drinks|boisson")],
    "dough": [("puff", r"feuillet|puff"), ("shortcrust", r"bris[ée]e|sabl[ée]e|shortcrust")],
    "supplement": [("protein", r"prot[ée]ine|whey|protein"), ("vitamin", r"vitamine|vitamin|magn[ée]sium|\bzinc\b|\bfer\b|om[ée]ga|calcium|multivit"), ("spirulina", r"spiruline|spirulina|chlorelle")],
    "pate_terrine": [("fish", r"thon|saumon|sardine|maquereau|poisson|crevette"), ("rillettes", r"rillettes?"), ("foie_gras", r"foie gras|bloc de foie")],
    "dried_fruit": [("mix", r"m[ée]lange|assortiment|\bmix\b|cocktail|fruits? secs"), ("raisin", r"raisin|sultanine|corinthe"), ("prune", r"pruneau|\bprunes?\b"),
                    ("date", r"datte|\bdates?\b"), ("fig", r"figue"), ("apricot", r"abricot|apricot"), ("cranberry", r"cranberr|craisin|airelle"), ("goji", r"goji"),
                    ("mango", r"mangue|mango"), ("banana", r"banane|banana"), ("apple", r"pomme|apple"), ("pineapple", r"ananas|pineapple"), ("blueberry", r"myrtille|blueberry")],
    "plain_yogurt": [("greek", r"\bgrec|greek|skyr|\bgrecque")],
    "fresh_fruit": [("apple", r"pomme(?! de terre)|apple"), ("banana", r"banane|banana"), ("orange", r"orange|cl[ée]mentine|mandarine|citron|lemon|pamplemousse"),
                    ("pineapple", r"ananas|pineapple"), ("strawberry", r"fraise|strawberry"), ("raspberry", r"framboise|raspberry"),
                    ("blueberry", r"myrtille|blueberry|groseille|currant|cassis"), ("pear", r"poire|pear"), ("peach", r"p[êe]che|peach|nectarine|abricot|apricot"),
                    ("grape", r"raisin|grape"), ("melon", r"melon|past[èe]que|watermelon"), ("plum", r"prune|plum|quetsche|mirabelle"),
                    ("kiwi", r"kiwi"), ("mango", r"mangue|mango"), ("cherry", r"cerise|cherry"), ("fig", r"figue|fig\b"),
                    ("date", r"datte|date\b"), ("avocado", r"avocat|avocado")],
    "baguette": [("wholemeal", r"complet|int[ée]gral|wholemeal|whole[- ]?wheat|seigle|c[ée]r[ée]ales|graines")],
    "sandwich_bread": [("wholemeal", r"complet|int[ée]gral|wholemeal|whole[- ]?wheat|seigle|c[ée]r[ée]ales|graines")],
    "flour": [("coconut", r"coco"), ("almond", r"amande|almond"), ("rice", r"\briz\b|\brice\b"), ("chestnut", r"ch[âa]taigne|chestnut"), ("buckwheat", r"sarrasin|buckwheat"),
              ("chickpea", r"pois chiche|chickpea"), ("corn", r"ma[ïi]s|corn"), ("spelt", r"[ée]peautre|spelt"), ("semolina", r"semoule|semolina")],   # coconut or almond flour is not wheat flour
    "oil": [("olive", r"olive|oliva")],
    "nuts": [("hazelnut", r"noisette|hazelnut"), ("almond", r"amande|almond"), ("walnut", r"\bnoix\b(?! de (coco|cajou|p[ée]can))|walnut"), ("peanut", r"cacahu|peanut|arachide"),
             ("cashew", r"cajou|cashew"), ("pistachio", r"pistache|pistachio"), ("pecan", r"p[ée]can|pecan"), ("coconut", r"noix de coco|coconut"),
             ("dried_fruit", r"fruits? secs?|raisin|abricot|datte|figue|cranberr|pruneau|dried[- ]fruit"), ("seeds", r"graines|seeds|tournesol|courge|s[ée]same|lin\b|chia"),
             ("mixed", r"m[ée]lange|mix|cocktail|assorti")],
    "dip": [("hummus", r"houm[ou]{1,2}s|hummus"), ("tarama", r"tarama"), ("tzatziki", r"tzatziki"), ("guacamole", r"guacamole"), ("pepper", r"ktipiti|poivron|mouhamara"), ("aubergine", r"aubergine|baba"), ("salsa", r"\bsalsa\b|mexic\w*")],   # a houmous leads to houmous, a tarama to tarama
    "peanut_butter": [("almond", r"amande|almond"), ("hazelnut", r"noisette|hazelnut"), ("peanut", r"cacahu|peanut|arachide"), ("cashew", r"cajou|cashew"), ("sesame", r"s[ée]same|tahin|tahini"), ("pistachio", r"pistache|pistachio"), ("pecan", r"p[ée]can|pecan")],   # an almond purée is not a peanut butter
    "milk": [("skimmed", r"[ée]cr[ée]m|skimmed"), ("whole", r"entier|whole")],
    # Rice, almond, soy, oat and coconut drinks share nothing but being "a plant-based drink": different base, taste,
    # texture and cooking behaviour. A shopper choosing rice-coconut milk is not well served by a barley drink.
    "plant_drink": [("rice", r"\briz\b|\brice\b"), ("almond", r"amande|almond"), ("soy", r"soja|soy"), ("oat", r"avoine|\boat\b"),
                     ("coconut", r"coco(?!a)|coconut"), ("hazelnut", r"noisette|hazelnut"), ("spelt", r"[ée]peautre|spelt"), ("barley", r"orge|barley")],
    "olives": [("green", r"verte?s?\b|green"), ("black", r"noire?s?\b|black|kalamata"), ("stuffed", r"farci|stuffed"), ("pitted", r"d[ée]noyaut|pitted")],
    "syrup": [("maple", r"[ée]rable|maple"), ("agave", r"agave")],     # maple syrup is not agave syrup: different taste, different product
    # A can of kidney beans is not a can of chickpeas: pulses are different products, not shapes of one.
    "legumes": [("haricot_rouge", r"haricots?[- ]rouges?|kidney"), ("pois_chiche", r"pois chiches?|chickpeas?|garbanzo"),
                ("lentille", r"lentilles?|corail"), ("feve", r"f[èe]ves?|fava|broad beans"),
                ("haricot_blanc", r"haricots?[- ](?:blancs?|cocos?)|cannellini|flageolets?|navy beans?"),
                ("azuki", r"azuki|adzuki|black beans?|noires?")],
    # Soba (buckwheat) and rice noodles are not wheat pasta: different flour, texture and use.
    "pasta": [("soba", r"\bsoba\b|sarrasin|buckwheat"), ("rice_noodle", r"nouilles? de riz|rice noodles?|vermicelle de riz|\bpho\b")],
}


_VAR_CACHE: Dict[tuple, Optional[str]] = {}


def variant(p: Dict[str, Any], type_id: Optional[str]) -> Optional[str]:
    """Which variant of its type this product is (e.g. greek / plain yogurt), or None when the type has no variants. Looks at the name and the category tags."""
    key = (type_id or "", p.get("name") or "", tuple(p.get("categories") or []))
    hit = _VAR_CACHE.get(key, False)
    if hit is not False:
        return hit
    if len(_VAR_CACHE) > 100_000:
        _VAR_CACHE.clear()
    rules = _VARIANTS.get(type_id or "")
    if not rules:
        return _VAR_CACHE.setdefault(key, None)
    text = ((p.get("name") or "") + " " + " ".join(p.get("categories") or [])).lower()
    for name, rx in rules:
        if re.search(rx, text):
            return _VAR_CACHE.setdefault(key, name)
    return _VAR_CACHE.setdefault(key, "standard")


def nut_prep(p: Dict[str, Any]) -> Dict[str, Any]:
    """How a nut product is prepared, from its name: in shell or shelled, raw or roasted, salted or plain. None = the name does not say."""
    t = str(p.get("name") or "").lower()
    shell = bool(re.search(r"en coque|in[- ]shell|\bcoque\b", t)) and not re.search(r"d[ée]cortiqu|shelled|sans coque", t)
    roast = "raw" if re.search(r"non grill|crue?s?\b|nature|raw|unroasted|non torr", t) else "roasted" if re.search(r"grill|torr[ée]f|roast", t) else None
    salt = "plain" if re.search(r"sans sel|non sal|unsalted|no salt", t) else "salted" if re.search(r"\bsal[ée]e?s?\b|salted", t) else None
    return {"shell": shell, "roast": roast, "salt": salt}


# Types where a different variant is a different product, not a trade-off: hazelnuts are not almonds, almonds are not raisins.
_HARD_VARIANT_TYPES = {"smoked_fish", "butter", "spirits", "tapenade", "pickles", "fruits_veg", "tomato_sauce", "mozzarella_fresh", "mayonnaise", "tea", "dough", "supplement", "pate_terrine", "dried_fruit", "nuts", "peanut_butter", "dip", "syrup", "fresh_fruit", "legumes", "pasta", "flour"}


# Words that find a product type by name in a full-text index (OR, accent-free), so a competing brand is found whatever it calls its product.
# Used only to widen the candidate pool; compatibility is still decided by substitution().
TYPE_TERMS: Dict[str, List[str]] = {
    "olives": ["olives", "olive verte", "olive noire", "aceitunas"],
    "chicken": ["poulet", "filet de poulet", "aiguillette de poulet"],
    "turkey": ["dinde", "escalope de dinde"], "duck": ["canard", "magret"],
    "beef": ["boeuf", "bœuf", "steak haché"], "pork": ["porc", "rôti de porc"],
    "beer": ["bière"], "wine": ["vin rouge", "vin blanc", "vin rosé"], "ice_cream": ["glace", "crème glacée"],
    "salt": ["sel fin", "gros sel", "sel marin"], "spices": ["épices", "paprika", "poivre", "cumin"], "flour": ["farine", "semoule"],
    "potatoes": ["pommes de terre", "patates"], "fresh_fruit": ["pommes", "bananes", "oranges"], "dough": ["pâte feuilletée", "pâte brisée"],
    "tart": ["tarte", "tartelette"], "sauce": ["sauce"], "dessert": ["dessert", "mousse"],
    "drink_syrup": ["sirop de citron", "sirop de menthe"], "supplement": ["complément alimentaire", "vitamines"],
    "speculoos": ["speculoos", "spéculoos", "speculaas", "biscoff"],
    "herbal_lozenge": ["pastilles gorge", "ricola", "valda", "bonbons plantes menthol"],
    "chocolate_spread": ["pâte à tartiner"],
    "peanut_butter": ["purée d'amande", "purée de noisette", "purée de cacahuète", "purée de cajou", "purée de sésame", "beurre de cacahuète", "tahin"],
    "eggs": ["oeufs", "œufs"],
    "dip": ["houmous", "tarama", "tzatziki", "guacamole", "ktipiti"],
    "tapenade": ["tapenade", "spécialité à la tomate", "caviar d'aubergine"],
    "fish_canned": ["thon", "sardines", "maquereau", "saumon conserve"],
    "butter": ["beurre"], "baguette": ["baguette", "pain de campagne"], "sandwich_bread": ["pain de mie"],
    "plain_yogurt": ["yaourt nature", "yaourt grec", "skyr"], "milk": ["lait demi-écrémé", "lait entier", "lait écrémé", "lait uht"],
    "cream_cheese": ["labneh", "carré frais", "fromage à tartiner", "cream cheese", "philadelphia", "boursin"],
    "cheese": ["emmental", "gruyère", "comté", "camembert", "mozzarella", "fromage râpé"],
    "hard_cheese": ["emmental", "comté", "gruyère", "parmesan", "cheddar", "gouda", "fromage râpé"],
    "blue_cheese": ["roquefort", "bleu d'auvergne", "fourme d'ambert", "gorgonzola"],
    "soft_ripened_cheese": ["camembert", "brie", "coulommiers", "reblochon", "munster"],
    "fresh_goat_cheese": ["chèvre", "crottin"],
    "mozzarella_fresh": ["mozzarella", "burrata", "ricotta", "feta"],
    "ham": ["jambon", "lardons"], "soup": ["soupe", "velouté"], "pizza": ["pizza"], "chips": ["chips"], "tea": ["thé", "infusion"],
    "mushrooms": ["champignons", "cèpes", "girolles", "morilles", "pleurotes", "chanterelles"],
    "pizza_dough": ["pâte à pizza"],
    "grilled_vegetables": ["légumes grillés", "poivrons grillés", "antipasti"],
    "vegetable_puree": ["purée de légumes"],
    "nuts": [],
}


def search_terms(p: Dict[str, Any]) -> List[str]:
    return TYPE_TERMS.get(classify(p).get("type") or "", [])
