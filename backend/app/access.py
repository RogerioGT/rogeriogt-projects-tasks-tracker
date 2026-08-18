"""Access control: visibility scopes and permission checks for boards/tasks.

Visibility model (prod mode, REQUIRE_AUTH=true):
- Admin: sees and edits everything.
- FULL access boards: created by the user, or shared via board_acl (user or
  team), plus their descendants. The user sees ALL tasks inside these boards.
- CHAIN-ONLY boards: ancestors of a board containing a task shared with the
  user via task_acl. The user sees the hierarchy (so the board renders) but
  ONLY the shared task(s) inside it, never siblings or nested sub-projects.
- Edit permission: admin, creator, or an explicit "edit" ACL (board ACL
  inherited down the tree; task ACL for that task).

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


def _task_acl_cond(user: User, teams: list[str]):
    cond = TaskAcl.user_id == user.id
    if teams:
        cond = cond | TaskAcl.team_id.in_(teams)
    return cond


def full_access_board_ids(db: Session, user: User) -> set[str] | None:
    """Boards where the user sees ALL tasks (created + board shares + descendants).

    None = unrestricted (admin / local mode).
    """
    if not REQUIRE_AUTH or user.is_admin or user.email == "local@rogeriogt":
        return None

    ids: set[str] = set()
    ids.update(db.scalars(select(Board.id).where(Board.created_by == user.id)).all())
    ids.update(db.scalars(select(BoardAcl.board_id).where(BoardAcl.user_id == user.id)).all())
    teams = _team_ids(db, user.id)
    if teams:
        ids.update(db.scalars(select(BoardAcl.board_id).where(BoardAcl.team_id.in_(teams))).all())
    frontier = list(ids)
    while frontier:
        children = db.scalars(select(Board.id).where(Board.parent_id.in_(frontier))).all()
        new = [c for c in children if c not in ids]
        if not new:
            break
        ids.update(new)
        frontier = new
    return ids


def chain_board_ids(db: Session, user: User) -> set[str]:
    """Ancestor chains of boards containing tasks shared with the user.

    These boards render in the hierarchy but reveal no tasks by themselves.
    """
    teams = _team_ids(db, user.id)
    shared_task_board_ids = db.scalars(
        select(Task.board_id)
        .join(TaskAcl, TaskAcl.task_id == Task.id)
        .where(_task_acl_cond(user, teams))
    ).all()
    chain: set[str] = set()
    for board_id in set(shared_task_board_ids):
        node = db.get(Board, board_id)
        while node is not None:
            chain.add(node.id)
            node = node.parent
    return chain


def visible_board_ids(db: Session, user: User) -> set[str] | None:
    """Board ids the user can see. None = unrestricted (admin / local mode)."""
    if not REQUIRE_AUTH or user.is_admin or user.email == "local@rogeriogt":
        return None
    ids = full_access_board_ids(db, user) or set()
    ids |= chain_board_ids(db, user)
    return ids


def visible_task_ids(db: Session, user: User) -> set[str] | None:
    """Task ids the user can see. None = unrestricted.

    Rules:
    - all tasks inside FULL access boards
    - tasks shared directly via task_acl (user or team)
    """
    if not REQUIRE_AUTH or user.is_admin or user.email == "local@rogeriogt":
        return None

    ids: set[str] = set()
    boards = full_access_board_ids(db, user)
    if boards:
        ids.update(db.scalars(select(Task.id).where(Task.board_id.in_(boards))).all())
    teams = _team_ids(db, user.id)
    ids.update(
        db.scalars(select(TaskAcl.task_id).where(_task_acl_cond(user, teams))).all()
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
