import os
from fastapi.testclient import TestClient
from app.main import app

H = {"X-Session-Id": "news-session-1", "X-Country": "FR", "X-Lang": "fr"}


def test_newsletter_needs_consent_valid_email_and_saves_once(monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "k-test")
    c = TestClient(app)
    assert c.post("/v1/newsletter", headers=H, json={"email": "a@b.fr", "consent": False}).status_code == 422
    assert c.post("/v1/newsletter", headers=H, json={"email": "nope", "consent": True}).status_code == 422
    for _ in range(2):
        assert c.post("/v1/newsletter", headers=H, json={"email": " Test.News@Example.com ", "consent": True}).status_code == 200
    assert c.get("/v1/newsletter/subscribers").status_code == 404
    r = c.get("/v1/newsletter/subscribers", headers={"X-Admin-Key": "k-test"}).json()
    assert [x["email"] for x in r["subscribers"]].count("test.news@example.com") == 1
    assert c.delete("/v1/newsletter", params={"email": "test.news@example.com"}).status_code == 200
    r = c.get("/v1/newsletter/subscribers", headers={"X-Admin-Key": "k-test"}).json()
    assert "test.news@example.com" not in [x["email"] for x in r["subscribers"]]


def test_supabase_sync_sends_the_row_and_survives_failures(monkeypatch):
    from app import supabase_sync as sb
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    assert sb.push_subscriber("a@b.fr", "fr", "FR") is False   # not configured: does nothing
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_x")
    seen = {}
    def ok(method, url, headers, data):
        seen.update(method=method, url=url, headers=headers, data=data); return 201
    assert sb.push_subscriber("a@b.fr", "fr", "FR", transport=ok) is True
    assert seen["url"] == "https://x.supabase.co/rest/v1/subscribers" and seen["method"] == "POST"
    assert seen["headers"]["apikey"] == "sb_publishable_x" and "Authorization" not in seen["headers"] and b"a@b.fr" in seen["data"]
    assert seen["headers"]["Prefer"] == "return=minimal"
    import urllib.error
    def dup(*a, **k): raise urllib.error.HTTPError("u", 409, "dup", {}, None)
    assert sb.push_subscriber("a@b.fr", "fr", "FR", transport=dup) is True   # already subscribed
    def boom(*a, **k): raise OSError("down")
    assert sb.push_subscriber("a@b.fr", "fr", "FR", transport=boom) is False
    assert sb.delete_subscriber("a+b@c.fr", transport=ok) is True and seen["url"].endswith("email=eq.a%2Bb%40c.fr")



def test_push_scan_is_anonymous(monkeypatch):
    from app import supabase_sync
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_x")
    seen = []
    assert supabase_sync.push_scan("123", "FR", transport=lambda m, u, h, d: seen.append((m, u, d)) or 201)
    assert seen[0][1].endswith("/rest/v1/scan_events") and b"user" not in seen[0][2]
