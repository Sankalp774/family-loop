from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Cookie, HTTPException, Response

from app.config import USERS

_SESSIONS: dict[str, dict] = {}


def login(email: str, password: str) -> dict:
    user = USERS.get(email.strip().lower())
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Unknown door or wrong key.")
    return {
        "email": email.strip().lower(),
        "name": user["name"],
        "role": user["role"],
        "kid": user["kid"],
    }


def start_session(response: Response, user: dict) -> str:
    token = secrets.token_urlsafe(24)
    _SESSIONS[token] = user
    response.set_cookie(
        "family_loop",
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return token


def clear_session(response: Response, token: str | None) -> None:
    if token:
        _SESSIONS.pop(token, None)
    response.delete_cookie("family_loop")


def current_user(family_loop: Annotated[str | None, Cookie()] = None) -> dict:
    if not family_loop or family_loop not in _SESSIONS:
        raise HTTPException(status_code=401, detail="Pick a door first.")
    return _SESSIONS[family_loop]


def require_parent(user: dict) -> dict:
    if user.get("role") != "parent":
        raise HTTPException(status_code=403, detail="Child cannot change rules or approve themselves.")
    return user


def require_child(user: dict) -> dict:
    if user.get("role") != "child":
        raise HTTPException(
            status_code=403,
            detail="This paste has to come from the child door. Parent may file it only if the child will not.",
        )
    return user
