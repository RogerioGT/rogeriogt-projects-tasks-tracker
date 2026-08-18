"""Sharing router v2: board ACL (user OR team) + task ACL (single or batch).

Board sharing inherits down the tree (share a company -> its projects/tasks
are shared). Task sharing is standalone: share one task or a batch of tasks.

Permissions:
- list ACLs:    must be able to view the entity (board/task)
- share:        must have edit permission on the entity
- unshare:      must have edit permission on the entity
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import board_permission, task_permission
from ..db import get_db
from ..deps import get_current_user
from ..models import Board, BoardAcl, Event, Task, TaskAcl, Team, User
from ..schemas import (
    BatchTaskShareIn,
    ShareIn,
    ShareOut,
    TaskShareIn,
    TaskShareOut,
)

router = APIRouter(prefix="/api", tags=["sharing"])


def _validate_target(db: Session, user_id: str | None, team_id: str | None) -> None:
    if user_id and not db.get(User, user_id):
        raise HTTPException(404, "user not found")
    if team_id and not db.get(Team, team_id):
        raise HTTPException(404, "team not found")


def _target_desc(user_id: str | None, team_id: str | None) -> str:
    return f"user:{user_id}" if user_id else f"team:{team_id}"


def _require_edit_board(db: Session, actor: User, board_id: str) -> Board:
    board = db.get(Board, board_id)
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, actor, board_id) != "edit":
        raise HTTPException(403, "no edit permission on this board")
    return board


def _require_edit_task(db: Session, actor: User, task_id: str) -> Task:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "task not found")
    if task_permission(db, actor, task_id) != "edit":
        raise HTTPException(403, "no edit permission on this task")
    return task


# ── Board ACL ──────────────────────────────────────────────────────────────

@router.get("/boards/{board_id}/acl", response_model=list[ShareOut])
def list_acl(board_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    board = db.get(Board, board_id)
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, board_id) is None:
        raise HTTPException(403, "no access to this board")
    return db.scalars(select(BoardAcl).where(BoardAcl.board_id == board_id)).all()


@router.post("/boards/{board_id}/acl", response_model=ShareOut, status_code=201)
def share_board(
    board_id: str,
    payload: ShareIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    board = _require_edit_board(db, actor, board_id)
    _validate_target(db, payload.user_id, payload.team_id)
    if payload.permission not in ("view", "edit"):
        raise HTTPException(400, "permission must be view or edit")
    existing = db.scalars(
        select(BoardAcl).where(
            BoardAcl.board_id == board_id,
            BoardAcl.user_id == payload.user_id,
            BoardAcl.team_id == payload.team_id,
        )
    ).first()
    if existing:
        existing.permission = payload.permission
        acl = existing
    else:
        acl = BoardAcl(board_id=board_id, user_id=payload.user_id,
                       team_id=payload.team_id, permission=payload.permission)
        db.add(acl)
    db.flush()
    db.add(Event(entity_type="board", entity_id=board_id, user_id=actor.id,
                 action="share", field="permission",
                 new_value=f"{_target_desc(payload.user_id, payload.team_id)}:{payload.permission}"))
    db.commit()
    db.refresh(acl)
    return acl


@router.delete("/boards/{board_id}/acl/{acl_id}", status_code=204)
def unshare_board(board_id: str, acl_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    _require_edit_board(db, actor, board_id)
    acl = db.scalars(
        select(BoardAcl).where(BoardAcl.board_id == board_id, BoardAcl.id == acl_id)
    ).first()
    if not acl:
        raise HTTPException(404, "share not found")
    db.delete(acl)
    db.commit()


# ── Task ACL ───────────────────────────────────────────────────────────────

@router.get("/tasks/{task_id}/acl", response_model=list[TaskShareOut])
def list_task_acl(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "task not found")
    if task_permission(db, user, task_id) is None:
        raise HTTPException(403, "no access to this task")
    return db.scalars(select(TaskAcl).where(TaskAcl.task_id == task_id)).all()


@router.post("/tasks/{task_id}/acl", response_model=TaskShareOut, status_code=201)
def share_task(
    task_id: str,
    payload: TaskShareIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    _require_edit_task(db, actor, task_id)
    _validate_target(db, payload.user_id, payload.team_id)
    if payload.permission not in ("view", "edit"):
        raise HTTPException(400, "permission must be view or edit")
    existing = db.scalars(
        select(TaskAcl).where(
            TaskAcl.task_id == task_id,
            TaskAcl.user_id == payload.user_id,
            TaskAcl.team_id == payload.team_id,
        )
    ).first()
    if existing:
        existing.permission = payload.permission
        acl = existing
    else:
        acl = TaskAcl(task_id=task_id, user_id=payload.user_id,
                      team_id=payload.team_id, permission=payload.permission)
        db.add(acl)
    db.flush()
    db.add(Event(entity_type="task", entity_id=task_id, user_id=actor.id,
                 action="share", field="permission",
                 new_value=f"{_target_desc(payload.user_id, payload.team_id)}:{payload.permission}"))
    db.commit()
    db.refresh(acl)
    return acl


@router.delete("/tasks/{task_id}/acl/{acl_id}", status_code=204)
def unshare_task(task_id: str, acl_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    _require_edit_task(db, actor, task_id)
    acl = db.scalars(
        select(TaskAcl).where(TaskAcl.task_id == task_id, TaskAcl.id == acl_id)
    ).first()
    if not acl:
        raise HTTPException(404, "share not found")
    db.delete(acl)
    db.commit()


@router.post("/tasks/share", response_model=dict, status_code=201)
def share_tasks_batch(
    payload: BatchTaskShareIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    """Share a selected list of tasks with a user or team in one call."""
    _validate_target(db, payload.user_id, payload.team_id)
    if payload.permission not in ("view", "edit"):
        raise HTTPException(400, "permission must be view or edit")
    created = 0
    updated = 0
    for task_id in set(payload.task_ids):
        task = db.get(Task, task_id)
        if not task or task.deleted_at is not None:
            continue
        if task_permission(db, actor, task_id) != "edit":
            raise HTTPException(403, f"no edit permission on task {task_id}")
        existing = db.scalars(
            select(TaskAcl).where(
                TaskAcl.task_id == task_id,
                TaskAcl.user_id == payload.user_id,
                TaskAcl.team_id == payload.team_id,
            )
        ).first()
        if existing:
            existing.permission = payload.permission
            updated += 1
        else:
            db.add(TaskAcl(task_id=task_id, user_id=payload.user_id,
                           team_id=payload.team_id, permission=payload.permission))
            created += 1
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "target": _target_desc(payload.user_id, payload.team_id),
        "permission": payload.permission,
    }
