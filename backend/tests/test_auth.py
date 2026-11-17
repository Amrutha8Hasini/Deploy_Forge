"""Tests for the simple token login."""

import time

from app import auth


def test_valid_token():
    token = auth.create_token("admin")
    assert auth.verify_token(token) == "admin"


def test_tampered_token_is_rejected():
    token = auth.create_token("admin")
    username, expires, signature = token.split(":")
    assert auth.verify_token(f"hacker:{expires}:{signature}") is None
    assert auth.verify_token("garbage") is None


def test_expired_token_is_rejected(monkeypatch):
    token = auth.create_token("admin")
    monkeypatch.setattr(time, "time", lambda: 10**12)  # far in the future
    assert auth.verify_token(token) is None
