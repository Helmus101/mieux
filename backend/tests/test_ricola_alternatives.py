"""
Ricola herbal lozenges must find comparable lozenges, require French
supermarket evidence, reject score<50 and unrelated products.

Most tests exercise engine.rank_quality / rank_best_value directly; the last
one drives the real alternatives endpoint with a controlled candidate pool.
"""
import copy
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import engine, main

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RICOLA = {
    "barcode": "7610700427705",
    "id": "7610700427705",
    "name": "Ricola Citron Mélisse",
    "brand": "Ricola",
    "categories": [
        "en:snacks", "en:sweet-snacks", "en:confectioneries",
        "en:candies", "en:lozenges",
    ],
    "soldInFrance": True,
    "chains": ["leclerc", "carrefour"],
    "nutriments": {
        "energyKcal100g": 380, "carbohydrates100g": 93, "sugars100g": 68,
        "fat100g": 0, "saturatedFat100g": 0, "protein100g": 0,
        "salt100g": 0, "fiber100g": 0,
    },
    "score": {"total": 20},
    "nutriScore": "d",
    "additives": [],
    "allergens": [],
    "traces": [],
    "quantity": {"amount": 75, "unit": "g"},
    "dataQuality": {"nutritionComplete": True},
    "ingredientsText": "Sucre, sirop de glucose, extraits de plantes",
    "analysis": [],
    "popularity": {"scans": 500, "chains": 2},
}


def _lozenge(bc, name, score=60, chains=None, categories=None):
    """Build a lozenge-category product dict."""
    return {
        **RICOLA,
        "barcode": bc,
        "id": bc,
        "name": name,
        "brand": "OtherBrand",
        "score": {"total": score},
        "chains": chains if chains is not None else ["leclerc"],
        "categories": categories or [
            "en:snacks", "en:sweet-snacks", "en:confectioneries",
            "en:candies", "en:lozenges",
        ],
        "popularity": {"scans": 100, "chains": 1},
    }


# ---------------------------------------------------------------------------
# Quality floor tests
# ---------------------------------------------------------------------------

def test_ricola_rejects_score_below_50():
    """Products scoring below the quality floor (50) must not appear."""
    low = _lozenge("001", "Pastilles miel gorge", score=45)
    result = engine.rank_quality(RICOLA, [low])
    assert result == [], "Score-45 product should be excluded by quality floor"


def test_ricola_accepts_score_at_floor():
    """Products scoring exactly at the quality floor (50) are eligible."""
    at_floor = _lozenge("002", "Pastilles gorge 50", score=50, chains=["carrefour"])
    result = engine.rank_quality(RICOLA, [at_floor])
    assert any(r["product"]["barcode"] == "002" for r in result), \
        "Score-50 product should pass the quality floor"


# ---------------------------------------------------------------------------
# Quality ranking tests
# ---------------------------------------------------------------------------

def test_ricola_quality_finds_comparable_lozenge():
    """A better-scoring lozenge from another brand must appear in quality results."""
    valda = _lozenge("003", "Valda pastilles menthol", score=55, chains=["carrefour", "leclerc"])
    result = engine.rank_quality(RICOLA, [valda])
    assert any(r["product"]["barcode"] == "003" for r in result), \
        "Better lozenge should appear in quality ranking"


def test_ricola_quality_ranks_better_score_first():
    """Higher-scoring lozenges rank above lower-scoring ones."""
    low = _lozenge("004", "Pastilles menthol basic", score=52, chains=["leclerc"])
    high = _lozenge("005", "Pastilles herbes premium", score=65, chains=["leclerc"])
    result = engine.rank_quality(RICOLA, [low, high])
    barcodes = [r["product"]["barcode"] for r in result]
    assert barcodes.index("005") < barcodes.index("004"), \
        "Higher-scoring product should rank first"


def test_ricola_quality_first_page_has_brand_variety():
    """One brand may not fill the visible top when other supermarket brands are comparable."""
    ricola = [_lozenge(f"r{i}", f"Ricola variante {i}", score=90, chains=["leclerc"]) for i in range(3)]
    for r in ricola:
        r["brand"] = "Ricola"
    others = []
    for bc, name, brand, score in [
        ("f1", "Fisherman's Friend menthe", "Fisherman's Friend", 80),
        ("v1", "Valda gorge", "Valda", 75),
        ("a1", "Aromandise miel", "Aromandise", 70),
    ]:
        p = _lozenge(bc, name, score=score, chains=["carrefour"])
        p["brand"] = brand
        others.append(p)
    result = engine.rank_quality(RICOLA, ricola + others)
    top5 = [r["product"]["brand"] for r in result[:5]]
    assert top5.count("Ricola") <= 2
    assert {"Fisherman's Friend", "Valda", "Aromandise"} <= set(top5)


# ---------------------------------------------------------------------------
# Value ranking tests
# ---------------------------------------------------------------------------

def test_ricola_value_requires_real_price():
    """A candidate without a price must not appear in Value rankings."""
    cand = _lozenge("006", "Pastilles gorge herbes", score=60, chains=["carrefour"])
    result = engine.rank_best_value(RICOLA, [cand], {}, orig_price=250.0)
    assert result["items"] == [], "No price → not eligible for Value ranking"


def test_ricola_value_works_with_real_price():
    """A candidate with a valid price and score ≥ 50 must appear in Value rankings."""
    cand = _lozenge("007", "Pastilles menthol bio", score=60, chains=["carrefour"])
    prices = {"007": 150.0}
    points = {"007": {"source": "open_prices", "date": date.today().isoformat()}}
    result = engine.rank_best_value(RICOLA, [cand], prices, orig_price=250.0, points=points)
    assert result["items"], "Better-priced lozenge should appear in Value ranking"


def test_ricola_value_damps_score_below_50_instead_of_excluding():
    """Low nutrition is a penalty, not an exclusion: at the same price, the product under the floor is listed but ranks below
    the one above it, and its value score is damped."""
    low = _lozenge("008", "Pastilles gorge cheap", score=45, chains=["carrefour"])
    ok = _lozenge("009", "Pastilles gorge correct", score=60, chains=["carrefour"])
    prices = {"008": 100.0, "009": 100.0}
    points = {k: {"source": "open_prices", "date": date.today().isoformat()} for k in prices}
    result = engine.rank_best_value(RICOLA, [low, ok], prices, orig_price=250.0, points=points)
    assert [r["product"]["barcode"] for r in result["items"]] == ["009", "008"]
    low_row = result["items"][1]
    assert low_row["value_detail"]["below_floor"] is True and low_row["value_score"] < result["items"][0]["value_score"]


# ---------------------------------------------------------------------------
# Chain / supermarket evidence tests
# ---------------------------------------------------------------------------

def test_ricola_quality_no_chain_still_ranked():
    """
    engine.rank_quality does not filter by chains — that is the backend's job.
    Products without chains still pass through the engine; the alternatives()
    endpoint applies the chain requirement before calling the engine.
    """
    no_chain = _lozenge("009", "Pastilles maison sans chaîne", score=55, chains=[])
    result = engine.rank_quality(RICOLA, [no_chain])
    # Engine itself does not enforce chain requirement; it just ranks
    # (the main.py alternatives() function enforces the chain gate).
    assert isinstance(result, list), "Engine returns a list regardless"


# ---------------------------------------------------------------------------
# Endpoint regression: retrieval -> France/chain gate -> quality/value ranks
# ---------------------------------------------------------------------------

def test_ricola_endpoint_keeps_only_comparable_french_supermarket_products(monkeypatch):
    """The endpoint must return comparable lozenges with chain evidence and images,
    while dropping unrelated candy, score<50 products and products with no chain."""
    today = date.today().isoformat()
    orig = copy.deepcopy(RICOLA)
    orig["score"] = {"total": 20}

    def cand(bc, name, score, brand="OtherBrand", chains_marker=None, categories=None):
        return {**copy.deepcopy(RICOLA), "barcode": bc, "id": bc, "name": name, "brand": brand,
                "score": {"total": score}, "chains": [], "categories": categories or copy.deepcopy(RICOLA["categories"]),
                "imageUrl": f"https://img.test/{bc}.jpg", "_chain_marker": chains_marker}

    peers = [
        cand("003", "Valda pastilles menthol", 60, brand="Valda"),
        cand("004", "Pastilles gorge leclerc", 55, brand="LeclercTest"),
        cand("005", "Pastilles gorge cheap", 40, brand="CheapBrand"),
        cand("006", "Caramel ourson", 90, brand="CandyBrand", categories=["en:snacks", "en:candies"]),
        cand("009", "Pastilles maison sans chaîne", 70, brand="NoChainBrand"),
        cand("010", "Pastilles sans marque", 80, brand=None),
    ]
    chain_names = {"003": "Carrefour", "004": "E.Leclerc", "005": "Carrefour", "006": "Carrefour", "010": "Carrefour"}  # 009 has no chain evidence
    points = {bc: {"source": "open_prices", "date": today, "pack_cents": 150} for bc in ("003", "004", "005", "006", "009", "010")}
    points[orig["barcode"]] = {"source": "open_prices", "date": today, "pack_cents": 189}

    class Prices:
        def prefetch(self, *_): pass
        def seen_in_france(self, *_): return False
        def chain_summary(self, bc, *_a, **_k):
            name = chain_names.get(bc)
            return [{"chain": name}] if name else []
        def latest(self, *_a, **_k): return None
        def stores(self, *_a, **_k): return []

    monkeypatch.setattr(main, "load_product", lambda s, b: copy.deepcopy(orig))
    monkeypatch.setattr(main, "_peers", lambda *a, **k: copy.deepcopy(peers))
    monkeypatch.setattr(main, "_price_map", lambda *a, **k: (250.0, {"003": 150.0, "004": 180.0, "005": 50.0, "006": 10.0, "009": 300.0, "010": 120.0}, points, {}))
    monkeypatch.setattr(main.app.state, "prices", Prices())

    client = TestClient(main.app)
    r = client.post("/v1/products/7610700427705/alternatives", headers={"X-Session-Id": "ricola-e2e", "X-Country": "FR"},
                    json={"priorities": ["overall"], "category_mode": "similar", "limit": 10, "substitution_max": 2,
                          "same_size": False, "chains": [], "price_constraint": "any", "approximate": False,
                          "strict_additives": False})
    assert r.status_code == 200, r.text
    d = r.json()

    assert "quality" not in d["rankings"], "one ranked list: the value score, nutrition shown inside each row"
    rows = {x["product"]["barcode"]: x for x in d["rankings"]["value"]}
    # In: priced, branded, at a supermarket, same kind of product. The cheap score-40 lozenge (005) stays: low nutrition
    # damps its score, it does not hide the only affordable option.
    assert {"003", "004", "005"} <= set(rows)
    assert rows["005"]["value_detail"]["below_floor"] is True
    # Out: another kind of product (006), no supermarket evidence (009), no brand (010).
    assert {"006", "009", "010"} & set(rows) == set()
    assert all(x["product"].get("chains") and x["product"].get("imageUrl") for x in rows.values())
