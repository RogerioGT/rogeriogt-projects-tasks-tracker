"""Auth router: register, login, me, list users, bootstrap admin."""
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import REQUIRE_AUTH, get_current_user
from ..models import User
from ..schemas import AuthResponse, LoginIn, RegisterIn, UserOut
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def bootstrap_admin(db: Session) -> None:
    """Create the admin account from env vars if no real (password-bearing) user exists."""
    if db.scalars(select(User).where(User.password_hash.isnot(None))).first():
        return
    email = os.environ.get("ADMIN_EMAIL", "admin@rogeriogt.com").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        return  # nothing to do until credentials are supplied
    db.add(User(
        email=email,
        name=os.environ.get("ADMIN_NAME", "Admin"),
        password_hash=hash_password(password),
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
