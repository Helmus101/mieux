import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402

from app import db, main  # noqa: E402
from test_all import FakeOFF  # noqa: E402

URL = "https://example.supabase.co"
SECRET = "unit-test-secret-unit-test-secret-1234"
main.app.state.off = FakeOFF()
c = TestClient(main.app)


def account_headers(sub="acct-1"):
    tok = jwt.encode({"sub": sub, "email": "a@b.fr", "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")
    return {"Authorization": "Bearer " + tok, "X-Lang": "en"}


def rows(model, **kw):
    with main.app.state.sessions() as s:
        return s.query(model).filter_by(**kw).all()


def setup_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)


def test_account_stores_no_scans_server_side(monkeypatch):
    setup_env(monkeypatch)
    h = account_headers("acct-scan")
    assert c.post("/v1/scans", json={"barcode": "1"}, headers=h).status_code == 200
    assert c.post("/v1/scans", json={"barcode": "2"}, headers=h).status_code == 200
    assert c.get("/v1/scans", headers=h).json() == {"scans": []}
    assert rows(db.Scan, user_id="acct-scan") == []


def test_account_saves_no_profile_or_preferences(monkeypatch):
    setup_env(monkeypatch)
    h = account_headers("acct-prof")
    c.post("/v1/scans", json={"barcode": "1"}, headers=h)  # creates the account row
    body = {"diet": "vegan", "priorities": ["protein"], "allergens": ["milk"]}
    assert c.put("/v1/me/preferences", json=body, headers=h).json() == body
    c.put("/v1/me/profile", json={"name": "Lea", "city": "Paris", "postcode": "75011", "platform": "web"}, headers=h)
    assert rows(db.Preference, user_id="acct-prof") == []
    u = rows(db.User, id="acct-prof")[0]
    assert (u.name, u.city, u.postcode) == (None, None, None)


def test_restrictions_travel_with_each_request(monkeypatch):
    setup_env(monkeypatch)
    h = account_headers("acct-fit")
    c.post("/v1/scans", json={"barcode": "1"}, headers=h)
    plain = c.get("/v1/products/1", headers=h).json()["fit"]
    assert not [f for f in plain if f["priority"].startswith("allergen:")]
    sent = {**h, "X-Prefs": urllib.parse.quote(json.dumps({"diet": "omnivore", "priorities": [], "allergens": ["milk"]}))}
    fit = c.get("/v1/products/1", headers=sent).json()["fit"]
    assert [f["status"] for f in fit if f["priority"] == "allergen:milk"] == ["conflict"]


def test_anonymous_sessions_behave_as_before():
    h = {"X-Session-Id": "anon-session-keep-1"}
    body = {"diet": "omnivore", "priorities": ["protein"], "allergens": []}
    c.put("/v1/me/preferences", json=body, headers=h)
    c.post("/v1/scans", json={"barcode": "1"}, headers=h)
    assert len(rows(db.Preference, user_id="anon-session-keep-1")) == 1
    assert len(rows(db.Scan, user_id="anon-session-keep-1")) == 1


def test_unverifiable_token_falls_back_to_the_anonymous_session(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    tok = jwt.encode({"sub": "x", "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 600}, SECRET, algorithm="HS256")
    assert c.get("/v1/products/1", headers={"Authorization": "Bearer " + tok}).status_code == 401
    assert c.get("/v1/products/1", headers={"Authorization": "Bearer " + tok, "X-Session-Id": "fallback-session-1"}).status_code == 200



def test_lookup_failure_is_retryable_not_not_found():
    from app.off import OFFError

    class Down(FakeOFF):
        def get_product(self, barcode):
            raise OFFError("down")

    real = main.app.state.off
    main.app.state.off = Down()
    try:
        r = c.get("/v1/products/3017620422003", headers={"X-Session-Id": "session-down-001"})
        assert r.status_code == 503
    finally:
        main.app.state.off = real
    assert c.get("/v1/products/3017620422003", headers={"X-Session-Id": "session-down-001"}).headers["x-content-type-options"] == "nosniff"


def test_non_food_barcode_is_a_clear_404_not_a_server_error():
    from app.off import NotFoodError

    class Book(FakeOFF):
        def get_product(self, barcode):
            raise NotFoodError(barcode)

    real = main.app.state.off
    main.app.state.off = Book()
    try:
        r = c.get("/v1/products/9782070612758", headers={"X-Session-Id": "session-book-001"})
        assert r.status_code == 404 and r.json()["detail"] == "not_food"
    finally:
        main.app.state.off = real


def test_off_json_404_is_an_answer_not_a_failure(monkeypatch):
    import app.off as off

    class R:
        status_code = 404
        text = '{"code":"9782070612758","status":0,"status_verbose":"product found with a different product type: product"}'
        headers = {}
        def json(self):
            import json
            return json.loads(self.text)

    calls = []
    monkeypatch.setattr(off.httpx, "get", lambda *a, **k: calls.append(1) or R())
    client = off.OFFClient.__new__(off.OFFClient)
    client.__init__()
    client.local = type("L", (), {"product": lambda self, b: None})()
    try:
        client.get_product("9782070612758")
        assert False, "expected NotFoodError"
    except off.NotFoodError:
        pass
    assert len(calls) == 1  # no retries: it was a real answer
