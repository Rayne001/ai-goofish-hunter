"""Small in-memory sessions for the single-admin web UI.

Sessions intentionally do not survive process restarts; the app runs as one
worker, so logout revocation is immediate without a database migration.
"""

from __future__ import annotations

import hashlib
import secrets
import time

SESSION_COOKIE_NAME = "goofish_session"
SESSION_TTL_SECONDS = 12 * 60 * 60

# This process-local store assumes the current single-worker Compose deployment.
_sessions: dict[str, tuple[str, int]] = {}


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _purge_expired(now: int) -> None:
    expired = [key for key, (_, expires_at) in _sessions.items() if expires_at <= now]
    for key in expired:
        _sessions.pop(key, None)


def create_session(
    username: str,
    *,
    now: int | None = None,
    ttl_seconds: int = SESSION_TTL_SECONDS,
) -> tuple[str, int]:
    current_time = int(time.time()) if now is None else int(now)
    _purge_expired(current_time)
    token = secrets.token_urlsafe(32)
    expires_at = current_time + max(1, int(ttl_seconds))
    _sessions[_token_key(token)] = (username, expires_at)
    return token, expires_at


def get_session_user(
    token: str | None,
    *,
    now: int | None = None,
    expected_username: str | None = None,
) -> str | None:
    if not token:
        return None

    current_time = int(time.time()) if now is None else int(now)
    key = _token_key(token)
    session = _sessions.get(key)
    if session is None:
        return None

    username, expires_at = session
    if expires_at <= current_time or (
        expected_username is not None and username != expected_username
    ):
        _sessions.pop(key, None)
        return None
    return username


def revoke_session(token: str | None) -> None:
    if token:
        _sessions.pop(_token_key(token), None)
