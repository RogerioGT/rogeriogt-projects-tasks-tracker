"""Trash router: soft-deleted boards/tasks with 30-day restore window.

Deletes are soft (deleted_at set). Items older than 30 days are purged on
startup. Admin-only: list trash, restore items, and purge permanently.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db, SessionLocal
from ..deps import get_current_admin
from ..models import Board, BoardAcl, Event, Task, TaskAcl, User

router = APIRouter(prefix="/api/trash", tags=["trash"], dependencies=[Depends(get_current_admin)])

TRASH_DAYS = 30


def _board_ids_under(db: Session, board_id: str) -> list[str]:
    ids = [board_id]
    frontier = [board_id]
    while frontier:
        children = db.scalars(select(Board.id).where(Board.parent_id.in_(frontier))).all()
        if not children:
            break
        ids.extend(children)
        frontier = list(children)
    return ids


@router.get("")
def list_trash(db: Session = Depends(get_db)):
    """Deleted items. Boards are grouped: only top-of-subtree deleted boards are
    listed (children come back with the parent). Deleted tasks whose board is
    NOT deleted are listed individually."""
    now = datetime.utcnow()
    boards = db.scalars(
        select(Board).where(Board.deleted_at.is_not(None)).order_by(Board.deleted_at.desc())
    ).all()
    deleted_ids = {b.id for b in boards}
    # top-of-subtree: parent not deleted
    top_boards = [b for b in boards if b.parent_id not in deleted_ids]

    tasks = db.scalars(
        select(Task).where(Task.deleted_at.is_not(None)).order_by(Task.deleted_at.desc())
    ).all()
    orphan_tasks = [t for t in tasks if t.board_id not in deleted_ids]

    def _days_left(deleted_at):
        elapsed_days = (now - deleted_at).days
        return max(0, TRASH_DAYS - elapsed_days)

    return {
        "boards": [
            {
                "id": b.id,
                "name": b.name,
                "kind": b.kind,
                "deleted_at": b.deleted_at.isoformat() if b.deleted_at else None,
                "expires_in_days": _days_left(b.deleted_at) if b.deleted_at else 0,
            }
            for b in top_boards
        ],
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
                "expires_in_days": _days_left(t.deleted_at) if t.deleted_at else 0,
            }
            for t in orphan_tasks
        ],
        "trash_days": TRASH_DAYS,
    }


@router.post("/boards/{board_id}/restore", status_code=200)
def restore_board(board_id: str, db: Session = Depends(get_db)):
    board = db.get(Board, board_id)
    if not board or board.deleted_at is None:
        raise HTTPException(404, "deleted board not found")
    subtree_ids = _board_ids_under(db, board_id)
    for b in db.scalars(select(Board).where(Board.id.in_(subtree_ids))).all():
        b.deleted_at = None
    for t in db.scalars(select(Task).where(Task.board_id.in_(subtree_ids))).all():
        t.deleted_at = None
    db.add(Event(entity_type="board", entity_id=board_id, action="restore"))
    db.commit()
    return {"restored": board_id}


@router.post("/tasks/{task_id}/restore", status_code=200)
def restore_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task or task.deleted_at is None:
        raise HTTPException(404, "deleted task not found")
    if task.board_id:
        board = db.get(Board, task.board_id)
        if board and board.deleted_at is not None:
            raise HTTPException(400, "restore the board first, or the task stays in trash")
    task.deleted_at = None
    db.add(Event(entity_type="task", entity_id=task_id, action="restore"))
    db.commit()
    return {"restored": task_id}


@router.delete("/boards/{board_id}", status_code=204)
def purge_board(board_id: str, db: Session = Depends(get_db)):
    """Permanently delete a trashed board + subtree (no restore after this)."""
    board = db.get(Board, board_id)
    if not board or board.deleted_at is None:
        raise HTTPException(404, "deleted board not found")
    subtree_ids = _board_ids_under(db, board_id)
    for acl in db.scalars(select(TaskAcl).where(TaskAcl.task_id.in_(
        select(Task.id).where(Task.board_id.in_(subtree_ids))
    ))).all():
        db.delete(acl)
    for acl in db.scalars(select(BoardAcl).where(BoardAcl.board_id.in_(subtree_ids))).all():
        db.delete(acl)
    db.flush()
    db.delete(board)  # cascade children + tasks
    db.commit()


@router.delete("/tasks/{task_id}", status_code=204)
def purge_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task or task.deleted_at is None:
        raise HTTPException(404, "deleted task not found")
    for acl in db.scalars(select(TaskAcl).where(TaskAcl.task_id == task_id)).all():
        db.delete(acl)
    db.flush()
    db.delete(task)
    db.commit()


def purge_expired() -> int:
    """Permanently delete trashed items older than TRASH_DAYS. Called on startup."""
    cutoff = datetime.utcnow() - timedelta(days=TRASH_DAYS)
    removed = 0
    db = SessionLocal()
    try:
        for b in db.scalars(select(Board).where(Board.deleted_at.is_not(None), Board.deleted_at < cutoff)).all():
            purge_board(b.id, db)
            removed += 1
        for t in db.scalars(select(Task).where(Task.deleted_at.is_not(None), Task.deleted_at < cutoff)).all():
            purge_task(t.id, db)
            removed += 1
    finally:
        db.close()
    return removed
