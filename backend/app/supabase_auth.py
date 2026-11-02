"""Verify Supabase Auth access tokens. Supabase is used only to sign people in; everything else stays in this API.

Set SUPABASE_URL (e.g. https://xxxx.supabase.co). New projects sign with asymmetric keys (verified through the project's JWKS);
legacy projects sign with HS256, in which case also set SUPABASE_JWT_SECRET."""
import os
import time
from typing import Any, Dict, Optional

import httpx
from jose import JWTError, jwt

_JWKS: Dict[str, Any] = {"keys": [], "at": 0.0}
_TTL = 3600


def _url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def enabled() -> bool:
    return bool(_url())


def _jwks(force: bool = False) -> list:
    if force or not _JWKS["keys"] or time.time() - _JWKS["at"] > _TTL:
        r = httpx.get(f"{_url()}/auth/v1/.well-known/jwks.json", timeout=5)
        r.raise_for_status()
        _JWKS["keys"], _JWKS["at"] = r.json().get("keys", []), time.time()
    return _JWKS["keys"]


def is_supabase_token(token: str) -> bool:
    if not enabled():
        return False
    try:
        return str(jwt.get_unverified_claims(token).get("iss", "")).startswith(_url())
    except JWTError:
        return False


def verify(token: str) -> Optional[Dict[str, Any]]:
    """The signed-in user ({'id', 'supabase_id', 'email'}) or None when the token is not a valid Supabase token."""
    if not is_supabase_token(token):
        return None
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "")
        if alg == "HS256":
            secret = os.getenv("SUPABASE_JWT_SECRET")
            if not secret:
                return None
            key: Any = secret
        else:
            kid = header.get("kid")
            key = next((k for k in _jwks() if k.get("kid") == kid), None) or next((k for k in _jwks(True) if k.get("kid") == kid), None)
            if not key:
                return None
        claims = jwt.decode(token, key, algorithms=[alg], audience="authenticated", issuer=f"{_url()}/auth/v1")
    except (JWTError, httpx.HTTPError, ValueError):
        return None
    sub = claims.get("sub")
    return {"id": sub, "supabase_id": sub, "email": claims.get("email")} if sub else None
