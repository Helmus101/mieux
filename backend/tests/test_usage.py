import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app import db, main  # noqa: E402

c = TestClient(main.app)


def stats() -> dict:
    r = c.get("/v1/usage/stats")
    assert r.status_code == 200
    return r.json()


def test_a_refresh_is_not_a_new_person():
    before = stats()
    h = {"user-agent": "pytest-visitor-one"}
    assert c.post("/v1/usage/visit", json={"surface": "landing"}, headers=h).status_code == 200
    assert c.post("/v1/usage/visit", json={"surface": "landing"}, headers=h).status_code == 200
    main.visit_batcher.flush()  # Flush batch queue before stats query
    after = stats()
    assert after["landing_views"] == before["landing_views"] + 1
    assert after["visitors"] == before["visitors"] + 1
    assert after["today"]["landing_views"] == before["today"]["landing_views"] + 1


def test_opening_the_app_is_counted_too():
    before = stats()
    h = {"user-agent": "pytest-visitor-one"}
    assert c.post("/v1/usage/visit", json={"surface": "app"}, headers=h).status_code == 200
    main.visit_batcher.flush()  # Flush batch queue before stats query
    after = stats()
    assert after["app_opens"] == before["app_opens"] + 1
    assert after["app_visitors"] == before["app_visitors"] + 1
    assert after["visitors"] == before["visitors"]          # same person, already counted


def test_two_browsers_are_two_people():
    before = stats()["visitors"]
    c.post("/v1/usage/visit", json={"surface": "landing"}, headers={"user-agent": "pytest-visitor-two"})
    c.post("/v1/usage/visit", json={"surface": "landing"}, headers={"user-agent": "pytest-visitor-three"})
    main.visit_batcher.flush()  # Flush batch queue before stats query
    assert stats()["visitors"] == before + 2


def test_unknown_surface_is_rejected():
    assert c.post("/v1/usage/visit", json={"surface": "admin"}).status_code == 422


def test_only_a_daily_hash_is_stored():
    main.visit_batcher.flush()  # Flush batch queue before database query
    with main.app.state.sessions() as s:
        rows = s.query(db.Visit).all()
    assert rows
    for r in rows:
        assert len(r.visitor) == 32
        assert "pytest-visitor" not in r.visitor
        assert r.surface in ("landing", "app")
        assert len(r.day) == 10
