"""
Simple login.

There is one admin account (username/password from the .env file). After a
successful login the server returns a token. The browser sends this token in
the `Authorization: Bearer <token>` header with every request.

The token is an HMAC signature of the username and an expiry time, so the
server can check it without storing anything. This is a simplified version of
how JSON Web Tokens (JWT) work.
"""

import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config

TOKEN_LIFETIME_SECONDS = 12 * 60 * 60  # 12 hours

bearer_scheme = HTTPBearer(auto_error=False)


def _sign(payload: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(username: str) -> str:
    expires_at = int(time.time()) + TOKEN_LIFETIME_SECONDS
    payload = f"{username}:{expires_at}"
    return f"{payload}:{_sign(payload)}"


def verify_token(token: str) -> str | None:
    """Return the username if the token is valid, otherwise None."""
    try:
        username, expires_at, signature = token.rsplit(":", 2)
    except ValueError:
        return None
    payload = f"{username}:{expires_at}"
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    if not expires_at.isdigit() or int(expires_at) < time.time():
        return None
    return username


def check_credentials(username: str, password: str) -> bool:
    # compare_digest avoids leaking information through timing differences
    return hmac.compare_digest(username, config.ADMIN_USERNAME) and hmac.compare_digest(
        password, config.ADMIN_PASSWORD
    )


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    """FastAPI dependency that protects an endpoint."""
    username = verify_token(credentials.credentials) if credentials else None
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in again")
    return username
