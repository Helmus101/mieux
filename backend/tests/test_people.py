import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402

c = TestClient(main.app)
H = {"X-Session-Id": "people-user-001"}


def test_profile_is_saved_and_given_back():
    r = c.put("/v1/me/profile", headers=H, json={"name": "Willem", "city": "Paris", "postcode": "75011", "platform": "web"})
    assert r.status_code == 200
    got = c.get("/v1/me/profile", headers=H).json()
    assert (got["name"], got["city"], got["postcode"], got["platform"]) == ("Willem", "Paris", "75011", "web")
    assert got["first_seen"] and got["last_seen"]


def test_saving_again_updates_the_same_person():
    c.put("/v1/me/profile", headers=H, json={"name": "Willem", "city": "Lyon"})
    got = c.get("/v1/me/profile", headers=H).json()
    assert got["city"] == "Lyon" and got["name"] == "Willem"
    assert c.get("/v1/people", headers={"X-Admin-Key": "unset"}).status_code == 404   # no ADMIN_KEY: closed


def test_blank_name_is_stored_as_nothing():
    c.put("/v1/me/profile", headers=H, json={"name": "   ", "city": "Lyon"})
    assert c.get("/v1/me/profile", headers=H).json()["name"] is None


def test_people_list_needs_the_admin_key(monkeypatch):
    assert c.get("/v1/people").status_code == 404
    monkeypatch.setenv("ADMIN_KEY", "s3cret-admin")
    assert c.get("/v1/people").status_code == 404                        # key not sent
    assert c.get("/v1/people", headers={"X-Admin-Key": "wrong"}).status_code == 404
    c.put("/v1/me/profile", headers=H, json={"name": "Willem", "city": "Lyon"})
    r = c.get("/v1/people", headers={"X-Admin-Key": "s3cret-admin"}).json()
    assert r["total_users"] >= 1 and r["with_name"] >= 1
    assert any(p["name"] == "Willem" and p["city"] == "Lyon" for p in r["people"])


def test_erasing_removes_the_person():
    assert c.delete("/v1/me", headers=H).status_code == 200
    got = c.get("/v1/me/profile", headers=H).json()
    assert got["name"] is None and got["city"] is None
