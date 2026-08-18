"""Events router: read-only audit history (who changed what, when).

The events table is append-only and already written by boards/tasks routers.
This exposes it so the frontend can show a History view.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Event
from ..schemas import EventOut

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = select(Event)
    if entity_type:
        q = q.where(Event.entity_type == entity_type)
    if entity_id:
        q = q.where(Event.entity_id == entity_id)
    if action:
        q = q.where(Event.action == action)
    q = q.order_by(Event.created_at.desc()).limit(limit)
    return db.scalars(q).all()
