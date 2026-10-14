"""
Purpose: Issue and verify JWT access tokens for the single admin
account. There is no User table — the admin's username and password
hash are read from environment variables (ADMIN_USERNAME,
ADMIN_PASSWORD_HASH), since there is currently no user management CRUD.
Tokens are stateless: verification relies entirely on the signature and
expiry embedded in the token itself (signed with the app's SECRET_KEY),
not on a server-side session store.
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from werkzeug.security import check_password_hash

TOKEN_EXPIRY_HOURS = 24  # Tokens are valid for 24 hours


def verify_admin_credentials(username: str, password: str) -> bool:
    expected_username = os.environ.get("ADMIN_USERNAME")
    expected_hash = os.environ.get("ADMIN_PASSWORD_HASH")

    if not expected_username or not expected_hash:
        return False

    if username != expected_username:
        return False

    return check_password_hash(expected_hash, password)


def generate_token(username: str, secret_key: str) -> str:
    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_token(token: str, secret_key: str) -> dict:
    """Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError if the
    token is expired or has been tampered with."""
    return jwt.decode(token, secret_key, algorithms=["HS256"])