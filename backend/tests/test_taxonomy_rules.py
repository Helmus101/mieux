"""The Mieux taxonomy rule layer: every rule must resolve to a real node, and known products must land where a shopper expects."""
import pytest

from app import taxo1000, taxorules


def test_every_rule_resolves_and_nothing_matches_everything():
    L = taxorules.load()
    assert L["unresolved"] == []
    for tid, nre, tre, veto, i in L["rules"]:
        for r in (nre, tre):
            if r is not None:
                assert not r.search("zzzz qqqq"), f"rule {i + 1} ({L['nodes'][tid]['name_fr']}) matches anything"


@pytest.mark.parametrize("name,tags,expected", [
    ("Biscuits fourrés au chocolat", [], "Biscuits fourrés au chocolat"),
    ("Cassoulet au confit de canard", [], "Cassoulet en conserve"),
    ("Chocolat noir 70 %", [], "Chocolat noir 70 % cacao"),
    ("Coca-Cola Zero 1,5 L", [], "Cola sans sucre"),
    ("Jambon blanc découenné", [], "Jambon blanc découenné dégraissé"),
    ("Emmental râpé", [], "Emmental râpé"),
    ("Huile d'olive vierge extra", [], "Huile d’olive vierge extra"),
    ("Sirop de noisette", [], "Sirop non précisé"),        # a syrup is not a nut
    ("Alpro Cashew Drink", [], "Boisson végétale non précisée"),
    ("Terrine de sanglier au cognac", [], "Pâté et terrine de volaille ou gibier"),   # not a spirit
    ("Bière blonde 33 cl", [], "Bière blonde"),
    ("Saumon fumé", [], "Saumon fumé"),
])
def test_known_placements(name, tags, expected):
    m = taxorules.match(name, None, tags)
    got = taxorules.load()["nodes"][m["type"]]["name_fr"] if m and m["type"] else None
    if expected is None:
        assert got is None
    else:
        assert got == expected


def test_broad_placement_when_only_a_tag_is_known():
    r = taxo1000.classify("Zzz inconnu", None, None, ["en:meats"])
    assert r["level"] == 2 and r["type"] is None and r["category"].endswith("SAUCISSES_PREPAREES")


def test_unknown_product_is_unclassified_not_forced():
    r = taxo1000.classify("Qwerty Zxcv", None, None, [])
    assert r["level"] == 0 and r["type"] is None


def _golden():
    import json, os
    return json.load(open(os.path.join(os.path.dirname(__file__), "data", "taxonomy_golden.json"), encoding="utf-8"))


def test_golden_products_land_in_their_type():
    """Realistic product names (brands, plurals, sizes) across every department must land in the expected type."""
    L = taxorules.load()
    misses = []
    for name, expected in _golden():
        m = taxorules.match(name)
        got = L["nodes"][m["type"]]["name_fr"] if m and m["type"] else (L["nodes"][m["category"]]["name_fr"] + " (cat)" if m and m["category"] else None)
        if got != expected:
            misses.append(f"{name!r}: expected {expected!r}, got {got!r}")
    assert not misses, "\n".join(misses)
