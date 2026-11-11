import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import main  # noqa: E402


def prod(code, score, brand="X", chains=(), unit="g", level=1, complete=True):
    return {"barcode": code, "id": code, "brand": brand, "quantity": {"amount": 180.0, "unit": unit}, "score": {"total": score},
            "dataQuality": {"nutritionComplete": complete}, "chains": list(chains), "substitution": {"level": level}, "popularity": {}}


ORIG = {"barcode": "0", "id": "0", "quantity": {"amount": 210.0, "unit": "g"}}


def test_the_best_unpriced_bars_are_searched_first_even_when_many_others_have_prices():
    priced = [prod(f"p{i}", 40) for i in range(15)]                    # plenty of observed prices elsewhere in the pool: the old rule skipped the search
    unpriced = [prod("g76", 76), prod("d71", 71), prod("c70", 70)] + [prod(f"u{i}", 30) for i in range(40)]
    prices = {c["barcode"]: 150.0 for c in priced}
    todo = main._search_targets(ORIG, False, priced + unpriced, prices)
    assert [c["barcode"] for c in todo[:3]] == ["g76", "d71", "c70"]
    assert all(c["barcode"] not in prices for c in todo)               # a priced product is never searched again
    assert len(todo) <= 30


def test_scanned_product_first_when_it_has_no_price_and_only_comparable_candidates_are_searched():
    cands = [prod("a", 80), prod("far", 90, level=3), prod("ml", 85, unit="ml"), prod("partial", 95, complete=False)]
    todo = main._search_targets(ORIG, True, cands, {})
    codes = [c["barcode"] for c in todo]
    assert codes[0] == "0"                                             # the scanned product first
    assert "far" not in codes and "ml" not in codes                    # not a close substitute / another unit
    assert codes.index("a") < codes.index("partial")                   # complete nutrition data comes before partial data
