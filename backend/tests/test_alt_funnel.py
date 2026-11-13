"""The alternatives funnel, in order: market -> supermarket -> price -> same small category -> rank.

These tests drive the real endpoint with a controlled candidate pool and check two things:
  1. each hard filter removes exactly the products it should, and the diagnostics report the count at every stage;
  2. the ranking is computed over the whole eligible pool (100 rows of depth), not the first few rows.
"""
import copy
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import main

ORIG = {
    "barcode": "7610700427705",
    "id": "7610700427705",
    "name": "Ricola Citron Mélisse",
    "brand": "Ricola",
    "categories": ["en:snacks", "en:sweet-snacks", "en:confectioneries", "en:candies", "en:lozenges"],
    "soldInFrance": True,
    "chains": ["carrefour"],
    "nutriments": {"energyKcal100g": 380, "carbohydrates100g": 93, "sugars100g": 68, "fat100g": 0,
                   "saturatedFat100g": 0, "protein100g": 0, "salt100g": 0, "fiber100g": 0},
    "score": {"total": 20},
    "nutriScore": "d",
    "additives": [],
    "allergens": [],
    "traces": [],
    "quantity": {"amount": 75, "unit": "g"},
    "dataQuality": {"nutritionComplete": True},
    "ingredientsText": "Sucre, sirop de glucose, extraits de plantes",
    "analysis": [],
    "popularity": {"scans": 500, "chains": 1},
}


def _lozenge(bc, name, score=70, sold=True, chains=("carrefour",), category=None):
    return {**copy.deepcopy(ORIG), "barcode": bc, "id": bc, "name": name, "brand": "Brand" + bc,
            "score": {"total": score}, "soldInFrance": sold, "chains": list(chains),
            "categories": category or copy.deepcopy(ORIG["categories"])}


class _Prices:
    def prefetch(self, *_a, **_k):
        pass

    def seen_in_france(self, *_a, **_k):
        return False

    def chain_summary(self, bc, *_a, **_k):
        return [{"chain": "Carrefour"}] if bc != "no_chain" else []

    def latest(self, *_a, **_k):
        return None

    def stores(self, *_a, **_k):
        return []


def _run(monkeypatch, peers, prices, orig_price=300.0, **body):
    monkeypatch.setattr(main, "load_product", lambda s, b: copy.deepcopy(ORIG))
    monkeypatch.setattr(main, "_peers", lambda *a, **k: copy.deepcopy(peers))
    monkeypatch.setattr(main, "_price_map", lambda *a, **k: (
        orig_price, dict(prices), {bc: {"source": "open_prices", "date": date.today().isoformat()} for bc in prices}, {}))
    monkeypatch.setattr(main.app.state, "prices", _Prices())
    client = TestClient(main.app)
    payload = {"priorities": ["overall"], "category_mode": "similar", "limit": 10, "substitution_max": 2,
               "same_size": False, "chains": [], "price_constraint": "any", "approximate": False,
               "strict_additives": False, **body}
    r = client.post("/v1/products/7610700427705/alternatives",
                    headers={"X-Session-Id": "funnel-test", "X-Country": "FR"}, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _codes(res):
    out = set()
    for key in ("value", "quality"):
        out |= {x["product"]["barcode"] for x in res["rankings"].get(key, [])}
    out |= {a["product"]["barcode"] for a in res["alternatives"]}
    return out


def test_each_filter_removes_its_products_and_is_reported(monkeypatch):
    peers = [
        _lozenge("ok", "Pastille gorge citron"),           # passes all four filters
        _lozenge("abroad", "Pastille gorge menthol", sold=False),       # not sold in this market
        _lozenge("unknown", "Pastille gorge eucalyptus", sold=None),    # availability unknown
        _lozenge("no_chain", "Pastille gorge miel", chains=()),         # no supermarket evidence
        _lozenge("no_price", "Pastille gorge thym"),                    # no real price
        _lozenge("wrong_type", "Caramel ourson", category=["en:snacks", "en:candies"]),  # not the same kind of product
    ]
    res = _run(monkeypatch, peers, prices={"ok": 150.0, "abroad": 150.0, "unknown": 150.0,
                                           "no_chain": 150.0, "wrong_type": 150.0})

    d = res["diagnostics"]
    assert d["retrieved"] == 6
    assert d["sold_in_market"] == 4          # abroad + unknown are gone
    assert d["at_supermarket"] == 3          # no_chain is gone
    assert d["with_price"] == 2              # no_price is gone
    assert d["comparable"] == 1              # wrong_type is gone

    assert _codes(res) == {"ok"} or _codes(res) == set()   # "ok" may still fail the quality floor, never the others
    assert not ({"abroad", "unknown", "no_chain", "no_price", "wrong_type"} & _codes(res))


def test_every_shown_row_has_a_supermarket_and_a_price(monkeypatch):
    peers = [_lozenge("a", "Pastille gorge citron"), _lozenge("b", "Pastille gorge menthe")]
    res = _run(monkeypatch, peers, prices={"a": 150.0, "b": 200.0})
    rows = [x for k in ("value", "quality") for x in res["rankings"].get(k, [])] + res["alternatives"]
    for row in rows:
        assert row["product"]["chains"], "a displayed alternative needs real supermarket evidence"
        assert row["price_per_100_cents"] is not None, "a displayed alternative needs a real price"


def test_ranking_is_deep_but_display_is_short(monkeypatch):
    peers = [_lozenge(f"c{i:03d}", f"Pastille gorge citron {i:03d}") for i in range(120)]
    prices = {p["barcode"]: 100.0 + i for i, p in enumerate(peers)}
    res = _run(monkeypatch, peers, prices=prices)

    value = res["rankings"]["value"]
    assert "quality" not in res["rankings"], "one recommendation score: no competing quality list"
    assert len(value) == 100, "the API keeps a full ranked list (100 rows) so filters still have rows"
    assert len(res["alternatives"]) <= 10, "cards stay short: 3 shown, expandable to 10"
    assert res["rankings"]["profile"] == "budget"

    scores = [row["value_score"] for row in value]
    assert all(s is not None for s in scores)
    assert scores == sorted(scores, reverse=True), "the value score alone decides the order"
    for row in value:   # the three measurements travel with the score, so the shopper can see the trade-off
        assert row["quality_score"] is not None and row["affordability_score"] is not None and row["confidence"] in ("high", "medium", "low")
