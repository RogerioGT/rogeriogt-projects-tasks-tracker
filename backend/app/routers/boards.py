"""Boards router: CRUD + tree. Boards = Sections/Companies/Projects."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Board, Event
from ..schemas import BoardCreate, BoardOut, BoardUpdate

router = APIRouter(prefix="/api/boards", tags=["boards"])


def _log(db: Session, entity: str, eid: str, action: str, field=None, old=None, new=None):
    db.add(Event(entity_type=entity, entity_id=eid, action=action, field=field,
                 old_value=old, new_value=new))


@router.get("", response_model=list[BoardOut])
def list_boards(db: Session = Depends(get_db)):
    return db.scalars(select(Board).order_by(Board.sort_order, Board.name)).all()


@router.get("/tree")
def board_tree(db: Session = Depends(get_db)):
    boards = db.scalars(select(Board).order_by(Board.sort_order, Board.name)).all()
    by_parent: dict[str | None, list[dict]] = {}
    for b in boards:
        by_parent.setdefault(b.parent_id, []).append(
            {
                "id": b.id,
                "name": b.name,
                "kind": b.kind,
                "color": b.color,
                "sort_order": b.sort_order,
                "parent_id": b.parent_id,
                "children": [],
            }
        )
    def build(parent_id):
        nodes = by_parent.get(parent_id, [])
        for n in nodes:
            n["children"] = build(n["id"])
        return nodes
    return build(None)


@router.post("", response_model=BoardOut, status_code=201)
def create_board(payload: BoardCreate, db: Session = Depends(get_db)):
    if payload.parent_id:
        parent = db.get(Board, payload.parent_id)
        if not parent:
            raise HTTPException(404, "parent board not found")
    board = Board(
        name=payload.name,
        parent_id=payload.parent_id,
        kind=payload.kind,
        color=payload.color or _auto_color(),
        sort_order=payload.sort_order,
    )
    db.add(board)
    db.flush()
    _log(db, "board", board.id, "create")
    db.commit()
    db.refresh(board)
    return board


@router.patch("/{board_id}", response_model=BoardOut)
def update_board(board_id: str, payload: BoardUpdate, db: Session = Depends(get_db)):
    board = db.get(Board, board_id)
    if not board:
        raise HTTPException(404, "board not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "parent_id" and v == board.id:
            raise HTTPException(400, "a board cannot be its own parent")
        setattr(board, k, v)
    _log(db, "board", board_id, "update")
    db.commit()
    db.refresh(board)
    return board


@router.delete("/{board_id}", status_code=204)
def delete_board(board_id: str, db: Session = Depends(get_db)):
    board = db.get(Board, board_id)
    if not board:
        raise HTTPException(404, "board not found")
    _log(db, "board", board_id, "delete")
    db.delete(board)  # cascade deletes children + tasks
    db.commit()


def _auto_color() -> str:
    palette = [
        "#3b82f6", "#f97316", "#22c55e", "#a855f7", "#ef4444",
        "#14b8a6", "#eab308", "#ec4899", "#06b6d4", "#8b5cf6",
    ]
    return palette[0]
