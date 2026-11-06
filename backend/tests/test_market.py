import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app import chains, main, market, retail  # noqa: E402
from app.products import normalize  # noqa: E402

c = TestClient(main.app)


class Fake:
    def __init__(self, name):
        self.name = name

    def search_name(self, q):
        return [{"code": "1", "product_name": f"{self.name} {q}", "categories_tags": []}]


def test_the_header_picks_the_market_and_unknown_values_fall_back_to_france(monkeypatch):
    monkeypatch.setattr(main.app.state, "off", market.PerMarket({"FR": Fake("fr"), "US": Fake("us")}))
    h = {"X-Session-Id": "market-test-1"}
    name = lambda hdr: c.get("/v1/search", params={"q": "x"}, headers={**h, **hdr}).json()["products"][0]["name"]  # noqa: E731
    assert name({"X-Country": "US"}).startswith("us")
    assert name({"X-Country": "us"}).startswith("us")
    assert name({"X-Country": "FR"}).startswith("fr")
    assert name({}).startswith("fr")
    assert name({"X-Country": "ZZ"}).startswith("fr")


def test_sold_here_follows_the_market():
    raw = {"code": "0070847811169", "product_name": "Monster", "countries_tags": ["en:united-states"], "categories_tags": ["en:beverages"], "nutriments": {}}
    market.set_current("US")
    try:
        assert normalize(raw)["soldInFrance"] is True      # sold in the shopper's market
        assert normalize({**raw, "countries_tags": ["en:france"]})["soldInFrance"] is False
    finally:
        market.set_current("FR")
    assert normalize(raw)["soldInFrance"] is False


def test_us_chains_are_recognised_and_own_brands_point_to_their_chain():
    assert chains.canon("Trader Joe's #123") == "Trader Joe's"
    assert chains.canon("Walmart Supercenter") == "Walmart"
    assert chains.own_brand_chain("Kirkland Signature") == "Costco"
    assert chains.own_brand_chain("Great Value") == "Walmart"
    assert chains.own_brand_chain("Good & Gather") == "Target"
    assert chains.canon("Carrefour Market") == "Carrefour"


def test_each_market_only_sees_its_own_chains():
    assert retail.in_market("traderjoes", "US") and not retail.in_market("traderjoes", "FR")
    assert retail.in_market("carrefour", "FR") and not retail.in_market("carrefour", "US")
    assert retail.in_market("aldi", "FR") and retail.in_market("aldi", "US")   # trades in both
    assert set(retail.US_IDS) <= set(retail.NAME_OF)


def test_branch_search_is_restricted_to_the_market_country(monkeypatch):
    seen = {}
    monkeypatch.setattr(chains, "_get_json", lambda url, params: seen.update(params) or [])
    market.set_current("US")
    try:
        chains.nearest_branches(40.7, -74.0, ["Walmart"], radius_km=5)
    finally:
        market.set_current("FR")
    assert seen.get("countrycodes") == "us"


def test_money_in_sentences_becomes_dollars_for_the_us_only():
    text = "Value 77/100: score 82/100 at 20.44 EUR/kg, 3 g/EUR, more per euro"
    assert market.localize_money(text) == text                       # France (default): unchanged
    market.set_current("US")
    try:
        assert market.localize_money(text) == "Value 77/100: score 82/100 at $20.44/kg, 3 g/$, more per dollar"
        assert market.localize_money("à 7,30 € le kilo") == "à $7,30 le kilo"
    finally:
        market.set_current("FR")


def test_worker_threads_see_the_requests_market():
    from concurrent.futures import ThreadPoolExecutor
    market.set_current("US")
    try:
        with ThreadPoolExecutor(max_workers=3) as ex:
            assert main._ctx_map(ex, lambda _: market.current(), range(5)) == ["US"] * 5
            assert list(ex.map(lambda _: market.current(), range(2))) == ["FR"] * 2   # a plain map would lose it: the bug this helper prevents
    finally:
        market.set_current("FR")


def test_us_prices_are_us_shops_in_dollars(tmp_path):
    import json
    import sqlite3
    from app import value
    path = str(tmp_path / "op_us.db")
    db = sqlite3.connect(path)
    db.execute("create table op_items (code text, date text, data text)")
    today = __import__("datetime").date.today().isoformat()

    def item(country, price, cur, shop):
        return {"id": shop, "product_code": "0001", "price": price, "currency": cur, "price_per": None, "date": today,
                "location": {"id": shop, "osm_brand": "Safeway" if country == "US" else "Carrefour", "osm_address_country_code": country, "osm_lat": 37.7, "osm_lon": -122.4}}
    rows = [item("US", "4.00", "USD", 1), item("US", "4.00", "USD", 2), item("FR", "9.99", "EUR", 3)]
    db.executemany("insert into op_items values (?,?,?)", [("0001", today, json.dumps(r)) for r in rows])
    db.commit()
    us = value.OpenPricesClient(local_path=path, country="US", base="USD")
    got = us.latest("0001", (200.0, "g"))
    assert got["currency"] == "USD" and got["per100_cents"] == 200.0   # $4.00 for 200 g = $2.00 per 100 g; the French price is ignored
    assert got["n_observations"] == 2 and us.seen_in_france("0001") is True   # "seen in this client's country"
    fr = value.OpenPricesClient(local_path=path)
    assert fr.latest("0001", (200.0, "g"))["currency"] == "EUR"


def test_sold_here_is_recomputed_per_market_even_for_cached_products():
    p = {"countries": ["france"], "soldInFrance": True}                      # as cached by a French shopper
    assert main._sold_here(p) is True
    market.set_current("US")
    try:
        assert main._sold_here(p) is False                                    # a US shopper must not see it as sold in the US
        assert main._sold_here({"countries": ["united-states", "world"]}) is True
        assert main._sold_here({"countries": []}) is None
    finally:
        market.set_current("FR")
