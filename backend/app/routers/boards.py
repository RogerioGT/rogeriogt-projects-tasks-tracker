"""Boards router: CRUD + tree. Boards = Sections/Companies/Projects.

Enforces visibility (list/tree show only what the user can see) and edit
permission (create/update/delete require edit access, inherited down the tree).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..access import board_permission, visible_board_ids
from ..db import get_db
from ..deps import get_current_user
from ..models import Board, BoardAcl, Event, Task, TaskAcl, User, Workspace
from ..schemas import BoardCreate, BoardKindChange, BoardMove, BoardOut, BoardUpdate

router = APIRouter(prefix="/api/boards", tags=["boards"])


def _board_ids_under(db: Session, board_id: str) -> list[str]:
    """board_id plus all descendant ids."""
    ids = [board_id]
    frontier = [board_id]
    while frontier:
        children = db.scalars(select(Board.id).where(Board.parent_id.in_(frontier))).all()
        if not children:
            break
        ids.extend(children)
        frontier = list(children)
    return ids


def _log(db: Session, entity: str, eid: str, action: str, user_id=None, field=None, old=None, new=None):
    db.add(Event(entity_type=entity, entity_id=eid, user_id=user_id, action=action,
                 field=field, old_value=old, new_value=new))


@router.get("", response_model=list[BoardOut])
def list_boards(workspace_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Board).where(Board.deleted_at.is_(None))
    if workspace_id:
        q = q.where(Board.workspace_id == workspace_id)
    visible = visible_board_ids(db, user)
    if visible is not None:
        q = q.where(Board.id.in_(visible))
    return db.scalars(q.order_by(Board.sort_order, Board.name)).all()


@router.get("/tree")
def board_tree(workspace_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Board).where(Board.deleted_at.is_(None))
    if workspace_id:
        q = q.where(Board.workspace_id == workspace_id)
    boards = db.scalars(q.order_by(Board.sort_order, Board.name)).all()
    visible = visible_board_ids(db, user)
    if visible is not None:
        boards = [b for b in boards if b.id in visible]
    by_parent: dict[str | None, list[dict]] = {}
    for b in boards:
        perm = board_permission(db, user, b.id)
        by_parent.setdefault(b.parent_id, []).append(
            {
                "id": b.id,
                "name": b.name,
                "kind": b.kind,
                "color": b.color,
                "sort_order": b.sort_order,
                "parent_id": b.parent_id,
                "workspace_id": b.workspace_id,
                "permission": perm,  # "edit" | "view" | None
                "children": [],
            }
        )
    def build(parent_id):
        nodes = by_parent.get(parent_id, [])
        for n in nodes:
            n["children"] = build(n["id"])
        return nodes
    roots = build(None)
    # Also surface visible boards whose ancestors are NOT visible (e.g. a user
    # shared only one project): attach them as top-level roots.
    visible_ids = set(b.id for b in boards)
    attached = set()
    for root in roots:
        attached.add(root["id"])
        queue = list(root["children"])
        while queue:
            attached.add(queue[0]["id"])
            queue.extend(queue[0]["children"])
            queue.pop(0)
    orphans = [b for b in boards if b.id not in attached]
    for b in orphans:
        roots.append(
            {
                "id": b.id,
                "name": b.name,
                "kind": b.kind,
                "color": b.color,
                "sort_order": b.sort_order,
                "parent_id": b.parent_id,
                "workspace_id": b.workspace_id,
                "permission": board_permission(db, user, b.id),
                "children": [],
            }
        )
    return roots


@router.post("", response_model=BoardOut, status_code=201)
def create_board(payload: BoardCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    parent = None
    if payload.parent_id:
        parent = db.get(Board, payload.parent_id)
        if not parent or parent.deleted_at is not None:
            raise HTTPException(404, "parent board not found")
        if board_permission(db, user, parent.id) != "edit":
            raise HTTPException(403, "no edit permission on parent board")
    if payload.kind not in ("section", "company", "project"):
        raise HTTPException(400, "kind must be section, company, or project")
    # resolve workspace: inherit from parent, else payload, else default
    if parent is not None:
        workspace_id = parent.workspace_id
    elif payload.workspace_id:
        from .workspaces import _ensure_default_workspace
        ws = db.get(Workspace, payload.workspace_id)
        if not ws or ws.deleted_at is not None:
            raise HTTPException(404, "workspace not found")
        workspace_id = ws.id
    else:
        from .workspaces import _ensure_default_workspace
        workspace_id = _ensure_default_workspace(db).id
    board = Board(
        name=payload.name,
        parent_id=payload.parent_id,
        workspace_id=workspace_id,
        kind=payload.kind,
        color=payload.color or _auto_color(db),
        sort_order=payload.sort_order,
        created_by=user.id,
    )
    db.add(board)
    db.flush()
    _log(db, "board", board.id, "create", user_id=user.id)
    db.commit()
    db.refresh(board)
    return board


@router.patch("/{board_id}", response_model=BoardOut)
def update_board(board_id: str, payload: BoardUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    board = db.get(Board, board_id)
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, board_id) != "edit":
        raise HTTPException(403, "no edit permission on this board")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(board, k, v)
    _log(db, "board", board_id, "update", user_id=user.id)
    db.commit()
    db.refresh(board)
    return board


@router.post("/{board_id}/move", response_model=BoardOut)
def move_board(board_id: str, payload: BoardMove, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Drag-and-drop: move/reorder a board. Sets parent_id and reindexes
    siblings so position = index in the parent's children list (0 = leftmost).

    Guards:
    - cannot nest a board under itself or its own descendant (cycle)
    - edit permission on the board AND the target parent (or top level)
    """
    board = db.get(Board, board_id)
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, board_id) != "edit":
        raise HTTPException(403, "no edit permission on this board")

    new_parent_id = payload.parent_id
    if new_parent_id == board.id:
        raise HTTPException(400, "a board cannot be its own parent")
    if new_parent_id is not None:
        new_parent = db.get(Board, new_parent_id)
        if not new_parent or new_parent.deleted_at is not None:
            raise HTTPException(404, "target board not found")
        if board_permission(db, user, new_parent_id) != "edit":
            raise HTTPException(403, "no edit permission on the target board")
        # workspace guard: boards cannot move across main boards
        if new_parent.workspace_id != board.workspace_id:
            raise HTTPException(400, "cannot move a board to another main board")
        # cycle guard: walk up from new_parent; must not hit this board
        node = new_parent
        while node is not None:
            if node.id == board_id:
                raise HTTPException(400, "cannot move a board under its own child")
            node = node.parent

    old_parent = board.parent_id
    board.parent_id = new_parent_id
    db.flush()

    # reindex siblings of the NEW parent (and old parent when different)
    # — only live boards, so trashed boards don't grab sort_order slots
    for pid in ({new_parent_id, old_parent} - {None}):
        siblings = db.scalars(
            select(Board).where(Board.parent_id == pid, Board.deleted_at.is_(None))
            .order_by(Board.sort_order, Board.name)
        ).all()
        for i, sib in enumerate(siblings):
            sib.sort_order = i
    # top-level boards too (only within the board's own main board)
    if new_parent_id is None or old_parent is None:
        roots = db.scalars(
            select(Board)
            .where(Board.parent_id.is_(None), Board.deleted_at.is_(None), Board.workspace_id == board.workspace_id)
            .order_by(Board.sort_order, Board.name)
        ).all()
        for i, r in enumerate(roots):
            r.sort_order = i
    # finally, put the moved board at the requested position
    if payload.position is not None:
        siblings = db.scalars(
            select(Board)
            .where(Board.parent_id == new_parent_id, Board.deleted_at.is_(None))
            .order_by(Board.sort_order)
        ).all()
        siblings = [s for s in siblings if s.id != board_id]
        pos = max(0, min(payload.position, len(siblings)))
        for i, sib in enumerate(siblings):
            sib.sort_order = i if i < pos else i + 1
        board.sort_order = pos
    _log(db, "board", board_id, "move", user_id=user.id,
         field="parent_id", old=old_parent, new=new_parent_id)
    db.commit()
    db.refresh(board)
    return board


@router.get("/{board_id}/assignees")
def board_assignees(board_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Users available for assigning tasks in this board: everyone the board
    is shared with (directly, via teams, via task-level shares), plus the
    board creator and admins. Requires at least view access on the board."""
    board = db.get(Board, board_id)
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, board_id) is None:
        raise HTTPException(403, "no access to this board")
    subtree = _board_ids_under(db, board_id)
    ids: set[str] = set()
    # board-level shares (user + team) on the board or its ancestors
    node: Board | None = board
    while node is not None:
        ids.update(u for u in db.scalars(select(BoardAcl.user_id).where(BoardAcl.board_id == node.id, BoardAcl.user_id.is_not(None))).all() if u)
        team_ids = db.scalars(select(BoardAcl.team_id).where(BoardAcl.board_id == node.id, BoardAcl.team_id.is_not(None))).all()
        if team_ids:
            from ..models import TeamMember
            ids.update(db.scalars(select(TeamMember.user_id).where(TeamMember.team_id.in_(team_ids))).all())
        node = node.parent
    # task-level shares within the subtree
    task_ids = db.scalars(select(Task.id).where(Task.board_id.in_(subtree))).all()
    if task_ids:
        ids.update(u for u in db.scalars(select(TaskAcl.user_id).where(TaskAcl.task_id.in_(task_ids), TaskAcl.user_id.is_not(None))).all() if u)
    # board creator + admins
    if board.created_by:
        ids.add(board.created_by)
    ids.update(db.scalars(select(User.id).where(User.is_admin.is_(True))).all())
    users = db.scalars(select(User).where(User.id.in_(ids), User.is_active.is_(True)).order_by(User.name, User.email)).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "is_admin": u.is_admin} for u in users]


@router.delete("/{board_id}", status_code=204)
def delete_board(board_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Soft delete: moves the board + entire subtree + their tasks to the Trash.
    Restorable for 30 days via /api/trash."""
    board = db.get(Board, board_id)
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, board_id) != "edit":
        raise HTTPException(403, "no edit permission on this board")
    now = datetime.utcnow()
    subtree_ids = _board_ids_under(db, board_id)
    for b in db.scalars(select(Board).where(Board.id.in_(subtree_ids))).all():
        b.deleted_at = now
    for t in db.scalars(select(Task).where(Task.board_id.in_(subtree_ids), Task.deleted_at.is_(None))).all():
        t.deleted_at = now
    _log(db, "board", board_id, "delete", user_id=user.id, new="trash")
    db.commit()


@router.post("/{board_id}/convert", response_model=BoardOut)
def convert_kind(board_id: str, payload: BoardKindChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Change a board's hierarchy level: project <-> company <-> section.

    Rules:
    - Converting to a section moves the board to the top level (sections are
      the top-level bands). Tasks and sub-boards come along untouched.
    - Converting a section to a company/project keeps it wherever it is.
    """
    board = db.get(Board, board_id)
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, board_id) != "edit":
        raise HTTPException(403, "no edit permission on this board")
    if payload.kind not in ("section", "company", "project"):
        raise HTTPException(400, "kind must be section, company, or project")
    if payload.kind == board.kind:
        return board
    old_kind = board.kind
    if payload.kind == "section":
        board.parent_id = None
        # reindex top-level (only within this board's own main board)
        roots = db.scalars(
            select(Board)
            .where(Board.parent_id.is_(None), Board.deleted_at.is_(None), Board.workspace_id == board.workspace_id)
            .order_by(Board.sort_order)
        ).all()
        for i, r in enumerate(roots):
            if r.id != board.id:
                r.sort_order = i
        board.sort_order = len(roots)
    board.kind = payload.kind
    _log(db, "board", board_id, "convert", user_id=user.id, field="kind", old=old_kind, new=payload.kind)
    db.commit()
    db.refresh(board)
    return board


def _auto_color(db: Session) -> str:
    """Pick the least-used color from the palette so auto-colored boards vary."""
    palette = [
        "#3b82f6", "#f97316", "#22c55e", "#a855f7", "#ef4444",
        "#14b8a6", "#eab308", "#ec4899", "#06b6d4", "#8b5cf6",
    ]
    counts: dict[str, int] = {}
    for color, cnt in db.execute(
        select(Board.color, func.count(Board.id)).group_by(Board.color)
    ).all():
        counts[color] = cnt
    return min(palette, key=lambda c: counts.get(c, 0))
