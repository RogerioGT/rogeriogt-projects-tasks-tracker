"""Workspaces: top-level 'main boards'. Each is a fully independent tree.

A workspace contains top-level sections (boards with parent_id=None). All
boards in a workspace share workspace_id. Workspaces soft-delete like boards
(30-day trash, restore, purge).
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import full_access_board_ids, visible_board_ids
from ..db import get_db, SessionLocal
from ..deps import get_current_user, is_local_mode, REQUIRE_AUTH
from ..models import Board, Event, Task, User, Workspace
from ..schemas import WorkspaceCreate, WorkspaceOut, WorkspaceRename

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

DEFAULT_WORKSPACE_NAME = "Main Board"
TRASH_DAYS = 30


def _ensure_default_workspace(db: Session) -> Workspace:
    """Create the default workspace if none exist (first-run bootstrap)."""
    ws = db.scalars(select(Workspace).where(Workspace.deleted_at.is_(None)).order_by(Workspace.created_at)).first()
    if ws is None:
        ws = Workspace(name=DEFAULT_WORKSPACE_NAME)
        db.add(ws)
        db.commit()
        db.refresh(ws)
    return ws


def backfill_boards(db: Session) -> int:
    """Assign orphan boards (no workspace_id) to the default workspace.

    Walks each unassigned top-level board and stamps its whole subtree.
    Returns the number of boards stamped.
    """
    ws = _ensure_default_workspace(db)
    orphans = db.scalars(
        select(Board).where(Board.workspace_id.is_(None), Board.deleted_at.is_(None))
    ).all()
    count = 0
    for b in orphans:
        # if its parent chain already has a workspace, inherit that; else default
        target = ws.id
        node = b
        seen = set()
        while node is not None and node.id not in seen:
            seen.add(node.id)
            if node.workspace_id:
                target = node.workspace_id
                break
            node = db.get(Board, node.parent_id) if node.parent_id else None
        b.workspace_id = target
        count += 1
    if count:
        db.commit()
    return count


def _workspace_counts(db: Session, workspace_ids: list[str]) -> dict[str, int]:
    if not workspace_ids:
        return {}
    rows = db.execute(
        select(Board.workspace_id, func.count(Board.id))
        .where(Board.workspace_id.in_(workspace_ids), Board.deleted_at.is_(None))
        .group_by(Board.workspace_id)
    ).all()
    return {wid: cnt for wid, cnt in rows}


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_default_workspace(db)
    ws_list = db.scalars(
        select(Workspace).where(Workspace.deleted_at.is_(None)).order_by(Workspace.created_at)
    ).all()
    if is_local_mode() or user.is_admin:
        visible = ws_list
    else:
        # non-admins see workspaces they created (even empty ones) plus any
        # workspace containing at least one board they can see.
        boards = db.scalars(select(Board).where(Board.deleted_at.is_(None))).all()
        visible_ids = visible_board_ids(db, user) or set()
        allowed = {b.workspace_id for b in boards if b.id in visible_ids}
        allowed |= {w.id for w in ws_list if w.created_by == user.id}
        visible = [w for w in ws_list if w.id in allowed]
    counts = _workspace_counts(db, [w.id for w in ws_list])
    return [
        WorkspaceOut(
            id=w.id,
            name=w.name,
            created_by=w.created_by,
            created_at=w.created_at,
            board_count=counts.get(w.id, 0),
        )
        for w in visible
    ]


@router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name is required")
    dup = db.scalars(
        select(Workspace).where(Workspace.name == name, Workspace.deleted_at.is_(None))
    ).first()
    if dup:
        raise HTTPException(409, "a board with this name already exists")
    ws = Workspace(name=name, created_by=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    db.add(Event(entity_type="workspace", entity_id=ws.id, user_id=user.id, action="create", new_value=ws.name))
    db.commit()
    return WorkspaceOut(id=ws.id, name=ws.name, created_by=ws.created_by, created_at=ws.created_at, board_count=0)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def rename_workspace(workspace_id: str, payload: WorkspaceRename, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if not is_local_mode() and not user.is_admin and ws.created_by != user.id:
        raise HTTPException(403, "no edit permission")
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name is required")
    dup = db.scalars(
        select(Workspace).where(Workspace.name == name, Workspace.deleted_at.is_(None), Workspace.id != ws.id)
    ).first()
    if dup:
        raise HTTPException(409, "a board with this name already exists")
    old = ws.name
    ws.name = name
    db.add(Event(entity_type="workspace", entity_id=ws.id, user_id=user.id, action="rename", field="name", old_value=old, new_value=name))
    db.commit()
    db.refresh(ws)
    return WorkspaceOut(id=ws.id, name=ws.name, created_by=ws.created_by, created_at=ws.created_at,
                        board_count=_workspace_counts(db, [ws.id]).get(ws.id, 0))


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Soft delete: workspace + every board and task in it -> Trash (30 days)."""
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if not is_local_mode() and not user.is_admin and ws.created_by != user.id:
        raise HTTPException(403, "no edit permission")
    # guard: keep at least one live workspace
    live = db.scalars(select(func.count(Workspace.id)).where(Workspace.deleted_at.is_(None))).first() or 0
    if live <= 1:
        raise HTTPException(400, "cannot delete the last board")
    now = datetime.utcnow()
    ws.deleted_at = now
    boards = db.scalars(select(Board).where(Board.workspace_id == workspace_id, Board.deleted_at.is_(None))).all()
    board_ids = [b.id for b in boards]
    for b in boards:
        b.deleted_at = now
    if board_ids:
        tasks = db.scalars(select(Task).where(Task.board_id.in_(board_ids), Task.deleted_at.is_(None))).all()
        for t in tasks:
            t.deleted_at = now
    db.add(Event(entity_type="workspace", entity_id=ws.id, user_id=user.id, action="delete", new_value=ws.name))
    db.commit()


@router.post("/{workspace_id}/restore", response_model=WorkspaceOut)
def restore_workspace(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.deleted_at is None:
        raise HTTPException(404, "deleted board not found in trash")
    if not is_local_mode() and not user.is_admin:
        raise HTTPException(403, "admin only")
    ws.deleted_at = None
    boards = db.scalars(select(Board).where(Board.workspace_id == workspace_id)).all()
    board_ids = [b.id for b in boards]
    for b in boards:
        b.deleted_at = None
    if board_ids:
        tasks = db.scalars(select(Task).where(Task.board_id.in_(board_ids))).all()
        for t in tasks:
            t.deleted_at = None
    db.add(Event(entity_type="workspace", entity_id=ws.id, user_id=user.id, action="restore", new_value=ws.name))
    db.commit()
    db.refresh(ws)
    return WorkspaceOut(id=ws.id, name=ws.name, created_by=ws.created_by, created_at=ws.created_at,
                        board_count=_workspace_counts(db, [ws.id]).get(ws.id, 0))


def _purge_ws_boards(db: Session, workspace_id: str) -> None:
    """Hard-delete every board in a workspace, deepest first."""
    boards = db.scalars(select(Board).where(Board.workspace_id == workspace_id)).all()
    board_ids = [b.id for b in boards]
    if not board_ids:
        return
    from ..models import BoardAcl, TaskAcl
    db.execute(BoardAcl.__table__.delete().where(BoardAcl.board_id.in_(board_ids)))
    task_ids = db.scalars(select(Task.id).where(Task.board_id.in_(board_ids))).all()
    if task_ids:
        db.execute(TaskAcl.__table__.delete().where(TaskAcl.task_id.in_(task_ids)))
    # order deepest-first so parents are deleted after their children
    by_parent: dict[str | None, list[Board]] = {}
    for b in boards:
        by_parent.setdefault(b.parent_id, []).append(b)
    ordered: list[Board] = []

    def visit(parent_id: str | None):
        for child in sorted(by_parent.get(parent_id, []), key=lambda b: b.sort_order):
            visit(child.id)
            ordered.append(child)

    visit(None)
    # any stragglers with dangling parents
    for b in boards:
        if b not in ordered:
            ordered.append(b)
    for b in ordered:
        db.delete(b)


@router.delete("/trash/{workspace_id}", status_code=204)
def purge_workspace(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Permanently delete a trashed workspace and everything in it."""
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.deleted_at is None:
        raise HTTPException(404, "deleted board not found in trash")
    if not is_local_mode() and not user.is_admin:
        raise HTTPException(403, "admin only")
    _purge_ws_boards(db, workspace_id)
    db.delete(ws)
    db.commit()


def purge_expired_workspaces() -> int:
    """Startup cleanup: permanently delete workspaces trashed >30 days ago."""
    cutoff = datetime.utcnow() - timedelta(days=TRASH_DAYS)
    db = SessionLocal()
    try:
        expired = db.scalars(
            select(Workspace).where(Workspace.deleted_at.is_not(None), Workspace.deleted_at < cutoff)
        ).all()
        for ws in expired:
            _purge_ws_boards(db, ws.id)
            db.delete(ws)
        db.commit()
        return len(expired)
    finally:
        db.close()
