"""Statuses router: custom workflow status options.

Any authenticated user can add a status; only admins can rename, recolor,
or delete. Deleting a status does not touch existing tasks (they keep the
status name as a plain string).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_admin, get_current_user
from ..models import Status, User
from ..schemas import StatusCreate, StatusOut, StatusUpdate

router = APIRouter(prefix="/api/statuses", tags=["statuses"])

# The 4 defaults, seeded on first boot. Deleting them is allowed but
# discouraged; tasks will simply keep using the name.
DEFAULT_STATUSES = [
    ("not_started", "#6b7280", 0),
    ("in_progress", "#3b82f6", 1),
    ("waiting", "#eab308", 2),
    ("done", "#22c55e", 3),
]


def seed_statuses(db: Session) -> None:
    if db.query(Status).first():
        return
    for i, (name, color, order) in enumerate(DEFAULT_STATUSES):
        db.add(Status(name=name, color=color, sort_order=order))
    db.commit()


@router.get("", response_model=list[StatusOut])
def list_statuses(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.scalars(select(Status).order_by(Status.sort_order, Status.name)).all()


@router.post("", response_model=StatusOut, status_code=201)
def create_status(payload: StatusCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "status name is required")
    if len(name) > 60:
        raise HTTPException(400, "status name too long (max 60 chars)")
    existing = db.scalars(select(Status).where(Status.name == name)).first()
    if existing:
        raise HTTPException(409, "status already exists")
    max_order = db.scalar(select(Status.sort_order).order_by(Status.sort_order.desc())) or 0
    status = Status(name=name, color=payload.color or "#64748b", sort_order=max_order + 1, created_by=user.id)
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


@router.patch("/{status_id}", response_model=StatusOut)
def update_status(status_id: str, payload: StatusUpdate, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    status = db.get(Status, status_id)
    if not status:
        raise HTTPException(404, "status not found")
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(400, "status name is required")
        dup = db.scalars(select(Status).where(Status.name == name, Status.id != status_id)).first()
        if dup:
            raise HTTPException(409, "status already exists")
        status.name = name
    if payload.color is not None:
        status.color = payload.color
    if payload.sort_order is not None:
        status.sort_order = payload.sort_order
    db.commit()
    db.refresh(status)
    return status


@router.delete("/{status_id}", status_code=204)
def delete_status(status_id: str, db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    status = db.get(Status, status_id)
    if not status:
        raise HTTPException(404, "status not found")
    db.delete(status)
    db.commit()
