import time

from jose import jwt

from app import auth, supabase_auth

URL = "https://example.supabase.co"
SECRET = "unit-test-secret-unit-test-secret-1234"


def _token(**over):
    claims = {"sub": "user-uuid-1", "email": "a@b.fr", "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 600}
    claims.update(over)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_valid_supabase_token_is_accepted(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    user = auth.get_user("Bearer " + _token())
    assert user == {"id": "user-uuid-1", "supabase_id": "user-uuid-1", "email": "a@b.fr"}


def test_wrong_audience_or_expired_token_is_rejected(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    for bad in (_token(aud="other"), _token(exp=int(time.time()) - 5)):
        assert supabase_auth.verify(bad) is None


def test_disabled_without_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    assert supabase_auth.verify(_token()) is None


def test_local_tokens_still_work(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    token = auth.create_access_token({"sub": "local-user"})
    assert auth.get_user("Bearer " + token) == {"id": "local-user"}
