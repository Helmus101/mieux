"""Reference dataset: unit normalisation, comparable / non-comparable pairs, and ticket formats. Synthetic but realistic."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from app import engine, receipts, value  # noqa: E402
from app.products import normalize  # noqa: E402

# ---------- units and price normalisation ----------
@pytest.mark.parametrize("text,expected", [
    ("500 g", (500.0, "g")), ("1 kg", (1000.0, "g")), ("1,5 kg", (1500.0, "g")), ("250ml", (250.0, "ml")), ("33 cl", (330.0, "ml")), ("1 l", (1000.0, "ml")),
    ("1.5 L", (1500.0, "ml")), ("6 x 125 g", (750.0, "g")), ("4x125g", (500.0, "g")), ("2 x 1 L", (2000.0, "ml")), ("12 x 33 cl", (3960.0, "ml")), ("un pot", None), ("", None),
])
def test_parse_quantity_table(text, expected):
    assert value.parse_quantity(text) == expected


@pytest.mark.parametrize("pack_cents,qty,per100", [(250, (500.0, "g"), 50.0), (200, (300.0, "g"), 66.7), (120, (1000.0, "ml"), 12.0), (249, (500.0, "g"), 49.8), (1, (100.0, "g"), 1.0)])
def test_price_per_100(pack_cents, qty, per100):
    assert round(value.per100(pack_cents, qty), 1) == per100


def test_larger_pack_can_cost_less_per_kg():
    assert value.per100(250, (500.0, "g")) < value.per100(200, (300.0, "g"))   # 2.50/500 g beats 2.00/300 g per kg


def test_old_observation_is_stale_not_fresh():
    from datetime import date, timedelta
    assert value.fresh((date.today() - timedelta(days=10)).isoformat()) and not value.fresh((date.today() - timedelta(days=400)).isoformat())
    assert value.age_days("not a date") is None


# ---------- comparable vs non-comparable pairs ----------
def prod(code, name, cats, protein=None, sugars=None, fibre=None, salt=0.1, kcal=100, ing="x", allergens=(), grade=None):
    nm = {"energy-kcal_100g": kcal, "fat_100g": 2, "saturated-fat_100g": 1, "carbohydrates_100g": max(8, (sugars or 0) + 1), "salt_100g": salt}   # sugars are part of the carbohydrates
    for k, v in (("proteins_100g", protein), ("sugars_100g", sugars), ("fiber_100g", fibre)):
        if v is not None: nm[k] = v
    return normalize({"code": code, "product_name": name, "brands": "B", "categories_tags": cats, "nutriments": nm, "ingredients_text": ing,
                      "allergens_tags": list(allergens), "ingredients_analysis_tags": [], "nutriscore_grade": grade, "quantity": "400 g", "countries_tags": ["en:france"]})


YOG = ["en:dairies", "en:fermented-foods", "en:yogurts"]
CER = ["en:breakfasts", "en:cereals-and-potatoes", "en:breakfast-cereals"]
BRD = ["en:cereals-and-potatoes", "en:breads"]
COMPARABLE = [  # (categories, original protein, candidate protein, original sugars, candidate sugars)
    (YOG, 4, 10, 12, 5), (YOG, 3, 9, 14, 6), (YOG, 5, 8, 11, 10), (CER, 7, 11, 22, 8), (CER, 6, 10, 25, 12), (CER, 8, 12, 18, 6), (BRD, 8, 11, 3, 2), (BRD, 7, 10, 4, 3),
] * 4  # 32 pairs


@pytest.mark.parametrize("cats,p0,p1,s0,s1", COMPARABLE)
def test_comparable_pairs_are_recommended_with_correct_deltas(cats, p0, p1, s0, s1):
    o, c = prod("1", "orig", cats, p0, s0), prod("2", "cand", cats, p1, s1)
    r = engine.choose(o, [c], ["protein"], [], None, "similar", 5, lang="en")
    assert [a["product_id"] for a in r["alternatives"]] == ["2"]
    assert r["alternatives"][0]["comparison"]["protein_difference_per_100g"] == round(p1 - p0, 2)


NON_COMPARABLE = [(YOG, CER), (CER, YOG), (YOG, BRD), (BRD, CER), (["en:beverages", "en:waters"], YOG)] * 4  # 20 pairs


@pytest.mark.parametrize("a,b", NON_COMPARABLE)
def test_non_comparable_pairs_are_never_recommended(a, b):
    o, c = prod("1", "orig", a, 3, 10), prod("2", "cand", b, 30, 1)          # the candidate is far better nutritionally
    assert engine.choose(o, [c], ["protein"], [], None, "similar", 5, lang="en")["alternatives"] == []


def test_missing_data_is_excluded_not_guessed():
    o = prod("1", "orig", YOG, 4, 12)
    no_protein = prod("2", "np", YOG, None, 5)
    assert engine.choose(o, [no_protein], ["protein"], [], None, "similar", 5, lang="en")["excluded"]["incomplete"] == 1


def test_unknown_allergen_data_is_unverified_and_declared_is_conflict():
    o = prod("1", "orig", YOG, 4, 12)
    nothing = prod("2", "n", YOG, 10, 5, ing=None)
    peanut = prod("3", "p", YOG, 10, 5, allergens=("peanuts",))
    r = engine.choose(o, [nothing, peanut], ["protein"], ["peanuts"], None, "similar", 5, lang="en")
    assert r["alternatives"] == [] and r["excluded"]["unverified"] == 1 and r["excluded"]["conflict"] == 1


# ---------- ticket formats ----------
TICKETS = {
    "carrefour": ("CARREFOUR MARKET\n28/10/2026 18:45\nYAOURT NATURE 1,59\nBANANES 2,10\nPAIN COMPLET 1,89\nTOTAL 5,58\nCB 5,58\nTVA 5,5% 0,28", 558, 3),
    "leclerc": ("E.LECLERC\n28.10.2026\nLAIT DEMI ECR 1L 1,05 €\nPATES TORSADES 1,20 €\nTOTAL A PAYER 2,25 €", 225, 2),
    "lidl": ("LIDL\n28/10/26\nBEURRE DOUX 250G 2.19\nOEUFS x6 2.35\nSOUS-TOTAL 4.54\nTOTAL 4.54 EUR", 454, 2),
    "monoprix": ("MONOPRIX PARIS 12\n28/10/26 18:45\nYAOURT GREC 1,59\nBANANES 2,10\nFLOCONS AVOINE 1,89\nOEUFS 3,20\nPOMMES 2,75\nTOTAL 11,53\nCB 11,53", 1153, 5),
    "franprix": ("FRANPRIX\n28/10/2026\nEAU 1,5L 0,89\nCHIPS 2,49\nNET A PAYER 3,38", 338, 2),
    "auchan_qty": ("AUCHAN\n28/10/2026\nYAOURT 4X125G 1,49\n2 x 1,29 PETITS POIS 2,58\nTOTAL 4,07", 407, 2),
    "intermarche_discount": ("INTERMARCHE\n28/10/2026\nCEREALES CHOCO 3,50\nREMISE FIDELITE -0,50\nTOTAL 3,00", 300, 1),  # one product + one discount line
    "casino": ("CASINO SHOPPING\n28/10/2026\nJAMBON BLANC 2,95\nBAGUETTE 1,10\nTOTAL TTC 4,05\nMONTANT CB 4,05", 405, 2),
    "aldi": ("ALDI\n28/10/2026\nFARINE 0,89\nSUCRE 1,19\nTOTAL 2,08", 208, 2),
    "grandfrais": ("GRAND FRAIS\n28/10/2026\nFROMAGE COMTE 6,90\nTOTAL 6,90", 690, 1),
    "picard": ("PICARD\n28/10/2026\nEPINARDS 2,59\nPIZZA 4,29\nTOTAL 6,88", 688, 2),
    "biocoop": ("BIOCOOP\n28/10/2026\nTOFU 2,75\nLAIT AVOINE 1,95\nTOTAL 4,70", 470, 2),
}


@pytest.mark.parametrize("name", list(TICKETS))
def test_ticket_formats_parse_to_the_printed_total(name):
    text, total, n = TICKETS[name]
    r = receipts.parse([{"text": t, "position": i} for i, t in enumerate(text.split("\n"))])
    assert r["total_cents"] == total, r
    assert r["purchase_date"] == "2026-10-28"
    assert len([i for i in r["items"] if not i["is_discount"]]) == n
    assert sum(i["line_total_cents"] for i in r["items"]) == total and not r["warnings"]


def test_unreadable_ticket_gives_warnings_not_invented_lines():
    r = receipts.parse([{"text": "~~ ## ??", "position": 0}, {"text": "abc", "position": 1}])
    assert r["items"] == [] and r["warnings"]


# ---------- deep algorithm ----------
def test_estimated_nova_is_flagged_and_sensible():
    from app.products import estimate_nova
    assert estimate_nova("lait entier", [], ["en:milks"]) == 1
    assert estimate_nova("huile d'olive", [], ["en:olive-oils"]) == 2
    assert estimate_nova("farine, eau, sel, levure", [], ["en:breads"]) == 3
    assert estimate_nova("sucre, arôme naturel, émulsifiant: lécithine", ["e322"], ["en:biscuits"]) == 4
    assert estimate_nova(None, [], []) is None
    assert normalize({"code": "1", "product_name": "x", "ingredients_text": "pommes", "nova_group": 3, "nutriments": {}})["novaEstimated"] is False


def test_deep_similarity_prefers_the_same_kind_of_product():
    a = prod("1", "Yaourt grec nature", YOG, 9, 4, kcal=110)
    same = prod("2", "Yaourt grec nature bio", YOG, 8, 4, kcal=105)
    other_kind = prod("3", "Boisson protéinée vanille", ["en:beverages", "en:protein-drinks"], 8, 4, kcal=60)
    cereal = prod("4", "Muesli croustillant", CER, 9, 4, kcal=380)
    s_same, s_other, s_cereal = engine.deep_similarity(a, same), engine.deep_similarity(a, other_kind), engine.deep_similarity(a, cereal)
    assert s_same > 0.7 and s_same > s_other and s_same > s_cereal and s_cereal < 0.45


def test_pack_size_variants_collapse_into_one_recommendation():
    # A plain yogurt: a fruit yogurt is a different kind of product, not another pack size of this one.
    o = prod("1", "Yaourt nature", YOG, 4, 12)
    big, small = prod("2", "Skyr nature", YOG, 10, 5), prod("3", "Skyr nature", YOG, 10, 5)
    big["quantity"] = {"amount": 1000.0, "unit": "g"}
    r = engine.choose(o, [small, big], ["protein"], [], None, "similar", 5, lang="en")
    assert len(r["alternatives"]) == 1 and r["alternatives"][0]["other_sizes"] == 1


def test_dominated_products_are_flagged_not_hidden():
    a, b, c = {"p": 3, "q": 3}, {"p": 2, "q": 2}, {"p": 4, "q": 1}
    keys = [lambda x: x["p"], lambda x: x["q"]]
    assert engine.dominated([a, b, c], keys) == [False, True, False]      # b is beaten by a on both; c trades q for p
    assert engine.dominated([{"p": None, "q": 1}, {"p": 1, "q": 1}], keys) == [False, False]   # a missing value is not compared: it never makes an item look dominated


# ---------- availability in France ----------
def test_sold_in_france_flag_true_false_unknown():
    base = {"code": "1", "product_name": "x", "nutriments": {}}
    assert normalize({**base, "code": "3250391887439", "countries_tags": ["en:france"]})["soldInFrance"] is True
    n = normalize({**base, "code": "8019428007579", "countries_tags": ["en:france"]})
    assert n["soldInFrance"] is True and n["frEvidence"] == "off_tag"   # foreign barcode: accepted on the tag, but flagged as to be confirmed
    assert normalize({**base, "code": "3250391887439", "countries_tags": ["en:france"]})["frEvidence"] == "gs1_fr"
    assert normalize({**base, "code": "3250391887439", "countries_tags": ["en:france", "en:belgium"]})["soldInFrance"] is True   # French GS1 prefix
    assert normalize({**base, "code": "8003180000145", "countries_tags": ["en:france", "en:italy"]})["frEvidence"] == "off_tag"  # Italian product also tagged France: weak evidence
    assert normalize({**base, "countries_tags": ["en:norway"]})["soldInFrance"] is False
    assert normalize(base)["soldInFrance"] is None                       # no data: availability is not assumed


def test_only_products_sold_in_france_are_recommended():
    o = prod("1", "orig", YOG, 4, 12)
    fr, abroad, unknown = prod("2", "fr", YOG, 10, 5), prod("3", "abroad", YOG, 11, 4), prod("4", "unk", YOG, 12, 3)
    abroad["soldInFrance"], unknown["soldInFrance"] = False, None
    r = engine.choose(o, [fr, abroad, unknown], ["protein"], [], None, "similar", 5, lang="en")
    assert [a["product_id"] for a in r["alternatives"]] == ["2"] and r["excluded"]["not_in_france"] == 2


def test_prices_seen_abroad_are_ignored():
    from datetime import date
    today = date.today().isoformat()
    c = value.OpenPricesClient("/nonexistent/op_local.db")
    item = lambda country, price: {"price": price, "currency": "EUR", "price_per": None, "date": today, "location": {"osm_address_country_code": country}}  # noqa: E731
    c._raw["123"] = (__import__("time").time(), [item("NO", 1.0), item("FR", 2.0)])
    got = c.latest("123", (400.0, "g"))
    assert got and got["per100_cents"] == 50.0                            # the French 2.00 EUR/400 g, not the Norwegian one
    c._raw["456"] = (__import__("time").time(), [item("NO", 1.0), item("DE", 1.5)])
    assert c.latest("456", (400.0, "g")) is None


def test_price_confidence_levels():
    from datetime import date
    from app import value
    t = date(2026, 11, 6)
    assert value.price_confidence(None) is None
    assert value.price_confidence({"source": "estimate", "date": None}, t) == "estimate"
    assert value.price_confidence({"source": "your_receipt", "date": "2026-10-20"}, t) == "high"
    assert value.price_confidence({"source": "open_prices", "date": "2026-10-20"}, t) == "medium"
    assert value.price_confidence({"source": "open_prices", "date": "2026-01-01"}, t) == "low"
    assert value.price_confidence({"source": "open_prices", "date": "2026-10-20", "stale": True}, t) == "low"


def test_sugar_and_salt_limits_follow_the_kind_of_product():
    from app import engine
    soda = {"name": "Cola", "categories": ["en:beverages", "en:sodas"]}
    fruit = {"name": "Dattes", "categories": ["en:fruits", "en:dried-fruits"]}
    cereal = {"name": "Corn flakes", "categories": ["en:breakfast-cereals"]}
    assert engine.nutrient_limits(soda)[0] == 2.5
    assert engine.nutrient_limits(cereal) == (4.0, 0.4)
    assert engine.nutrient_limits({"name": "Inconnu", "categories": []}) == (5.0, 0.5)


def test_variants_are_disclosed_not_disqualifying():
    from app import taxonomy
    plain = {"name": "Yaourt nature", "categories": ["en:yogurts", "en:plain-yogurts"]}
    greek = {"name": "Yaourt grec nature", "categories": ["en:yogurts", "en:greek-yogurts"]}
    sub = taxonomy.substitution(plain, greek)
    assert sub is not None and sub["variant_diff"] == ["standard", "greek"]
    assert taxonomy.substitution(plain, plain)["variant_diff"] is None
