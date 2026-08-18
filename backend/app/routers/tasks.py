"""Tasks router: CRUD + sort/filter + complete + move.

Enforces visibility (list shows only tasks the user can see) and edit
permission (create/update/complete/move/delete require edit access).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..access import board_permission, task_permission, visible_task_ids
from ..db import get_db
from ..deps import get_current_user
from ..models import Board, Event, Task, User
from ..schemas import TaskCreate, TaskMove, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

SORTABLE = {"created_at", "updated_at", "due_date", "priority", "status", "position", "title"}


def _log(db: Session, entity: str, eid: str, action: str, user_id=None, field=None, old=None, new=None):
    db.add(Event(entity_type=entity, entity_id=eid, user_id=user_id, action=action,
                 field=field, old_value=old, new_value=new))


def _board_ids_under(db: Session, board_id: str) -> list[str]:
    """Return board_id plus all descendant board ids (for 'show tasks in whole company')."""
    ids = [board_id]
    frontier = [board_id]
    while frontier:
        children = db.scalars(select(Board.id).where(Board.parent_id.in_(frontier))).all()
        if not children:
            break
        ids.extend(children)
        frontier = list(children)
    return ids


@router.get("", response_model=list[TaskOut])
def list_tasks(
    board_id: str | None = None,
    include_descendants: bool = False,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    search: str | None = None,
    due_before: str | None = None,
    due_after: str | None = None,
    sort: str = "position",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Task)
    visible = visible_task_ids(db, user)
    if visible is not None:
        q = q.where(Task.id.in_(visible))
    if board_id:
        if include_descendants:
            q = q.where(Task.board_id.in_(_board_ids_under(db, board_id)))
        else:
            q = q.where(Task.board_id == board_id)
    if status:
        q = q.where(Task.status == status)
    if priority:
        q = q.where(Task.priority == priority)
    if assignee:
        q = q.where(Task.assignee == assignee)
    if search:
        q = q.where(Task.title.ilike(f"%{search}%"))
    if due_before:
        q = q.where(Task.due_date <= due_before)
    if due_after:
        q = q.where(Task.due_date >= due_after)

    col = sort if sort in SORTABLE else "position"
    order = getattr(Task, col)
    if sort == "created_at":
        order = order.desc()  # newest first
    elif sort == "position":
        order = order.asc()   # 0 = top
    else:
        order = order.asc()
    q = q.order_by(order)

    # semantic ordering for priority/status handled in Python for clarity
    tasks = db.scalars(q).all()
    if sort == "priority":
        prio = {"high": 0, "medium": 1, "low": 2, "none": 3}
        tasks = sorted(tasks, key=lambda t: prio.get(t.priority, 3))
    elif sort == "status":
        st = {"in_progress": 0, "waiting": 1, "not_started": 2, "done": 3}
        tasks = sorted(tasks, key=lambda t: st.get(t.status, 3))
    return tasks


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    board = db.get(Board, payload.board_id)
    if not board:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, payload.board_id) != "edit":
        raise HTTPException(403, "no edit permission on this board")
    task = Task(
        board_id=payload.board_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assignee=payload.assignee,
        due_date=payload.due_date,
        tags=payload.tags,
        position=0,  # new tasks always on top
        created_by=user.id,
    )
    db.add(task)
    db.flush()
    _log(db, "task", task.id, "create", user_id=user.id, new=payload.title)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task_permission(db, user, task_id) != "edit":
        raise HTTPException(403, "no edit permission on this task")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "status" and v == "done" and task.status != "done":
            task.completed_at = datetime.utcnow()
        elif k == "status" and v != "done":
            task.completed_at = None
        setattr(task, k, v)
    task.updated_by = user.id
    _log(db, "task", task_id, "update", user_id=user.id)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/complete", response_model=TaskOut)
def toggle_complete(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task_permission(db, user, task_id) != "edit":
        raise HTTPException(403, "no edit permission on this task")
    if task.status == "done":
        task.status = "not_started"
        task.completed_at = None
        action = "reopen"
    else:
        task.status = "done"
        task.completed_at = datetime.utcnow()
        action = "complete"
    _log(db, "task", task_id, action, user_id=user.id, field="status")
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/move", response_model=TaskOut)
def move_task(task_id: str, payload: TaskMove, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if not db.get(Board, payload.board_id):
        raise HTTPException(404, "board not found")
    if task_permission(db, user, task_id) != "edit":
        raise HTTPException(403, "no edit permission on this task")
    if board_permission(db, user, payload.board_id) != "edit":
        raise HTTPException(403, "no edit permission on target board")
    old_board = task.board_id
    task.board_id = payload.board_id
    if payload.position is not None:
        task.position = payload.position
    _log(db, "task", task_id, "move", user_id=user.id, field="board_id", old=old_board, new=payload.board_id)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task_permission(db, user, task_id) != "edit":
        raise HTTPException(403, "no edit permission on this task")
    _log(db, "task", task_id, "delete", user_id=user.id)
    db.delete(task)
    db.commit()


@router.get("/stats/summary")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(func.count(Task.id))
    visible = visible_task_ids(db, user)
    if visible is not None:
        q = q.where(Task.id.in_(visible))
    total = db.scalar(q) or 0
    done = db.scalar(q.where(Task.status == "done")) or 0
    waiting = db.scalar(q.where(Task.status == "waiting")) or 0
    in_progress = db.scalar(q.where(Task.status == "in_progress")) or 0
    not_started = db.scalar(q.where(Task.status == "not_started")) or 0
    return {
        "total": total,
        "done": done,
        "waiting": waiting,
        "in_progress": in_progress,
        "not_started": not_started,
        "completion_rate": round(done / total * 100, 1) if total else 0,
    }
