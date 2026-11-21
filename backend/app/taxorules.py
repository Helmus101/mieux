"""Rule layer of the Mieux taxonomy classifier (app/data/taxo_rules.txt).

Each rule: TARGET <TAB> NAME_REGEX <TAB> TAG_REGEX [<TAB> NAME_VETO]. TARGET is a product-type name (level 3), "C:<category suffix>"
(level 2, a broad placement) or "D:<NN>" (level 1). Rules are ordered from specific to general; of all rules that hit (on the
name or on the OFF category tags) the earliest wins, so the file order *is* the specificity order. Everything is deterministic."""
import html
import json
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

_BLOCK = 24
_DIR = os.path.dirname(os.path.abspath(__file__))
_TAXO = os.path.join(_DIR, "mieux_taxonomy.json")
_RULES = os.path.join(_DIR, "data", "taxo_rules.txt")


def norm(s: Optional[str]) -> str:
    s = html.unescape(s or "").lower().replace("œ", "oe").replace("æ", "ae").replace("’", " ").replace("'", " ")
    # "pâté" (a spread) and "pâte" (pasta, dough) must stay different words once accents are stripped: pâté -> "patee".
    s = re.sub(r"\bp[aâ]t[ée]s?\b(?<=é)|\bp[aâ]t(?:é|ée)s?\b", lambda m: "patee" + ("s" if m.group(0).endswith("s") else ""), s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9%]+", " ", s).strip()


def tag_text(tags: Optional[Sequence[str]]) -> str:
    return "|".join(re.sub(r"^[a-z]{2}:", "", t).replace("-", " ") for t in (tags or []))


@lru_cache(maxsize=1)
def load() -> Dict[str, Any]:
    d = json.load(open(_TAXO, encoding="utf-8"))
    nodes = {n["id"]: n for n in d["nodes"]}
    by_name: Dict[str, str] = {}
    for n in d["nodes"]:
        if n["level"] == 3:
            by_name.setdefault(norm(n["name_fr"]), n["id"])
    rules: List[Tuple[str, Any, Any, Any, int]] = []
    unresolved: List[str] = []
    for i, line in enumerate(open(_RULES, encoding="utf-8").read().split("\n")):
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 3:
            continue
        t = f[0]
        if t.startswith("C:"):
            tid = "C_" + t[2:]
        elif t.startswith("D:"):
            tid = next((k for k in nodes if k.startswith("D_" + t[2:] + "_")), None)
        else:
            tid = by_name.get(norm(t))
        if not tid or tid not in nodes:
            unresolved.append(t)
            continue
        # A pattern may never start or end inside a word: "cola" must not fire on "chocolate".
        c = lambda x: None if x in ("", "-") else re.compile(r"(?<![a-z0-9])(?:" + x + r")(?![a-z0-9])", re.I)  # noqa: E731
        ct = lambda x: None if x in ("", "-") else re.compile(r"(?:^|\|)(?:" + x + r")(?:\||$)", re.I)  # noqa: E731  (a tag pattern must match a WHOLE tag)
        rules.append((tid, c(f[1]), ct(f[2]), c(f[3]) if len(f) > 3 else None, i))
    # Prefilter: one combined regex per block of consecutive rules. A block whose combined pattern finds nothing is skipped
    # in a single C call, so the per-rule Python loop only runs for the few blocks that can actually match.
    chunks = []
    for a in range(0, len(rules), _BLOCK):
        blk = rules[a:a + _BLOCK]
        nps = [r[1].pattern for r in blk if r[1] is not None]
        tps = [r[2].pattern for r in blk if r[2] is not None]
        chunks.append((a, a + len(blk), re.compile("|".join(f"(?:{x})" for x in nps), re.I) if nps else None,
                       re.compile("|".join(f"(?:{x})" for x in tps), re.I) if tps else None))
    return {"nodes": nodes, "rules": rules, "unresolved": unresolved, "chunks": chunks}


# A name that starts with a dish word is that dish, not the ingredient it mentions ("Pizza 4 fromages", "Tarte au chèvre").
# Only departments that really sell dishes (prepared meals, bakery, soups, frozen) may claim such a name.
_DISH_START = re.compile(r"^(pizzas?|quiches?|sandwich(es)?|burgers?|salades?|gratins?|tartes?|lasagn?es?|raviolis?|croques?|wraps?|paninis?|soupes?|veloutes?|tourtes?|feuilletes?|gnocchis?|nuggets?|cordons? bleus?|hachis|plats?|assiette|bol|bowl|tacos?|kebab|sushis?|makis?|nems?|samoussas?|boulettes?|brochettes?|croquettes?|galettes? (garnie|complete)|crepes? (jambon|fromage|garnie)|poelee|risotto|paella|couscous|tajine|curry|chili|pasta|spaghettis? (a la|bolognaise|carbonara))\b")
_DISH_DEPTS = {"D_26_NON_ALIMENTAIRE_ET_HORS_PERIMETRE", "D_18_PLATS_PREPARES", "D_16_BISCUITS_GATEAUX_DESSERTS", "D_22_SURGELES", "D_06_BOULANGERIE_PAINS", "D_19_SOUPES_CONSERVES", "D_24_ALIMENTS_MONDE", "D_08_PATES_RIZ_CEREALES", "D_05_ALTERNATIVES_VEGETALES", "D_02_VIANDES_VOLAILLES", "D_03_POISSONS_FRUITS_MER", "D_01_FRUITS_LEGUMES"}


# Alcohol and chocolate words inside a food name ("Terrine de sanglier au cognac", "Céréales fourrées chocolat") describe a flavour, not the product.
_NOT_ALCOHOL = re.compile(r"\b(terrines?|pates?|patees?|sauces?|gateaux?|chocolats?|biscuits?|saucissons?|foie gras|confitures?|moutardes?|bonbons?|glaces?|cakes?|truffes?|cremes?|jambons?|fromages?|vinaigres?|vinaigrettes?|marinades?|moules?|gelees?|aromes?|arome|saveur|parfum|cuisine|cuisson|filet|epices?|brioches?|yaourts?|dessert|tartes?|poulet|boeuf|porc|lapin|canard|veau|sorbets?|barres?|cafe|the|infusion|lait|creme|boisson|jus|sirop|nougat|pralines?|madeleines?|baba|savarin|bouchees?|pain|crepes?|chips|lentilles?|poires?|pommes?|venison|slow cooked|braised|stew|roast|soup|dressing|cooked|marinated)\b")
_ALCOHOL_FOODWORD_OK = {"D_25_BOISSONS_ALCOOLISEES"}
_CV = re.compile(r"\b(cereales?|biscuits?|cookies?|cremes?|desserts?|glaces?|gateaux?|cakes?|brioches?|gaufres?|crepes?|muesli|granola|barres?|batonnets?|bonbons?|muffins?|pains?|galettes?|mousses?|boissons?|yaourts?|fromages?|coulants?|fondants?|sticks?|moelleux|tartiner|petit pot|nappes?|enrobes?|cafe|the|pate|sauces?|chantilly|ice cream|dragees?|noisettes? chocolat|tuiles?|crepe|petit dejeuner|lait chocolat|lait au chocolat|cacao pret|spread|pudding|riz|quinoa|ble|mais|fourres?|fourrees?|flocons?|choco ?balls?|pops?|wafers?|gaufrettes?|tablette biscuit)\b")
_CHOC_TYPES = ("Tablette chocolat noir", "Tablette chocolat au lait", "Tablette chocolat blanc", "Chocolat noir 70 % cacao", "Chocolat noir 85 % cacao", "Chocolat noir aux fruits ou éclats", "Chocolat au lait aux noisettes", "Tablette de chocolat aux noix", "Chocolat fourré", "Chocolat praliné", "Chocolat au lait fourré", "Chocolat non précisé", "Pépites de chocolat", "Chocolat de couverture")


# Ingredient categories (a plain nut, spice, fruit, vegetable, grain or pulse): a name that also carries a product-form word
# ("Sirop de noisette", "Cashew Drink", "Chocolate Almond", "Pâtes aux épinards") is a processed product, not the raw ingredient.
_INGREDIENT_CATS = ("FRUITS_FRAIS", "LEGUMES_FRAIS", "FRUITS_EXOTIQUES", "CHAMPIGNONS_SALADES", "POMMES_DE_TERRE", "LEGUMES_RACINES_CHOUX", "NOIX_GRAINES_NOIX_GRAINES", "NOIX_GRAINES_FRUITS_SECS",
                    "EPICES_HERBES_EPICES", "EPICES_HERBES_HERBES", "LEGUMINEUSES_SECHES", "CEREALES_GRAINES", "FRUITS_COQUE_TRANSFORMES")
_FORM = re.compile(r"\b(sirops?|boissons?|drinks?|milks?|laits?|chocolats?|chocolate|choc|biscuits?|cookies?|gateaux|gateau|cakes?|cremes?|glaces?|ice cream|barres?|bars?|yaourts?|yogurts?|huiles?|oil|olio|aceite|beurres?|butter|puree|pates?|tartiner|spread|sauces?|soupes?|jus|juice|confitures?|jam|compotes?|nectar|cafe|thes?|tea|infusion|liqueur|vins?|bieres?|alcool|vodka|rhum|pains?|bread|brioches?|muesli|granola|cereales?|crackers?|chips|flocons?|farines?|flour|salades?|gratins?|tartes?|plats?|nems?|sorbets?|desserts?|mousses?|flans?|nougat|pralines?|marzipan|massepain|krem|krounchy|gouts?|saveurs?|parfums?|aromes?|arome|flavou?r|flavou?red|aromatis\w*|savon|shampoo\w*|cosmetic\w*|eclats?|enrobe\w*|nappe\w*|fourre\w*|petales?|bonbons?|sucettes?|dragees?|vinaigres?|moutardes?|nouilles?|pates?|pasta|tisane|capsules?|gelules?)\b")


# A meat, fish or cheese word inside a dish name ("Minis samossas au bœuf", "Pizza au chèvre") does not make the dish a raw cut.
_DISH_ANY = re.compile(r"\b(samoussas?|samossas?|nems?|pizzas?|quiches?|tartes?|tourtes?|lasagn?es?|raviolis?|burgers?|sandwich(?:es)?|wraps?|empanadas?|bouchees?|feuilletes?|beignets?|croquettes?|cannelloni|gratins?|hachis|couscous|paella|curry|tajine|chili|farcis?|farcies?|farcie|brioches?|cakes?|friands?|pains?|boulettes?|nuggets?|panini|croque|calzone|crepes?|galettes?|bowl|salades?|soupes?|veloutes?|risotto|pates? (?:au|aux)|gnocchis?|ravioles?|tacos?|burritos?|kebab|sushis?|makis?)\b")
_RAW_DEPT_OK_CATS = ("SAUCISSES_PREPAREES", "CHARCUTERIE", "FOIE_GRAS")


# "Filets de maquereaux sauce tomate", "Haricots à la sauce tomate": the sauce is a component of a food named first, not the product.
_SAUCE_CATS = ("SAUCES_FROIDES", "SAUCES_CUISINE", "SAUCES_ASIATIQUES")
_SAUCE_COMPONENT = re.compile(r"^(?:filets?|haricots?|poissons?|saucisses?|boulettes?|ravioli|pates|legumes|viande|poulet|boeuf|thon|sardines?|maquereaux?|oeufs?|lentilles?|pois|riz|quenelles?|cassoulet|tripes?|boudin|escargots?|moules?|crevettes?|travers|ribs|nouilles|spaghetti|pizza|burger|sandwich)\b")


def _chain(nid: str, nodes: Dict[str, Any]) -> Dict[str, Optional[str]]:
    n = nodes[nid]
    lvl = n["level"]
    cat = nid if lvl == 2 else (n["parent_id"] if lvl == 3 else None)
    dep = nid if lvl == 1 else (nodes[cat]["parent_id"] if cat else None)
    return {"type": nid if lvl == 3 else None, "category": cat, "department": dep, "level": lvl}


def match(name: Optional[str], generic_name: Optional[str] = None, tags: Optional[Sequence[str]] = None) -> Optional[Dict[str, Any]]:
    """Earliest rule that hits on the name or on the tags. None when no rule hits."""
    L = load()
    nt = norm(" ".join(x for x in (name, generic_name) if x))
    tt = tag_text(tags)
    rules = L["rules"]
    todo: List[int] = []
    for a_, b_, cn, ct_ in L["chunks"]:
        if (cn is not None and nt and cn.search(nt)) or (ct_ is not None and tt and ct_.search(tt)):
            todo.extend(range(a_, b_))
    dish = bool(nt) and bool(_DISH_START.search(nt))
    best_name = None   # (start position, rule order) - the product's head noun is the first one named, so the earliest hit wins
    best_tag = None
    best_spec = None   # best hit among the non-catch-all rules
    for k in todo:
        tid, nre, tre, veto, i = rules[k]
        ch = None
        if dish:
            ch = _chain(tid, L["nodes"])
            if ch["department"] not in _DISH_DEPTS:
                continue
        hit = nre.search(nt) if (nre is not None and nt) else None
        if hit and not (veto and veto.search(nt)):
            ch = ch or _chain(tid, L["nodes"])
            if ch["department"] == "D_25_BOISSONS_ALCOOLISEES" and (ch["category"] != "C_25_BOISSONS_ALCOOLISEES_BIERES" or hit.start() > 0) and _NOT_ALCOHOL.search(nt):
                hit = None
            elif L["nodes"][tid]["name_fr"] in _CHOC_TYPES and _CV.search(nt):
                hit = None
            elif ch["category"] and ch["category"].endswith(_INGREDIENT_CATS) and _FORM.search(nt):
                hit = None
            elif (ch["category"] or "").endswith(_SAUCE_CATS) and hit.start() > 0 and _SAUCE_COMPONENT.search(nt):
                hit = None
            elif ch["department"] in ("D_02_VIANDES_VOLAILLES", "D_03_POISSONS_FRUITS_MER") and not (ch["category"] or "").endswith(_RAW_DEPT_OK_CATS) and _DISH_ANY.search(nt):
                hit = None
            if hit:
                key = (hit.start(), 0, i)
                if best_name is None or key < best_name[0]:
                    best_name = (key, tid)
                if "non précis" not in L["nodes"][tid]["name_fr"] and (best_spec is None or key < best_spec[0]):
                    best_spec = (key, tid)
        if best_tag is None and tre is not None and tt and tre.search(tt):
            ch = ch or _chain(tid, L["nodes"])
            # a tag says "oranges" but the name says "Boisson orange": the form word in the name wins over an ingredient tag
            if ch["department"] == "D_25_BOISSONS_ALCOOLISEES" and ch["category"] != "C_25_BOISSONS_ALCOOLISEES_BIERES" and _NOT_ALCOHOL.search(nt):
                continue   # "venison with red wine sauce" is a dish, whatever its tags say
            if not (ch["category"] and ch["category"].endswith(_INGREDIENT_CATS) and _FORM.search(nt)) \
                    and not (ch["department"] in ("D_02_VIANDES_VOLAILLES", "D_03_POISSONS_FRUITS_MER") and not (ch["category"] or "").endswith(_RAW_DEPT_OK_CATS) and _DISH_ANY.search(nt)):
                best_tag = (i, tid)
    if best_name and best_spec and "non précis" in L["nodes"][best_name[1]]["name_fr"]:
        best_name = best_spec     # "Pâtes torsades": the specific word beats the catch-all "pâtes"
    pick = None
    if best_name and best_tag and "non précis" in L["nodes"][best_tag[1]]["name_fr"] and "non précis" not in L["nodes"][best_name[1]]["name_fr"]:
        best_tag = None    # a catch-all tag ("shellfish") never beats a specific name ("anneaux d'encornet")
    if best_name and (best_name[0][0] == 0 or not best_tag):
        pick = (best_name[1], "name", best_name[0][2])
    elif best_tag:
        if best_name and L["nodes"][best_tag[1]]["level"] < 3 and L["nodes"][best_name[1]]["level"] == 3:
            pick = (best_name[1], "name", best_name[0][2])   # a broad tag never overrides a specific name
        else:
            pick = (best_tag[1], "tag", best_tag[0])
    elif best_name:
        pick = (best_name[1], "name", best_name[0][2])
    if pick:
        return {**_chain(pick[0], L["nodes"]), "source": pick[1], "rule": pick[2] + 1}
    return None
