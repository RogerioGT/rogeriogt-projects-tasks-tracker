"""FastAPI dependencies: optional current-user resolution.

The app runs single-user by default with no login (a "local" pseudo-user).
If an Authorization: Bearer token is present and valid, resolve the real user;
otherwise fall back to the local user so localhost stays frictionless.
"""
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import verify_token

LOCAL_USER_ID = "00000000-0000-0000-0000-000000000000"
LOCAL_USER_EMAIL = "local@rogeriogt"


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the acting user. Bearer token wins; else the local pseudo-user."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        user_id = verify_token(token)
        if user_id:
            user = db.get(User, user_id)
            if user and user.is_active:
                return user

    # Fall back to the local pseudo-user (ensure it exists).
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
