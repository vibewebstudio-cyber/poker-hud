"""Password hashing and JWT issuing/verification.

JWT rather than session cookies: the frontend and backend are meant to
live on different origins once hosted (Cloudflare Pages + Fly.io), and
a bearer token in an Authorization header sidesteps cross-origin
cookie/SameSite configuration entirely. The tradeoff is that the token
lives in the frontend's localStorage rather than an httpOnly cookie,
which is more exposed to XSS — acceptable here since there's no
third-party script surface on the frontend, but worth knowing if that
ever changes.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Header, HTTPException

# Falls back to a fixed dev secret so local development works without
# extra setup; any real deployment MUST set a real JWT_SECRET env var,
# since anyone who knows this default could forge tokens.
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(days=30)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def get_current_user_id(authorization: str | None = Header(default=None)) -> int:
    """FastAPI dependency: extracts and validates the bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id
