"""Access control: visibility scopes and permission checks for boards/tasks.

Rules (prod mode, REQUIRE_AUTH=true):
- Admin: sees and edits everything.
- Regular user sees:
  - boards they created (created_by == user.id)
  - boards shared with them directly (board_acl.user_id)
  - boards shared with their teams (board_acl.team_id)
  - descendants of any visible board (inheritance down the tree)
- Tasks are visible when their board is visible OR a task_acl row grants access.
- Edit permission: admin, creator, or an explicit "edit" ACL (board ACL inherited
  down the tree; task ACL for that task).

Local mode (REQUIRE_AUTH=false): everything is allowed (single user, frictionless).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .deps import REQUIRE_AUTH
from .models import Board, BoardAcl, Task, TaskAcl, TeamMember, User

_EDIT = "edit"


def _team_ids(db: Session, user_id: str) -> list[str]:
    return list(
        db.scalars(select(TeamMember.team_id).where(TeamMember.user_id == user_id)).all()
    )


def visible_board_ids(db: Session, user: User) -> set[str] | None:
    """Board ids the user can see. None = unrestricted (admin / local mode)."""
    if not REQUIRE_AUTH or user.is_admin or user.email == "local@rogeriogt":
        return None

    ids: set[str] = set()
    # created by user
    ids.update(db.scalars(select(Board.id).where(Board.created_by == user.id)).all())
    # shared directly
    ids.update(
        db.scalars(select(BoardAcl.board_id).where(BoardAcl.user_id == user.id)).all()
    )
    # shared with user's teams
    teams = _team_ids(db, user.id)
    if teams:
        ids.update(
            db.scalars(select(BoardAcl.board_id).where(BoardAcl.team_id.in_(teams))).all()
        )
    # descendants of every visible board (inheritance down the tree)
    frontier = list(ids)
    while frontier:
        children = db.scalars(select(Board.id).where(Board.parent_id.in_(frontier))).all()
        new = [c for c in children if c not in ids]
        if not new:
            break
        ids.update(new)
        frontier = new
    return ids


def visible_task_ids(db: Session, user: User) -> set[str] | None:
    """Task ids the user can see. None = unrestricted."""
    if not REQUIRE_AUTH or user.is_admin or user.email == "local@rogeriogt":
        return None

    ids: set[str] = set()
    boards = visible_board_ids(db, user)
    if boards:
        ids.update(db.scalars(select(Task.id).where(Task.board_id.in_(boards))).all())
    ids.update(db.scalars(select(TaskAcl.task_id).where(TaskAcl.user_id == user.id)).all())
    teams = _team_ids(db, user.id)
    if teams:
        ids.update(
            db.scalars(select(TaskAcl.task_id).where(TaskAcl.team_id.in_(teams))).all()
        )
    return ids


def board_permission(db: Session, user: User, board_id: str) -> str | None:
    """Effective permission ("edit"/"view"/None) for a board, inheriting down the tree.

    Walks from the board up through ancestors, taking the strongest ACL found.
    """
    if not REQUIRE_AUTH or user.is_admin or user.email == "local@rogeriogt":
        return _EDIT

    board = db.get(Board, board_id)
    if board is None:
        return None
    if board.created_by == user.id:
        return _EDIT

    teams = _team_ids(db, user.id)
    best: str | None = None
    node = board
    while node is not None:
        cond = BoardAcl.user_id == user.id
        if teams:
            cond = cond | BoardAcl.team_id.in_(teams)
        rows = db.scalars(select(BoardAcl).where(BoardAcl.board_id == node.id, cond)).all()
        for r in rows:
            if r.permission == _EDIT:
                return _EDIT
            best = "view"
        node = node.parent
    return best


def task_permission(db: Session, user: User, task_id: str) -> str | None:
    """Effective permission for a task: board inheritance + task-level ACL."""
    if not REQUIRE_AUTH or user.is_admin or user.email == "local@rogeriogt":
        return _EDIT

    task = db.get(Task, task_id)
    if task is None:
        return None
    best = board_permission(db, user, task.board_id)
    if best == _EDIT:
        return _EDIT

    teams = _team_ids(db, user.id)
    cond = TaskAcl.user_id == user.id
    if teams:
        cond = cond | TaskAcl.team_id.in_(teams)
    rows = db.scalars(select(TaskAcl).where(TaskAcl.task_id == task_id, cond)).all()
    for r in rows:
        if r.permission == _EDIT:
            return _EDIT
        best = best or "view"
    return best


def require_board_permission(db: Session, user: User, board_id: str, minimum: str) -> bool:
    perm = board_permission(db, user, board_id)
    if minimum == _EDIT:
        return perm == _EDIT
    return perm is not None
