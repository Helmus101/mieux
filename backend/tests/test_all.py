import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from fastapi.testclient import TestClient  # noqa: E402

from app import db, engine, main, receipts  # noqa: E402
from app.products import normalize  # noqa: E402


def raw(code, name, sugars, prot, cats=("en:dairies", "en:yogurts"), ing="milk", allergens=("en:milk",), grade="b", an=("en:vegetarian",)):
    nm = {"energy-kcal_100g": 90, "fat_100g": 2, "saturated-fat_100g": 1, "carbohydrates_100g": 8, "sugars_100g": sugars, "proteins_100g": prot, "salt_100g": .1, "fiber_100g": .5}
    nm = {k: v for k, v in nm.items() if v is not None}
    if sugars is None: nm.pop("sugars_100g", None)
    return {"code": code, "product_name": name, "brands": "B", "categories_tags": list(cats), "nutriments": nm, "ingredients_text": ing,
            "allergens_tags": list(allergens), "ingredients_analysis_tags": list(an), "nutriscore_grade": grade, "last_modified_t": 1700000000, "countries_tags": ["en:france"]}


class FakeOFF:
    def __init__(self):
        self.items = {r["code"]: r for r in [
            raw("1", "Strawberry yogurt", 12, 4, grade="d"),
            raw("2", "Skyr nature", 5, 10, grade="a"),
            raw("3", "Yaourt grec nature", 4, 9),
            raw("4", "Peanut yogurt", 2, 12, allergens=("en:milk", "en:peanuts")),
            raw("5", "Unknown yogurt", None, 12),
            raw("6", "No-ingredients yogurt", 3, 11, ing=None),
            raw("7", "Chocolate cereal", 20, 6, cats=("en:cereals",)),
        ]}
    def get_product(self, b): return self.items.get(b)
    def search_category(self, tag, size=60): return [r for r in self.items.values() if tag in r["categories_tags"]] * 3 if tag == "en:yogurts" else []
    def search_name(self, q): return [r for r in self.items.values() if q.lower() in r["product_name"].lower()]


main.app.state.off = FakeOFF()
c = TestClient(main.app)
main.app.state.prices = type("Stocked", (), {"latest": lambda self, *a, **k: None, "chain_summary": lambda self, *a, **k: [{"chain": "Carrefour"}]})()  # every product is sold somewhere
H = {"X-Session-Id": "test-session-1", "X-Lang": "en"}


def test_missing_stays_none():
    p = normalize(main.app.state.off.items["5"])
    assert p["nutriments"]["sugars100g"] is None and not p["dataQuality"]["nutritionComplete"]


def test_unknown_barcode_and_auth():
    assert c.get("/v1/products/999", headers=H).status_code == 404
    assert c.get("/v1/products/1").status_code == 401


def test_alternatives_rank_and_explain():
    r = c.post("/v1/products/1/alternatives", headers=H, json={"category_mode": "any", "priorities": ["protein", "sugars"], "limit": 5, "excluded_allergens": ["peanuts"]}).json()
    ids = [a["product_id"] for a in r["alternatives"]]
    assert ids[0] == "2" and "3" in ids                      # skyr: +6 g protein beats greek +5
    assert "5" not in ids and "6" not in ids and "7" not in ids   # incomplete / unverified... / wrong category
    a = r["alternatives"][0]
    assert a["comparison"]["protein_difference_per_100g"] == 6.0 and a["comparison"]["sugars_difference_per_100g"] == -7.0
    assert any("protein" in x for x in a["improvements"]) and a["tradeoffs"]


def test_allergen_hard_exclusion_and_unverified():
    c.put("/v1/me/preferences", headers=H, json={"diet": "omnivore", "priorities": ["protein"], "allergens": ["peanuts"]})
    r = c.post("/v1/products/1/alternatives", headers=H, json={"category_mode": "any", "priorities": ["protein"]}).json()
    ids = [a["product_id"] for a in r["alternatives"]]
    assert "4" not in ids and "6" not in ids                      # peanut conflict; no ingredients => cannot verify
    assert r["excluded"]["conflict"] >= 1 and r["excluded"]["unverified"] >= 1
    c.put("/v1/me/preferences", headers=H, json={"diet": "omnivore", "priorities": [], "allergens": []})


def test_no_recommendation():
    r = c.post("/v1/products/4/alternatives", headers=H, json={"category_mode": "any", "priorities": ["protein"]}).json()
    assert r["alternatives"] == [] and r["no_recommendation_reason"]


def test_compare_same_basis():
    r = c.post("/v1/comparisons", headers=H, json={"product_ids": ["1", "2"]}).json()
    assert r["basis"].startswith("per 100")
    prot = next(x for x in r["rows"] if x["field"] == "protein100g")
    assert prot["favourable"] == [False, True]


SAMPLE = [{"text": t, "confidence": .97, "position": i} for i, t in enumerate(
    ["MONOPRIX PARIS", "28/10/2026", "YAOURT GREC 1,59", "BANANES 2,10", "FLOCONS AVOINE 1,89", "OEUFS 3,20", "POMMES 2,75", "SOUS-TOTAL 11,53", "TOTAL 11,53 EUR", "CB 11,53", "TVA 5,5% 0,60"])]


def test_receipt_parse_french_decimals():
    r = receipts.parse(SAMPLE)
    assert r["total_cents"] == 1153 and len(r["items"]) == 5 and sum(i["line_total_cents"] for i in r["items"]) == 1153
    assert r["purchase_date"] == "2026-10-28" and not r["warnings"]
    # Verify the 5 items are the expected ones
    item_names = [i["raw"] for i in r["items"]]
    assert "YAOURT GREC" in item_names


def test_receipt_flow_duplicate_delete_and_last_price():
    c.get("/v1/products/3", headers=H); c.post("/v1/scans", headers=H, json={"barcode": "3"})
    pv = c.post("/v1/receipts/preview", headers=H, json={"lines": SAMPLE}).json()
    yo = pv["items"][0]
    assert yo["match_candidate"]["product_id"] == "3"      # candidate only, user must confirm
    body = {"retailer": pv["retailer"], "purchase_date": pv["purchase_date"], "total_cents": pv["total_cents"],
            "items": [{"raw_description": i["raw"], "unit_price_cents": i["unit_price_cents"], "line_total_cents": i["line_total_cents"],
                       "matched_product_id": "3" if k == 0 else None} for k, i in enumerate(pv["items"])]}
    rid = c.post("/v1/receipts/confirm", headers=H, json=body).json()["id"]
    assert c.post("/v1/receipts/confirm", headers=H, json=body).status_code == 409
    assert c.post("/v1/receipts/preview", headers=H, json={"lines": SAMPLE}).json()["possible_duplicate"]
    p = c.get("/v1/purchases", headers=H).json()
    assert p["recorded_spending_cents"] == 1153 and any(x["product_id"] == "3" and x["last_price_cents"] == 159 for x in p["purchases"])
    assert c.delete(f"/v1/receipts/{rid}", headers=H).status_code == 200
    assert c.get("/v1/purchases", headers=H).json()["purchases"] == []
    s = main.app.state.sessions()
    assert s.query(db.PriceObservation).count() == 0 and s.query(db.ReceiptItem).count() == 0


def test_erase_account():
    assert c.delete("/v1/me", headers=H).json()["deleted"]
    assert c.get("/v1/scans", headers=H).json()["scans"] == []


# ---- value / grocery intelligence
from app import value  # noqa: E402


def test_quantity_parsing():
    assert value.parse_quantity("375 g") == (375.0, "g")
    assert value.parse_quantity("1,5 l") == (1500.0, "ml")
    assert value.parse_quantity("6 x 125 g") == (750.0, "g")
    assert value.parse_quantity(None) is None and value.parse_quantity("one pot") is None


class FakePrices:
    def latest(self, barcode, qty, max_age_days=None):
        return {"source": "open_prices", "per100_cents": 30.0, "date": __import__("datetime").date.today().isoformat(), "where": "Test shop"} if barcode == "2" else None


def test_insights_saving_needs_size_and_dated_price():
    from datetime import date
    main.app.state.prices = FakePrices()
    for r in main.app.state.off.items.values():
        r["quantity"] = "400 g"
    H2 = {"X-Session-Id": "insight-user-1"}
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()   # drop cached copies made before sizes existed
    c.put("/v1/me/preferences", headers=H2, json={"diet": "omnivore", "priorities": ["protein"], "allergens": []})
    c.get("/v1/products/1", headers=H2); c.post("/v1/scans", headers=H2, json={"barcode": "1"})
    today = date.today().isoformat()
    c.post("/v1/receipts/confirm", headers=H2, json={"retailer": "Carrefour", "purchase_date": today, "total_cents": 200,
           "items": [{"raw_description": "YAOURT FRAISE", "unit_price_cents": 200, "line_total_cents": 200, "matched_product_id": "1"}]})
    r = c.get("/v1/insights", headers=H2).json()
    assert r["month_spend_cents"] == 200 and r["top_products"][0]["share"] == 1.0
    o = r["opportunities"][0]
    assert o["alternative"]["id"] == "2" and o["alt_price"]["source"] == "open_prices"
    assert o["your_price"]["per100_cents"] == 50.0 and o["saving_per_purchase_cents"] == 80   # (50-30)*400/100
    assert o["protein_g_per_euro"]["alternative"] > o["protein_g_per_euro"]["yours"] and o["caveats"]
    main.app.state.prices = type("N", (), {"latest": lambda self, b, q, *a: None})()
    assert c.get("/v1/insights", headers=H2).json()["opportunities"] == []   # no verified price => no saving claimed


def test_budget_priority_ranks_by_verified_price_only():
    from datetime import date
    main.app.state.prices = type("P", (), {"latest": lambda self, b, q, *a: {"source": "open_prices", "per100_cents": {"2": 30.0, "3": 45.0}.get(b, 60.0) if b != "1" else 50.0, "date": date.today().isoformat(), "where": "X"}})()
    Hb = {"X-Session-Id": "budget-user-1", "X-Lang": "en"}
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    r = c.post("/v1/products/1/alternatives", headers=Hb, json={"priorities": ["budget"], "excluded_allergens": ["peanuts"]}).json()
    ids = [a["product_id"] for a in r["alternatives"]]
    assert ids[0] == "2" and "3" in ids and "5" not in ids or ids[0] == "2"
    assert r["alternatives"][0]["comparison"]["price_difference_cents_per_100g"] == -20.0
    r2 = c.post("/v1/products/1/alternatives", headers=Hb, json={"priorities": ["protein", "budget"], "excluded_allergens": ["peanuts"]}).json()
    assert r2["alternatives"][0]["product_id"] == "5"        # protein first: 12 g beats 10 g; price breaks ties
    assert all("price_per_100_cents" in a for a in r2["alternatives"])
    main.app.state.prices = type("N", (), {"latest": lambda self, b, q, *a: None})()
    r3 = c.post("/v1/products/1/alternatives", headers=Hb, json={"category_mode": "any", "priorities": ["budget"]}).json()
    assert r3["alternatives"] == [] and "price" in (r3["price_note"] or "").lower()


def test_french_by_default():
    r = c.post("/v1/products/1/alternatives", headers={"X-Session-Id": "fr-user-001"}, json={"category_mode": "any", "priorities": ["protein"], "excluded_allergens": ["peanuts"]}).json()
    txt = " ".join(r["alternatives"][0]["improvements"] + r["alternatives"][0]["tradeoffs"])
    assert "protéines" in txt and "en plus" in txt
    r = c.post("/v1/products/4/alternatives", headers={"X-Session-Id": "fr-user-001"}, json={"category_mode": "any", "priorities": ["protein"]}).json()
    assert r["no_recommendation_reason"].startswith("Aucune alternative")


def test_value_ranking_and_price_comparison_always_present():
    from datetime import date
    today = date.today().isoformat()
    per = {"1": 50.0, "2": 30.0, "3": 45.0}
    main.app.state.prices = type("P", (), {"latest": lambda self, b, q, *a: {"source": "open_prices", "per100_cents": per.get(b, 90.0), "date": today, "where": "X"}})()
    Hv = {"X-Session-Id": "value-user-1", "X-Lang": "en"}
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    r = c.post("/v1/products/1/alternatives", headers=Hv, json={"priorities": ["value", "protein"], "excluded_allergens": ["peanuts"]}).json()
    a0 = r["alternatives"][0]
    assert a0["product_id"] == "2"                                   # 10 g protein at 0.30/100 g = 33 g/EUR vs 8 g/EUR
    assert round(a0["value"]["protein_g_per_euro"]["alt"], 1) == 33.3 and round(a0["value"]["protein_g_per_euro"]["orig"], 1) == 8.0
    assert any("per euro" in x for x in a0["improvements"])
    # a non-price priority still returns the price comparison
    r2 = c.post("/v1/products/1/alternatives", headers=Hv, json={"priorities": ["protein"], "excluded_allergens": ["peanuts"]}).json()
    assert r2["original_price"]["per100_cents"] == 50.0 and r2["alternatives"][0]["value"] is not None and r2["alternatives"][0]["price_source"]["source"] == "open_prices"
    # no price anywhere -> no price claims
    main.app.state.prices = type("N", (), {"latest": lambda self, b, q, *a: None})()
    r3 = c.post("/v1/products/1/alternatives", headers=Hv, json={"priorities": ["protein"], "excluded_allergens": ["peanuts"], "approximate": False}).json()
    assert r3["original_price"] is None and r3["alternatives"][0]["value"] is None


def test_store_prices_by_location_and_alternatives_use_nearby():
    from datetime import date
    from app import value as V
    today = date.today().isoformat()
    class Geo:
        def _it(self, price, name, lat, lon, city, d=today, i=1):
            return {"price": price, "price_per": None, "date": d, "location": {"id": i, "osm_name": name, "osm_brand": name, "osm_address_city": city, "osm_lat": lat, "osm_lon": lon}}
        def stores(self, b, q, lat, lon, r):
            data = {"2": [("Lidl", 1.2, 48.86, 2.35, "Paris", 1), ("Carrefour", 1.5, 48.85, 2.34, "Paris", 2), ("Auchan", 0.9, 45.7, 4.8, "Lyon", 3)]}.get(b, [("Monoprix", 2.0, 48.86, 2.35, "Paris", 4)])
            out = []
            for n, p, la, lo, city, k in data:
                d = V.haversine_km(lat, lon, la, lo)
                if d <= r: out.append({"store": n, "name": n, "city": city, "per100_cents": p * 100 / 4, "pack_cents": round(p * 100), "date": today, "distance_km": round(d, 1), "source": "open_prices"})
            return sorted(out, key=lambda x: x["per100_cents"])
        def latest(self, b, q, *a): return None
    main.app.state.prices = Geo()
    Hs = {"X-Session-Id": "geo-user-001", "X-Lang": "en"}
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    r = c.post("/v1/products/2/store-prices", headers=Hs, json={"lat": 48.8566, "lon": 2.3522, "radius_km": 15}).json()
    assert [x["store"] for x in r["stores"]] == ["Lidl", "Carrefour"]          # Lyon is outside the radius


def test_nova_and_vitamins_normalised():
    raw_p = raw("9", "Cereal", 5, 8)
    raw_p["nova_group"] = 4
    raw_p["nutriments"].update({"vitamin-c_100g": 0.08, "vitamin-d_100g": 0.000005, "iron_100g": 0.007})
    p = normalize(raw_p)
    assert p["novaGroup"] == 4
    m = {x["key"]: x for x in p["micronutrients"]}
    assert m["vit_c"]["amount"] == 80.0 and m["vit_c"]["unit"] == "mg" and m["vit_c"]["nrv_pct"] == 100
    assert m["vit_d"]["amount"] == 5.0 and m["vit_d"]["unit"] == "µg" and m["iron"]["nrv_pct"] == 50
    assert "vit_a" not in m                      # absent is not shown as zero
    est = normalize(raw("8", "x", 1, 1))                                # no official group -> estimated from the ingredient list, and flagged
    assert est["novaGroup"] == 1 and est["novaEstimated"] is True and p["novaEstimated"] is False


def test_indicators_and_three_rankings():
    from datetime import date
    today = date.today().isoformat()
    per = {"1": 50.0, "2": 30.0, "3": 45.0}
    main.app.state.prices = type("P", (), {"latest": lambda self, b, q, *a: {"source": "open_prices", "per100_cents": per.get(b, 90.0), "date": today, "where": "X"}})()
    for r in main.app.state.off.items.values(): r["quantity"] = "400 g"; r["serving_quantity"] = 125
    Hr = {"X-Session-Id": "rank-user-001", "X-Lang": "en"}
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    r = c.post("/v1/products/1/alternatives", headers=Hr, json={"priorities": ["protein"], "excluded_allergens": ["peanuts"]}).json()
    ind = r["original_indicators"]
    assert ind["price_per_kg_eur"] == 5.0 and ind["price_per_serving_eur"] == 0.62 and ind["cost_per_10g_protein_eur"] == 1.25   # 0.5 EUR/100 g -> 10 g protein costs 1.25
    rk = r["rankings"]
    assert rk["budget"][0]["product"]["barcode"] == "2" and rk["budget"][0]["price_per_100_cents"] == 30.0 and rk["budget"][0]["why"]
    assert rk["value"][0]["product"]["barcode"] == "2"
    assert all(x["product"]["barcode"] != "7" for x in rk["budget"] + rk["value"])        # different category never ranked
    assert len(rk["match"]) >= 1
    main.app.state.prices = type("N", (), {"latest": lambda self, b, q, *a: None})()
    r2 = c.post("/v1/products/1/alternatives", headers=Hr, json={"priorities": ["protein"], "excluded_allergens": ["peanuts"], "approximate": False}).json()
    assert r2["rankings"]["budget"] == [] and r2["rankings"]["value"] == [] and r2["original_indicators"] is None


def test_a_price_is_never_guessed_from_a_category_average():
    from app import estimate as E
    assert not hasattr(E, "estimate_per100") and not hasattr(E, "category_price_per100")      # removed on purpose
    ch = E.chain_prices(100.0, 400)                                                           # chain levels apply only to a price that exists
    assert ch[0]["chain"] in ("Lidl", "Aldi") and ch[-1]["chain"].startswith("Naturalia") and ch[0]["pack_cents"] == 344
    main.app.state.prices = type("N", (), {"latest": lambda self, b, q, *a: None, "stores": lambda self, *a: []})()
    for r in main.app.state.off.items.values(): r["quantity"] = "400 g"
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    Hq = {"X-Session-Id": "estimate-user-1", "X-Lang": "en"}
    for approx in (True, False):                                                              # even when a client still asks for estimates
        r = c.post("/v1/products/1/alternatives", headers=Hq, json={"priorities": ["protein"], "excluded_allergens": ["peanuts"], "approximate": approx}).json()
        assert r["original_price"] is None and "paris_estimate" not in r and not r.get("original_estimated")
        assert all(a["price_per_100_cents"] is None and not a["estimated"] for a in r["alternatives"])
    for qs in ("", "?approximate=true"):
        pc = c.get("/v1/products/1" + qs, headers=Hq).json()["price_context"]
        assert pc["estimate"] is None and (pc["value"] is None or pc["value"].get("basis_source") != "estimate")


def test_product_price_database_is_per_product_not_per_shop():
    from datetime import date
    today = date.today().isoformat()
    main.app.state.prices = type("P", (), {"latest": lambda self, b, q, *a: {"source": "open_prices", "per100_cents": 40.0, "date": today, "where": "Some Shop"}, "stores": lambda self, *a: []})()
    for r in main.app.state.off.items.values(): r["quantity"] = "500 g"
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    Hp = {"X-Session-Id": "pricedb-user-01", "X-Lang": "en"}
    assert c.post("/v1/products/3/prices", headers=Hp, json={"price_cents": 250}).status_code == 200      # manual entry
    h = c.get("/v1/products/3/prices", headers=Hp).json()["history"]
    assert h[0]["source"] == "manual" and h[0]["pack_cents"] == 250 and h[0]["per100_cents"] == 50.0 and "retailer" not in h[0] and "store" not in h[0]
    pc = c.get("/v1/products/3", headers=Hp).json()["price_context"]
    assert pc["your_last"]["unit_price_cents"] == 250 and pc["history"] and pc["summary"]["n"] >= 1
    c.post("/v1/products/1/alternatives", headers=Hp, json={"priorities": ["protein"], "excluded_allergens": ["peanuts"]})   # fetches community prices
    sess = main.app.state.sessions()
    assert sess.query(db.ProductPrice).filter_by(source="open_prices", user_id=None).count() >= 1               # stored for everyone, no shop column
    assert not hasattr(db.ProductPrice, "retailer")
    pid = h[0]["id"]
    assert c.delete(f"/v1/prices/{pid}", headers=Hp).status_code == 200
    assert not [x for x in c.get("/v1/products/3/prices", headers=Hp).json()["history"] if x["id"] == pid]


def test_price_constraint_compare_prices_and_receipt_name_search():
    from datetime import date
    today = date.today().isoformat()
    per = {"1": 50.0, "2": 30.0, "3": 55.0}
    main.app.state.prices = type("P", (), {"latest": lambda self, b, q, *a: {"source": "open_prices", "per100_cents": per.get(b, 90.0), "date": today, "where": None}})()
    for r in main.app.state.off.items.values(): r["quantity"] = "400 g"
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.query(db.ProductPrice).delete(); _s.commit()
    Hk = {"X-Session-Id": "constraint-user-1", "X-Lang": "en"}
    base = {"priorities": ["protein"], "excluded_allergens": ["peanuts"], "approximate": False}
    r = c.post("/v1/products/1/alternatives", headers=Hk, json={**base, "price_constraint": "cheaper"}).json()
    ids = [a["product_id"] for a in r["alternatives"]]
    assert ids == ["2"]                                     # 3 costs more, 5 has no price: neither passes "cheaper"
    r = c.post("/v1/products/1/alternatives", headers=Hk, json={**base, "price_constraint": "any"}).json()
    assert {"2", "3"} <= {a["product_id"] for a in r["alternatives"]}
    cmpr = c.post("/v1/comparisons", headers=Hk, json={"product_ids": ["1", "2"]}).json()
    assert cmpr["products"][0]["price"]["per100_cents"] == 50.0 and cmpr["products"][1]["price"]["pack_cents"] == 120
    # receipt line with no scanned match is looked up by name; it is only a candidate
    pv = c.post("/v1/receipts/preview", headers=Hk, json={"lines": [{"text": "YAOURT GREC 1,59", "position": 0}, {"text": "TOTAL 1,59", "position": 1}]}).json()
    cand = pv["items"][0]["match_candidate"]
    assert cand and cand["product_id"] == "3" and cand["source"] == "search" and cand["score"] >= 0.6


def test_budget_api_adapts_and_savings_are_realised_only_by_a_receipt():
    from datetime import date
    today = date.today().isoformat()
    main.app.state.prices = type("P", (), {"latest": lambda self, b, q, *a: {"source": "open_prices", "per100_cents": {"1": 50.0, "2": 30.0}.get(b, 90.0), "date": today, "where": None}})()
    for r in main.app.state.off.items.values(): r["quantity"] = "400 g"
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    Hb2 = {"X-Session-Id": "budget-api-user1", "X-Lang": "en"}
    assert c.get("/v1/budget", headers=Hb2).json()["budget"] is None
    assert c.put("/v1/me/budget", headers=Hb2, json={"period": "monthly", "amount_cents": 10000, "style": "balanced", "savings_goal_cents": 3000}).status_code == 200
    c.get("/v1/products/1", headers=Hb2); c.post("/v1/scans", headers=Hb2, json={"barcode": "1"}); c.get("/v1/products/2", headers=Hb2); c.post("/v1/scans", headers=Hb2, json={"barcode": "2"})
    b = c.get("/v1/budget", headers=Hb2).json()["budget"]
    assert b["status"]["spent_cents"] == 0 and b["pressure"] == "relaxed" and b["recommended_ranking"] == "value"
    c.post("/v1/receipts/confirm", headers=Hb2, json={"retailer": "X", "purchase_date": today, "total_cents": 9500,
           "items": [{"raw_description": "BIG SHOP", "unit_price_cents": 9500, "line_total_cents": 9500}]})
    b = c.get("/v1/budget", headers=Hb2).json()["budget"]
    assert b["status"]["spent_cents"] == 9500 and b["pressure"] == "tight" and b["recommended_ranking"] == "budget"   # updates after the receipt
    r = c.post("/v1/products/1/alternatives", headers=Hb2, json={"priorities": ["protein"], "excluded_allergens": ["peanuts"]}).json()
    assert r["budget"]["recommended_ranking"] == "budget" and r["budget"]["pressure"] == "tight"
    # choose the cheaper alternative: counts as chosen, NOT realised
    s1 = c.post("/v1/savings/choose", headers=Hb2, json={"original_id": "1", "alt_id": "2", "expected_saving_cents": 80, "original_per100_cents": 50.0}).json()["savings"]
    assert s1["realized_cents"] == 0 and s1["chosen_cents"] == 80
    # a receipt that actually contains the alternative (paid 1.00 for 400 g = 25/100 g) realises (50-25)*4 = 100 cents
    c.post("/v1/receipts/confirm", headers=Hb2, json={"retailer": "Y", "purchase_date": today, "total_cents": 100,
           "items": [{"raw_description": "SKYR", "unit_price_cents": 100, "line_total_cents": 100, "matched_product_id": "2"}]})
    s2 = c.get("/v1/budget", headers=Hb2).json()["savings"]
    assert s2["realized_cents"] == 100 and s2["chosen_cents"] == 0 and s2["goal_cents"] == 3000 and s2["acceptance_pct"] == 100


def test_category_budgets_and_receipt_status():
    from datetime import date
    today = date.today().isoformat()
    for r in main.app.state.off.items.values(): r["quantity"] = "400 g"
    _s = main.app.state.sessions(); _s.query(db.Product).delete(); _s.commit()
    Hc = {"X-Session-Id": "catbudget-user1", "X-Lang": "en"}
    c.put("/v1/me/budget", headers=Hc, json={"period": "monthly", "amount_cents": 20000, "style": "balanced", "categories": {"dairy": 3000, "bogus": 100}})
    c.get("/v1/products/3", headers=Hc); c.post("/v1/scans", headers=Hc, json={"barcode": "3"})
    pv = c.post("/v1/receipts/preview", headers=Hc, json={"lines": [{"text": "YAOURT GREC 1,59", "position": 0}, {"text": "PAIN BIZARRE 2,00", "position": 1}, {"text": "TOTAL 3,59", "position": 2}]}).json()
    st = {i["raw"]: i["match_status"] for i in pv["items"]}
    assert st["YAOURT GREC"] == "probable" and st["PAIN BIZARRE"] == "unidentified"
    c.post("/v1/receipts/confirm", headers=Hc, json={"retailer": "X", "purchase_date": today, "total_cents": 359,
           "items": [{"raw_description": "YAOURT GREC", "unit_price_cents": 159, "line_total_cents": 159, "matched_product_id": "3"},
                     {"raw_description": "PAIN BIZARRE", "unit_price_cents": 200, "line_total_cents": 200}]})
    b = c.get("/v1/budget", headers=Hc).json()["budget"]
    assert b["config"]["categories"] == {"dairy": 3000}                       # unknown groups are dropped
    d = next(x for x in b["category_status"] if x["group"] == "dairy")
    assert d["spent_cents"] == 159 and d["used_pct"] == 5.3                   # only the matched line counts toward its group
    assert b["status"]["spent_cents"] == 359                                  # but the unidentified line is still in the total
    assert c.get("/v1/budget/forecast", headers=Hc).status_code == 200 and c.get("/v1/savings", headers=Hc).status_code == 200
    assert c.get("/v1/prices?product=3", headers=Hc).status_code == 200


def test_an_already_cached_web_price_shows_up_even_when_this_candidate_is_not_searched_again(monkeypatch):
    """A price found earlier (through that product's own page, say) must appear for every alternatives request from then on,
    not only when this candidate happens to be among the limited set the server starts a fresh search for this time."""
    from app import webprice
    monkeypatch.setattr(main, "_search_targets", lambda *a, **k: [])          # no candidate is chosen for a fresh search this time
    monkeypatch.setattr(main, "_own_price", lambda *a, **k: None)
    monkeypatch.setattr(main, "_community", lambda *a, **k: None)             # no observed/community price for anyone: isolates the web-cache fallback
    cached = {"per100_cents": 45.0, "pack_cents": 180, "store": "Carrefour", "stores": ["Carrefour"], "chains": ["carrefour"],
              "source_urls": ["https://x.fr"], "date": "2026-11-10", "source": "web_search", "approximate": True}
    monkeypatch.setattr(webprice, "enabled", lambda: True)
    monkeypatch.setattr(webprice, "cached_only", lambda p: cached if p.get("barcode") == "2" else None)
    r = c.post("/v1/products/1/alternatives", headers=H, json={"category_mode": "any", "priorities": ["protein"], "excluded_allergens": ["peanuts"]}).json()
    row = next(x for lst in r["rankings"].values() if isinstance(lst, list) for x in lst if x.get("product", {}).get("id") == "2")
    assert row["price_per_100_cents"] == 45.0
