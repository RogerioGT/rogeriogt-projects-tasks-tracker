"""FastAPI dependencies: current-user resolution.

Two modes:
- Local (default): no login required. Falls back to a "local" pseudo-user so
  localhost stays frictionless.
- Required (REQUIRE_AUTH=true): every request needs a valid Bearer token;
  otherwise a 401 is raised and the frontend shows the login screen.
"""
import os

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import verify_token

REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() in ("1", "true", "yes")

LOCAL_USER_ID = "00000000-0000-0000-0000-000000000000"
LOCAL_USER_EMAIL = "local@rogeriogt"


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the acting user.

    Bearer token wins. In local mode, fall back to the local pseudo-user.
    In required mode, reject anonymous requests with 401.
    """
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        user_id = verify_token(token)
        if user_id:
            user = db.get(User, user_id)
            if user and user.is_active:
                return user

    if REQUIRE_AUTH:
        raise HTTPException(401, "login required")

    # Local mode: fall back to the local pseudo-user (ensure it exists).
    local = db.get(User, LOCAL_USER_ID)
    if local is None:
        local = User(
            id=LOCAL_USER_ID,
            email=LOCAL_USER_EMAIL,
            name="Local",
            locale="en",
        )
        db.add(local)
        db.commit()
        db.refresh(local)
    return local


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Require the acting user to be an admin (403 otherwise)."""
    if not REQUIRE_AUTH or user.is_admin or user.email == LOCAL_USER_EMAIL:
        return user
    raise HTTPException(403, "admin required")


def is_local_mode() -> bool:
    """True when running without mandatory auth (localhost / dev)."""
    return not REQUIRE_AUTH
