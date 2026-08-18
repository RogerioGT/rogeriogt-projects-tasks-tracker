"""Events router: read-only audit history (who changed what, when).

The events table is append-only and already written by boards/tasks routers.
This exposes it so the frontend can show a History view.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import visible_board_ids, visible_task_ids
from ..db import get_db
from ..deps import get_current_user
from ..models import Event, User
from ..schemas import EventOut

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Event)
    # Visibility: regular users only see events for entities they can access.
    task_visible = visible_task_ids(db, user)
    board_visible = visible_board_ids(db, user)
    if task_visible is not None and board_visible is not None:
        q = q.where(
            ((Event.entity_type == "task") & Event.entity_id.in_(task_visible))
            | ((Event.entity_type == "board") & Event.entity_id.in_(board_visible))
        )
    if entity_type:
        q = q.where(Event.entity_type == entity_type)
    if entity_id:
        q = q.where(Event.entity_id == entity_id)
    if action:
        q = q.where(Event.action == action)
    q = q.order_by(Event.created_at.desc()).limit(limit)
    return db.scalars(q).all()
