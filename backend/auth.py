"""Password hashing and signed session tokens."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from pathlib import Path
from typing import Optional

import bcrypt
from dotenv import load_dotenv
from fastapi import Header, HTTPException

from db import get_db

load_dotenv(Path(__file__).resolve().parent / ".env")

TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]{3,30}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt only uses the first 72 bytes

_secret = os.getenv("SECRET_KEY")
if not _secret:
    _secret = secrets.token_hex(32)
    print("SECRET_KEY not set; using a temporary key (sign-ins reset on restart).")
SECRET_KEY = _secret.encode()

# Compared against when a username doesn't exist, so response time doesn't reveal it
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt())


def validate_credentials(username: str, password: str) -> Optional[str]:
    """Return an error message if the username or password is not allowed."""
    if not USERNAME_PATTERN.match(username):
        return "Username must be 3-30 characters: letters, numbers, dots, dashes, or underscores."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "Password is too long."
    return None


def hash_password(password: str) -> str:
    """bcrypt hash; the salt is stored inside the returned string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    if password_hash is None:
        bcrypt.checkpw(encoded, _DUMMY_HASH)
        return False
    return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()


def create_token(user_id: int) -> str:
    """Token format: '<user_id>.<expires_at>.<signature>'."""
    payload = f"{user_id}.{int(time.time()) + TOKEN_TTL_SECONDS}"
    return f"{payload}.{_sign(payload)}"


def read_token(token: str) -> Optional[int]:
    """Return the user id if the token is authentic and unexpired."""
    try:
        user_id, expires_at, signature = token.split(".")
        payload = f"{user_id}.{expires_at}"
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        if int(expires_at) < time.time():
            return None
        return int(user_id)
    except ValueError:
        return None


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """FastAPI dependency: the signed-in user, or a 401 error."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Please sign in.")

    user_id = read_token(authorization.removeprefix("Bearer ").strip())
    if user_id is None:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Please sign in.")

    return {"id": row["id"], "username": row["username"]}
