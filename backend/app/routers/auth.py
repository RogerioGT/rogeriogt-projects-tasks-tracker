"""Auth router: register, login, me, list users, bootstrap admin."""
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import REQUIRE_AUTH, get_current_admin, get_current_user
from ..models import User
from ..schemas import (
    AuthResponse,
    ChangePasswordIn,
    LoginIn,
    RegisterIn,
    UserCreateIn,
    UserOut,
    UserSelfUpdateIn,
    UserUpdateIn,
)
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _email_taken(db: Session, email: str, exclude_user_id: str | None = None) -> bool:
    q = select(User).where(User.email == email)
    if exclude_user_id:
        q = q.where(User.id != exclude_user_id)
    return db.scalars(q).first() is not None


def _valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1] and len(email) <= 255


def bootstrap_admin(db: Session) -> None:
    """Ensure the admin account exists and has the admin role.

    Creates it from env vars if no password-bearing user exists, and promotes
    the ADMIN_EMAIL user on every startup (covers upgrades where is_admin
    was added after the account was created).
    """
    email = os.environ.get("ADMIN_EMAIL", "admin@rogeriogt.com").strip().lower()
    existing = db.scalars(select(User).where(User.email == email)).first()
    if existing is not None:
        if not existing.is_admin:
            existing.is_admin = True
            db.commit()
        return
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        return  # nothing to do until credentials are supplied
    db.add(User(
        email=email,
        name=os.environ.get("ADMIN_NAME", "Admin"),
        password_hash=hash_password(password),
        is_admin=True,
    ))
    db.commit()


@router.get("/required")
def auth_required():
    return {"required": REQUIRE_AUTH}


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if REQUIRE_AUTH:
        raise HTTPException(403, "registration is closed; contact the admin")
    email = payload.email.strip().lower()
    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(409, "email already registered")
    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=create_token(user.id), user=user)


# Simple in-memory login rate limiter: max 10 attempts per 15 min per IP+email.
# Good enough for a small single-server deployment; swap for Redis if it grows.
import threading
import time as _time

_login_attempts: dict[str, list[float]] = {}
_login_lock = threading.Lock()

LOGIN_MAX_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 15 * 60


def _login_blocked(key: str) -> bool:
    now = _time.time()
    with _login_lock:
        attempts = [t for t in _login_attempts.get(key, []) if now - t < LOGIN_WINDOW_SECONDS]
        _login_attempts[key] = attempts
        return len(attempts) >= LOGIN_MAX_ATTEMPTS


def _record_failed_login(key: str) -> None:
    with _login_lock:
        _login_attempts.setdefault(key, []).append(_time.time())


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{email}"
    if _login_blocked(key):
        raise HTTPException(429, "too many attempts; try again later")
    user = db.scalars(select(User).where(User.email == email)).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        _record_failed_login(key)
        raise HTTPException(401, "invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "account disabled")
    return AuthResponse(token=create_token(user.id), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Users list. Admins see everyone (incl. deactivated); regular users only
    see active accounts (the share dialog needs the list)."""
    q = select(User)
    if not user.is_admin:
        q = q.where(User.is_active.is_(True))
    return db.scalars(q.order_by(User.name, User.email)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def admin_create_user(
    payload: UserCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Admin creates a user account (registration is closed in prod mode)."""
    email = payload.email.strip().lower()
    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(409, "email already registered")
    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        phone=payload.phone.strip() if payload.phone else None,
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: str,
    payload: UserUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    if user.id == admin.id and payload.is_admin is False:
        raise HTTPException(400, "you cannot remove your own admin role")
    if payload.email is not None:
        email = payload.email.strip().lower()
        if not _valid_email(email):
            raise HTTPException(400, "invalid email address")
        if _email_taken(db, email, exclude_user_id=user.id):
            raise HTTPException(409, "email already registered")
        user.email = email
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip() or None
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserSelfUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """A user edits their own profile: name, email, phone."""
    if payload.email is not None:
        email = payload.email.strip().lower()
        if not _valid_email(email):
            raise HTTPException(400, "invalid email address")
        if _email_taken(db, email, exclude_user_id=user.id):
            raise HTTPException(409, "email already registered")
        user.email = email
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip() or None
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.password_hash or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(401, "current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
