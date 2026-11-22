"""Single-admin login endpoints backed by a short-lived server session."""

import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from src.auth.session_store import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    create_session,
    get_session_user,
    revoke_session,
)
from src.infrastructure.config.settings import settings as app_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _credentials_configured() -> bool:
    return bool(
        app_settings.web_username
        and len(app_settings.web_password) >= 12
        and app_settings.web_password != "admin123"
    )


@router.post("/login")
@router.post("/status", include_in_schema=False)
async def login(payload: LoginRequest, response: Response):
    """Validate the single administrator and set an HttpOnly session cookie."""
    if not _credentials_configured():
        raise HTTPException(status_code=503, detail="请先配置 WEB_USERNAME 和强密码 WEB_PASSWORD")

    username_matches = hmac.compare_digest(
        payload.username.encode("utf-8"), app_settings.web_username.encode("utf-8")
    )
    password_matches = hmac.compare_digest(
        payload.password.encode("utf-8"), app_settings.web_password.encode("utf-8")
    )
    if not (username_matches and password_matches):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    token, _ = create_session(app_settings.web_username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return {"authenticated": True, "username": app_settings.web_username}


@router.get("/session")
async def get_session(request: Request):
    """Return the current browser session state without exposing its token."""
    username = get_session_user(
        request.cookies.get(SESSION_COOKIE_NAME),
        expected_username=app_settings.web_username,
    )
    if not username:
        return {"authenticated": False, "username": None}
    return {"authenticated": True, "username": username}


@router.post("/logout", status_code=204)
async def logout(request: Request):
    """Revoke this browser's server-side session and clear its cookie."""
    revoke_session(request.cookies.get(SESSION_COOKIE_NAME))
    response = Response(status_code=204)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return response
