"""Trash router: soft-deleted boards/tasks with 30-day restore window.

Deletes are soft (deleted_at set). Items older than 30 days are purged on
startup. Admin-only: list trash, restore items, and purge permanently.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db, SessionLocal
from ..deps import get_current_admin
from ..models import Board, BoardAcl, Event, Task, TaskAcl, User, Workspace

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
    NOT deleted are listed individually. Trashed main boards (workspaces) are
    listed as a whole; their boards don't appear individually."""
    now = datetime.utcnow()
    trashed_ws = db.scalars(
        select(Workspace).where(Workspace.deleted_at.is_not(None)).order_by(Workspace.deleted_at.desc())
    ).all()
    trashed_ws_ids = {w.id for w in trashed_ws}

    boards = db.scalars(
        select(Board).where(Board.deleted_at.is_not(None), Board.workspace_id.not_in(trashed_ws_ids))
        .order_by(Board.deleted_at.desc())
    ).all() if trashed_ws_ids else db.scalars(
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

    ws_counts = {}
    if trashed_ws_ids:
        rows = db.execute(
            select(Board.workspace_id, func.count(Board.id))
            .where(Board.workspace_id.in_(trashed_ws_ids))
            .group_by(Board.workspace_id)
        ).all()
        ws_counts = {wid: cnt for wid, cnt in rows}

    return {
        "workspaces": [
            {
                "id": w.id,
                "name": w.name,
                "deleted_at": w.deleted_at.isoformat() if w.deleted_at else None,
                "expires_in_days": _days_left(w.deleted_at) if w.deleted_at else 0,
                "board_count": ws_counts.get(w.id, 0),
            }
            for w in trashed_ws
        ],
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
    # if its main board was trashed too, restore it along
    if board.workspace_id:
        ws = db.get(Workspace, board.workspace_id)
        if ws and ws.deleted_at is not None:
            ws.deleted_at = None
            for b in db.scalars(select(Board).where(Board.workspace_id == ws.id)).all():
                b.deleted_at = None
            ws_board_ids = [b.id for b in db.scalars(select(Board).where(Board.workspace_id == ws.id)).all()]
            if ws_board_ids:
                for t in db.scalars(select(Task).where(Task.board_id.in_(ws_board_ids))).all():
                    t.deleted_at = None
            db.add(Event(entity_type="workspace", entity_id=ws.id, action="restore"))
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
        if board and board.workspace_id:
            ws = db.get(Workspace, board.workspace_id)
            if ws and ws.deleted_at is not None:
                raise HTTPException(400, "restore the main board first, or the task stays in trash")
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
    """Permanently delete trashed items older than TRASH_DAYS. Called on startup.

    Only top-of-subtree boards are purged individually: an expired child whose
    parent is also expired gets cascade-deleted with the parent, so purging it
    again would 404 and crash the startup loop. Boards belonging to an expired
    trashed workspace are handled by purge_expired_workspaces() instead."""
    cutoff = datetime.utcnow() - timedelta(days=TRASH_DAYS)
    removed = 0
    db = SessionLocal()
    try:
        ws_expired = db.scalars(
            select(Workspace).where(Workspace.deleted_at.is_not(None), Workspace.deleted_at < cutoff)
        ).all()
        ws_ids = {w.id for w in ws_expired}
        expired_boards = db.scalars(
            select(Board).where(Board.deleted_at.is_not(None), Board.deleted_at < cutoff)
        ).all()
        expired_boards = [b for b in expired_boards if b.workspace_id not in ws_ids]
        expired_ids = {b.id for b in expired_boards}
        # only purge boards whose parent is not also expired (they die via cascade)
        tops = [b for b in expired_boards if b.parent_id not in expired_ids]
        for b in tops:
            purge_board(b.id, db)
            removed += 1
        # tasks whose board was cascade-purged above are already gone; purge the rest
        for t in db.scalars(
            select(Task).where(Task.deleted_at.is_not(None), Task.deleted_at < cutoff)
        ).all():
            board = db.get(Board, t.board_id) if t.board_id else None
            if board is not None and board.deleted_at is not None and board.deleted_at < cutoff:
                continue  # will be / was handled by its board's subtree purge
            if board is not None and board.workspace_id in ws_ids:
                continue  # handled by workspace purge
            purge_task(t.id, db)
            removed += 1
    finally:
        db.close()
    return removed
