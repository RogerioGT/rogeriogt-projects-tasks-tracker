"""Sharing router: board ACL — share a board with another user (view/edit)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Board, BoardAcl, Event, User
from ..schemas import ShareIn, ShareOut

router = APIRouter(prefix="/api/boards", tags=["sharing"])


@router.get("/{board_id}/acl", response_model=list[ShareOut])
def list_acl(board_id: str, db: Session = Depends(get_db)):
    if not db.get(Board, board_id):
        raise HTTPException(404, "board not found")
    return db.scalars(select(BoardAcl).where(BoardAcl.board_id == board_id)).all()


@router.post("/{board_id}/acl", response_model=ShareOut, status_code=201)
def share_board(
    board_id: str,
    payload: ShareIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    board = db.get(Board, board_id)
    if not board:
        raise HTTPException(404, "board not found")
    if not db.get(User, payload.user_id):
        raise HTTPException(404, "user not found")
    if payload.permission not in ("view", "edit"):
        raise HTTPException(400, "permission must be view or edit")
    # upsert: one ACL row per (board, user)
    existing = db.scalars(
        select(BoardAcl).where(BoardAcl.board_id == board_id, BoardAcl.user_id == payload.user_id)
    ).first()
    if existing:
        existing.permission = payload.permission
        acl = existing
    else:
        acl = BoardAcl(board_id=board_id, user_id=payload.user_id, permission=payload.permission)
        db.add(acl)
    db.flush()
    db.add(Event(entity_type="board", entity_id=board_id, user_id=actor.id,
                 action="share", field="permission", new_value=f"{payload.user_id}:{payload.permission}"))
    db.commit()
    db.refresh(acl)
    return acl


@router.delete("/{board_id}/acl/{user_id}", status_code=204)
def unshare_board(board_id: str, user_id: str, db: Session = Depends(get_db)):
    acl = db.scalars(
        select(BoardAcl).where(BoardAcl.board_id == board_id, BoardAcl.user_id == user_id)
    ).first()
    if not acl:
        raise HTTPException(404, "share not found")
    db.delete(acl)
    db.commit()
