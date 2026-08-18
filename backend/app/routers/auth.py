"""Auth router: register, login, me, list users, bootstrap admin."""
import os

from fastapi import APIRouter, Depends, HTTPException
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
    UserUpdateIn,
)
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


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


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalars(select(User).where(User.email == email)).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "account disabled")
    return AuthResponse(token=create_token(user.id), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.name, User.email)).all()


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
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
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
