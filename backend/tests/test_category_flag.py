from fastapi.testclient import TestClient

from app import db, main


def test_category_flag_is_stored_once_per_person_and_product(monkeypatch):
    monkeypatch.setattr(main, "load_product", lambda s, b, refresh=False: {"id": "P1", "barcode": b, "name": "Purée d'amandes", "brand": None, "categories": []})
    c = TestClient(main.app)
    H = {"X-Session-Id": "flag-test-0001", "X-Country": "FR"}
    assert c.post("/v1/products/123/category-flag", json={"suggested_type": "P0658"}, headers=H).json() == {"ok": True}
    assert c.post("/v1/products/123/category-flag", json={}, headers=H).status_code == 200   # a second flag updates the first
    assert c.post("/v1/products/123/category-flag", json={"suggested_type": "nope"}, headers=H).status_code == 422
    s = main.app.state.sessions()
    try:
        rows = s.query(db.CategoryFlag).filter_by(user_id="flag-test-0001").all()
        assert len(rows) == 1 and rows[0].placed_type and rows[0].suggested_type is None
    finally:
        s.close()
