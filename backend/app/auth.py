"""Local authentication module for Mieux using JWT tokens."""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from . import supabase_auth

# JWT Configuration
# CRITICAL: JWT_SECRET_KEY must be set in production with a strong random value
# Generate with: openssl rand -base64 32
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable must be set")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60  # 7 days (reduced from 30 for better security)


def create_access_token(data: dict) -> str:
    """Create a JWT access token.

    Args:
        data: The data to encode in the token (typically user_id)

    Returns:
        The encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded token data

    Raises:
        JWTError: If the token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")


def get_user(authorization: Optional[str] = Header(None)) -> dict:
    """Validate JWT token and return user info.

    This is used for authenticated endpoints. The token should be passed
    in the Authorization header as "Bearer <token>".

    Args:
        authorization: The Authorization header value

    Returns:
        The user object (decoded from token)

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(401, "Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header format")

    token = authorization.replace("Bearer ", "")

    sb = supabase_auth.verify(token)
    if sb:
        return sb
    if supabase_auth.is_supabase_token(token):
        raise HTTPException(401, "Invalid Supabase token")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token: no user_id")
        return {"id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")


def get_user_or_anonymous(
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None)
) -> tuple[Optional[dict], Optional[str]]:
    """Get user from JWT token or fall back to anonymous session ID.

    This is used for endpoints that support both authenticated and anonymous users.
    Returns a tuple of (user_dict, session_id).

    Args:
        authorization: The Authorization header value
        x_session_id: The X-Session-Id header value

    Returns:
        Tuple of (user, session_id). If authenticated, user is set and session_id is None.
        If anonymous, user is None and session_id is set.
    """
    if authorization:
        try:
            user = get_user(authorization)
            return user, None
        except HTTPException:
            pass  # Fall back to anonymous

    if x_session_id and len(x_session_id) >= 8:
        return None, x_session_id

    raise HTTPException(401, "Either valid authorization token or X-Session-Id header required")
