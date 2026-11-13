"""The alternatives database: what the builder lets in, and how the request uses it.

A product is in alt_index.db only with a brand, a supermarket chain and a real observed price; the request then needs no
per-candidate lookups, only the shopper's filters and the ranking."""
import importlib
import json
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import altindex, main, market
from app.products import normalize

TODAY = date.today().isoformat()
YOGURT = ["en:dairies", "en:yogurts", "en:plain-yogurts"]


def raw(code, name, brand="Marque", qty="500 g", cats=YOGURT, sugars=4.5, protein=5, fibre=0):
    nm = {"energy-kcal_100g": 60, "fat_100g": 3, "saturated-fat_100g": 1.5, "carbohydrates_100g": max(5, sugars + 1), "sugars_100g": sugars, "proteins_100g": protein, "salt_100g": .1, "fiber_100g": fibre}
    r = {"code": code, "product_name": name, "brands": brand, "categories_tags": list(cats), "nutriments": nm, "ingredients_text": "lait",
         "nutriscore_grade": "b", "countries_tags": ["en:france"], "last_modified_t": 1700000000}
    if qty:
        r["quantity"] = qty
    return r


def observation(code, price, brand_shop="Carrefour Market", country="FR"):
    return json.dumps({"id": 1, "product_code": code, "price": price, "currency": "EUR", "price_per": None, "date": TODAY, "price_is_discounted": False,
                       "location": {"id": 1, "osm_id": 1, "osm_brand": brand_shop, "osm_name": brand_shop, "osm_address_country_code": country,
                                    "osm_lat": "48.85", "osm_lon": "2.35", "osm_address_city": "Paris"}})


def test_builder_keeps_only_branded_chained_priced_products(tmp_path, monkeypatch):
    off, ops, out = tmp_path / "off.db", tmp_path / "op.db", tmp_path / "alt.db"
    c = sqlite3.connect(off)
    c.execute("create table off_products (code text primary key, scans integer, data text)")
    for r in (raw("100", "Yaourt nature", "Marque"), raw("101", "Yaourt nature sans marque", ""), raw("102", "Yaourt nature sans taille", "Marque", qty=None),
              raw("103", "Yaourt nature belge", "Marque"), raw("104", "Yaourt nature sans enseigne", "Marque Inconnue")):
        c.execute("insert into off_products values (?,?,?)", (r["code"], 7, json.dumps(r)))
    c.commit()
    o = sqlite3.connect(ops)
    o.execute("create table op_items (code text, date text, data text)")
    o.execute("create index op_code on op_items (code, date desc)")
    for code, price, shop, country in (("100", "1.250", "Carrefour Market", "FR"), ("101", "1.250", "Carrefour Market", "FR"), ("102", "1.250", "Carrefour Market", "FR"),
                                       ("103", "1.250", "Delhaize", "BE"), ("104", "1.250", "Epicerie du coin", "FR")):
        o.execute("insert into op_items values (?,?,?)", (code, TODAY, observation(code, price, shop, country)))
    o.commit()
    monkeypatch.setattr(main, "_brand_chain_ids", lambda *a, **k: ["franprix"])   # brand-level "usually sold at" evidence must not put a product in a store it was never seen in
    monkeypatch.setenv("OFF_LOCAL", str(off)); monkeypatch.setenv("OP_LOCAL", str(ops)); monkeypatch.setenv("ALT_INDEX", str(out)); monkeypatch.setenv("MARKET", "FR")
    from scripts import build_alt_index
    importlib.reload(build_alt_index)
    build_alt_index.main()

    rows = sqlite3.connect(out).execute("select code, brand, per100, unit, chains from alt").fetchall()
    assert [r[0] for r in rows] == ["100"], "no brand, no pack size, no French price and no supermarket are each out"
    assert rows[0][1] == "Marque" and round(rows[0][2]) == 25 and rows[0][3] == "g"
    assert json.loads(rows[0][4]) == ["carrefour"], "only where this exact product was seen: never the brand's guessed stores"
    got = altindex.AltIndex(str(out)).candidates(["en:yogurts"])
    assert [g["code"] for g in got] == ["100"] and got[0]["quantity"] == {"amount": 500.0, "unit": "g"} and got[0]["price_date"] == TODAY


# ---- the request ------------------------------------------------------------------------------------------------------

ORIG = normalize(raw("000", "Yaourt nature", "Marque", cats=YOGURT))


class FakeOFF:
    def __init__(self, records):
        self.records, self.asked = {r["code"]: r for r in records}, []

    def quick_products(self, codes):
        self.asked += list(codes)
        return [self.records[c] for c in codes if c in self.records]


@pytest.fixture
def api(tmp_path, monkeypatch):
    """The real endpoint over an alternatives database of five yogurts; a sixth is in Open Food Facts but not in the database."""
    path = tmp_path / "alt.db"
    c = sqlite3.connect(path)
    c.executescript("""create table alt (code text primary key, brand text not null, name text not null, type text, per100 real not null, pack_cents integer,
                       amount real not null, unit text not null, price_date text not null, price_stale integer not null, chains text not null, scans integer);
                       create table alt_cat (tag text, code text); create table alt_tax (grp text, code text);""")
    rows = [("001", "Auchan", "Yaourt nature Auchan", 20.0, "g", ["auchan"]), ("002", "Leclerc", "Yaourt nature Leclerc", 15.0, "g", ["leclerc"]),
            ("003", "Marque B", "Yaourt nature B", 40.0, "g", ["carrefour", "leclerc"]), ("004", "Marque C", "Yaourt nature en litres", 10.0, "ml", ["carrefour"]),
            ("005", "Marque D", "Yaourt nature D", 25.0, "g", ["carrefour"])]
    for code, brand, name, p100, unit, chains in rows:
        c.execute("insert into alt values (?,?,?,?,?,?,?,?,?,?,?,?)", (code, brand, name, "yogurt", p100, round(p100 * 5), 500, unit, TODAY, 0, json.dumps(chains), 3))
        c.executemany("insert into alt_cat values (?,?)", [(t, code) for t in YOGURT])
    c.commit()
    sweet = dict(sugars=25, protein=2)              # every other yogurt is sweet and low in protein: 003, the dearest, is by far the best nutritionally
    off = FakeOFF([raw(code, name, brand, qty="500 ml" if unit == "ml" else "500 g", **({} if code == "003" else sweet)) for code, brand, name, _, unit, _ in rows]
                  + [raw("006", "Yaourt nature hors base", "Marque E")])
    priced = []
    monkeypatch.setattr(main, "load_product", lambda s, b: dict(ORIG))
    monkeypatch.setattr(main, "_price_map", lambda s, uid, orig, prods, *a, **k: (priced.append(list(prods)) or (60.0, {}, {orig["barcode"]: {"source": "open_prices", "date": TODAY}}, {})))
    monkeypatch.setattr(main.app.state, "off", off)
    monkeypatch.setattr(main.app.state, "alt", market.PerMarket({"FR": altindex.AltIndex(str(path))}))
    client = TestClient(main.app)

    def post(**body):
        r = client.post("/v1/products/000/alternatives", headers={"X-Session-Id": "alt-index-test", "X-Country": "FR"},
                        json={"priorities": ["overall"], "category_mode": "similar", "limit": 10, **body})
        assert r.status_code == 200, r.text
        return r.json()
    post.off, post.priced = off, priced
    return post


def test_request_reads_the_database_and_prices_only_the_scanned_product(api):
    res = api()
    assert api.priced == [[]], "candidates already carry their price: only the scanned product is priced"
    assert "006" not in api.off.asked and set(api.off.asked) == {"001", "002", "003", "005"}, "only database rows are read, and not the one in litres"
    rows = res["rankings"]["value"]
    assert {r["product"]["barcode"] for r in rows} == {"001", "002", "003", "005"}
    for r in rows:
        assert r["product"]["brand"] and r["product"]["chains"] and r["price_per_100_cents"] is not None
    assert [r["value_score"] for r in rows] == sorted((r["value_score"] for r in rows), reverse=True)
    assert res["diagnostics"]["retrieved"] == res["diagnostics"]["at_supermarket"] == res["diagnostics"]["with_price"] == 4


def test_chain_filter_applies_on_top_of_the_database(api):
    rows = api(chains=["leclerc"])["rankings"]["value"]
    assert {r["product"]["barcode"] for r in rows} == {"002", "003"}
    assert all("leclerc" in r["product"]["chains"] for r in rows)


def test_every_profile_is_ranked_in_one_answer(api):
    """Budget leads with the cheapest decent product, nutrition with the best quality, balanced with the best of both:
    all three come in the same response, so switching needs no new request."""
    res = api()
    rows = {r["product"]["barcode"]: r for r in res["rankings"]["value"]}
    quality = {c: r["quality_score"] for c, r in rows.items()}
    assert quality["003"] > max(q for c, q in quality.items() if c != "003") + 8, "the fixture's best product must really be the best"
    first = {pf: res["rankings"]["profiles"][pf][0]["code"] for pf in ("budget", "balanced", "nutrition")}
    assert first["budget"] == "002", "the cheapest leads the budget profile"
    assert first["nutrition"] == "003", "the best quality leads the nutrition profile, whatever it costs"
    for pf in ("budget", "balanced", "nutrition"):
        assert {x["code"] for x in res["rankings"]["profiles"][pf]} == set(rows), "same products in every profile, only the order differs"
    assert api(profile="nutrition")["rankings"]["value"][0]["product"]["barcode"] == "003"


def test_maple_syrup_never_leads_to_agave():
    from app import taxonomy
    syrup = lambda name, cat: {"name": name, "brand": "Marque", "categories": ["en:syrups", "en:simple-syrups", cat], "quantity": {"amount": 250, "unit": "ml"}, "nutriments": {}}  # noqa: E731
    maple, agave, maple2 = syrup("Sirop d'érable", "en:maple-syrups"), syrup("Sirop d'agave bio", "en:agave-syrups"), syrup("Sirop d'érable bio", "en:maple-syrups")
    assert taxonomy.substitution(maple, agave) is None
    assert taxonomy.substitution(maple, maple2) is not None
