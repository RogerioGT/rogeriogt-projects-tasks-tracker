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
from ..models import Board, Event, Task, TaskAcl, User
from ..schemas import BoardOut, TaskCreate, TaskConvertOut, TaskMove, TaskOut, TaskUpdate

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
    q = select(Task).where(Task.deleted_at.is_(None))
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
    if sort == "created_at":
        order = getattr(Task, col).desc()  # newest first
    elif sort == "due_date":
        order = getattr(Task, col).asc().nulls_last()  # undated tasks at the end
    elif sort == "position":
        order = getattr(Task, col).asc()   # 0 = top
    else:
        order = getattr(Task, col).asc()
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
    if not board or board.deleted_at is not None:
        raise HTTPException(404, "board not found")
    if board_permission(db, user, payload.board_id) != "edit":
        raise HTTPException(403, "no edit permission on this board")
    # new tasks go on top: shift existing LIVE tasks in this board down by one
    existing = db.scalars(
        select(Task).where(Task.board_id == payload.board_id, Task.deleted_at.is_(None))
    ).all()
    for t in existing:
        t.position += 1
    task = Task(
        board_id=payload.board_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assignee=payload.assignee,
        due_date=payload.due_date,
        tags=payload.tags,
        position=0,  # top of the board
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
    if not task or task.deleted_at is not None:
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
    if not task or task.deleted_at is not None:
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
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "task not found")
    target = db.get(Board, payload.board_id)
    if not target or target.deleted_at is not None:
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


@router.post("/{task_id}/convert", response_model=TaskConvertOut, status_code=201)
def convert_to_project(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Turn a task into a project board: creates a new board named after the
    task, nested under the task's current board, and moves the task into it.
    The task becomes the first task of the new project; more sub-tasks can be
    added to it like any other board."""
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "task not found")
    if task_permission(db, user, task_id) != "edit":
        raise HTTPException(403, "no edit permission on this task")
    parent = db.get(Board, task.board_id)
    if not parent or parent.deleted_at is not None:
        raise HTTPException(404, "parent board not found")
    if board_permission(db, user, parent.id) != "edit":
        raise HTTPException(403, "no edit permission on the task's board")

    new_board = Board(
        name=task.title[:200],
        parent_id=parent.id,
        kind="project",
        color=parent.color or "#64748b",
        sort_order=0,
        created_by=user.id,
    )
    db.add(new_board)
    db.flush()
    old_board = task.board_id
    task.board_id = new_board.id
    task.position = 0
    _log(db, "board", new_board.id, "create", user_id=user.id,
         field="from_task", new=task.id)
    _log(db, "task", task_id, "convert", user_id=user.id,
         field="board_id", old=old_board, new=new_board.id)
    db.commit()
    db.refresh(task)
    db.refresh(new_board)
    return {"board": new_board, "task": task}


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Soft delete: moves the task to the Trash (restorable for 30 days)."""
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "task not found")
    if task_permission(db, user, task_id) != "edit":
        raise HTTPException(403, "no edit permission on this task")
    _log(db, "task", task_id, "delete", user_id=user.id, new="trash")
    task.deleted_at = datetime.utcnow()
    db.commit()


@router.get("/stats/summary")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(func.count(Task.id)).where(Task.deleted_at.is_(None))
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
