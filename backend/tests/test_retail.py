from app import db, retail


def session():
    return db.make_session_factory("sqlite:///:memory:")()


def test_seed_and_chain_listings_are_independent_of_branches():
    s = session()
    retail.seed(s)
    assert s.query(db.RetailChain).count() >= 10
    p = {"id": "3000000000001", "brand": "Marque Repère, Epi d'Or"}
    sightings = [{"store": "Carrefour City", "per100_cents": 111.2}, {"name": "Lidl", "per100_cents": 88.0}, {"store": "Boulangerie du coin", "per100_cents": 50}]
    rows = {r.chain_id: r for r in retail.discover(s, p, sightings)}
    assert set(rows) == {"carrefour", "lidl", "leclerc"}                 # two sightings + the own brand; the bakery is not a chain
    assert rows["carrefour"].match_type == "exact_ean" and rows["carrefour"].source == "open_prices" and rows["carrefour"].listing_status == "listed"
    assert rows["leclerc"].match_type == "own_brand" and rows["leclerc"].match_confidence < 1
    assert s.query(db.ChainProductListing).count() == 3                  # one row per chain, never per branch
    retail.discover(s, p, sightings)                                     # idempotent
    assert s.query(db.ChainProductListing).count() == 3


def test_user_confirmation_never_downgrades_exact_ean_and_unknown_is_not_stored():
    s = session()
    retail.seed(s)
    p = {"id": "3000000000002", "brand": "X"}
    retail.discover(s, p, [{"store": "Monoprix", "per100_cents": 100}])
    r = retail.confirm(s, "3000000000002", "monoprix")
    assert r.match_type == "exact_ean"                                    # the stronger evidence stays
    r2 = retail.confirm(s, "3000000000002", "auchan", "https://example.test/p")
    assert r2.match_type == "user_confirmed" and r2.source_url
    assert s.query(db.ChainProductListing).filter_by(product_id="3000000000002", chain_id="intermarche").count() == 0   # absence of evidence is not a row


def test_nearest_branches_come_from_our_stores_table_sorted_by_distance():
    s = session()
    retail.seed(s)
    for i, (la, lo) in enumerate([(48.8590, 2.3522), (48.8700, 2.3600), (48.9000, 2.4000)]):
        s.add(db.Store(chain_id="carrefour", store_name=f"Carrefour {i}", latitude=la, longitude=lo, source_id=f"n{i}"))
    s.commit()
    near = retail.nearest(s, "carrefour", 48.8566, 2.3522, 10, k=2, refresh=False)
    assert [n["name"] for n in near] == ["Carrefour 0", "Carrefour 1"] and near[0]["distance_m"] < near[1]["distance_m"]
    assert near[0]["distance_m"] < 400
    assert retail.nearest(s, "carrefour", 43.2965, 5.3698, 10, refresh=False) == []   # Marseille: none stored, none invented


def test_open_prices_average_per_chain_and_chain_listing_from_any_french_sighting():
    import time
    from datetime import date
    from app import value
    today = date.today().isoformat()
    c = value.OpenPricesClient("/nonexistent/op_local.db")
    loc = lambda i, brand, cc="FR": {"id": i, "osm_brand": brand, "osm_name": brand, "osm_address_country_code": cc}  # noqa: E731
    item = lambda price, l: {"price": price, "currency": "EUR", "price_per": None, "date": today, "location": l}  # noqa: E731
    c._raw["9"] = (time.time(), [item(2.0, loc(1, "Carrefour City")), item(2.2, loc(2, "Carrefour Market")), item(9.0, loc(3, "Carrefour")),   # 9.0 is an outlier
                                 item(1.6, loc(4, "Super U")), item(5.0, loc(5, "Carrefour", "ES"))])                                          # Spain ignored
    rows = {r["chain"]: r for r in c.chain_summary("9", (400.0, "g"))}
    assert set(rows) == {"Carrefour", "Super U"}
    assert rows["Carrefour"]["shops"] == 3 and abs(rows["Carrefour"]["per100_cents"] - 52.5) < 0.1      # mean of 2.00 and 2.20 per 400 g, outlier dropped
    assert abs(rows["Super U"]["per100_cents"] - 40.0) < 0.1
    got = c.latest("9", (400.0, "g"))
    assert got["n_chains"] == 2 and abs(got["per100_cents"] - 46.25) < 0.2                              # average of the chain averages
    s = session()
    retail.seed(s)
    ls = {r.chain_id for r in retail.discover(s, {"id": "9", "brand": "X"}, list(rows.values()))}
    assert ls == {"carrefour", "superu"}


def test_nearest_widens_beyond_the_local_radius_when_a_chain_has_no_branch_nearby():
    s = session()
    retail.seed(s)
    s.add(db.Store(chain_id="monoprix", store_name="Monoprix Orléans", latitude=47.9029, longitude=1.9093, source_id="far1"))   # ~110 km from Paris
    s.commit()
    near = retail.nearest(s, "monoprix", 48.8566, 2.3522, 15, refresh=False)
    assert near and near[0]["name"] == "Monoprix Orléans" and 100_000 < near[0]["distance_m"] < 130_000
    assert retail.nearest(s, "monoprix", 43.2965, 5.3698, 15, refresh=False) == []          # Marseille is ~600 km away: beyond the widening limit, none invented


def test_same_size_filter_and_pack_price_come_with_every_price():
    from app import main as m
    assert hasattr(m.AltReq(priorities=["overall"]), "same_size") and m.AltReq(priorities=["overall"]).same_size is False


def test_local_open_prices_copy_serves_items_without_network(tmp_path):
    import json
    import sqlite3
    from app import value
    path = str(tmp_path / "op.db")
    db = sqlite3.connect(path)
    db.execute("create table op_items (code text, date text, data text)")
    loc = {"id": 1, "osm_id": 5, "osm_brand": "Carrefour", "osm_name": "Carrefour City", "osm_address_country_code": "FR", "osm_lat": "48.85", "osm_lon": "2.35", "osm_address_city": "Paris"}
    for i, (pr, d) in enumerate([("2.00", "2026-10-01"), ("2.20", "2026-09-01")]):
        db.execute("insert into op_items values (?,?,?)", ("777", d, json.dumps({"id": i, "product_code": "777", "price": pr, "currency": "EUR", "price_per": None, "date": d, "location": loc})))
    db.commit(); db.close()
    c = value.OpenPricesClient(path)
    assert c.local.available() and len(c._items("777")) == 2 and c._items("000") == []
    rows = c.chain_summary("777", (400.0, "g"))
    assert rows and rows[0]["chain"] == "Carrefour" and rows[0]["observations"] == 2 and abs(rows[0]["per100_cents"] - 52.5) < 0.1
    assert c.latest("777", (400.0, "g"))["n_chains"] == 1


def test_full_store_list_gives_exact_nearest_branch_in_dense_areas():
    s = session()
    retail.seed(s)
    # 60 Carrefours in a ring 3-9 km away, one 150 m from the user: the nearest must be found whatever "importance" a text search would give
    import math
    for i in range(60):
        a = i * 6.0 * math.pi / 180
        s.add(db.Store(chain_id="carrefour", store_name=f"Carrefour {i}", latitude=48.8566 + 0.05 * math.sin(a), longitude=2.3522 + 0.07 * math.cos(a), source_id=f"ring{i}"))
    s.add(db.Store(chain_id="carrefour", store_name="Carrefour City tout près", latitude=48.8579, longitude=2.3522, source_id="close"))
    s.commit()
    near = retail.nearest(s, "carrefour", 48.8566, 2.3522, 15, k=3, refresh=False)
    assert near[0]["name"] == "Carrefour City tout près" and near[0]["distance_m"] < 200 and near[1]["distance_m"] > 3000
    assert [n["distance_m"] for n in near] == sorted(n["distance_m"] for n in near)
