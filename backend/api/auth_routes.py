"""Signup/login/me endpoints. Included into the main app in api/routes.py."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth.security import create_token, get_current_user_id, hash_password, verify_password
from db.importer import get_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class TokenResponse(BaseModel):
    token: str
    email: str


def _connect():
    return get_connection()


@router.post("/signup", response_model=TokenResponse)
def signup(creds: Credentials):
    conn = _connect()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (creds.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    cur = conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
        (creds.email, hash_password(creds.password), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return TokenResponse(token=create_token(user_id), email=creds.email)


@router.post("/login", response_model=TokenResponse)
def login(creds: Credentials):
    conn = _connect()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = ?", (creds.email,)
    ).fetchone()
    conn.close()
    if row is None or not verify_password(creds.password, row[1]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(token=create_token(row[0]), email=creds.email)


@router.get("/me")
def me(user_id: int = Depends(get_current_user_id)):
    conn = _connect()
    row = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return {"email": row[0]}
