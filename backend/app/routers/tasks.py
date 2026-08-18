"""Tasks router: CRUD + sort/filter + complete + move."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Board, Event, Task
from ..schemas import TaskCreate, TaskMove, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])

SORTABLE = {"created_at", "updated_at", "due_date", "priority", "status", "position", "title"}


def _log(db: Session, entity: str, eid: str, action: str, field=None, old=None, new=None):
    db.add(Event(entity_type=entity, entity_id=eid, action=action, field=field,
                 old_value=old, new_value=new))


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
    sort: str = "position",
    db: Session = Depends(get_db),
):
    q = select(Task)
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

    col = sort if sort in SORTABLE else "position"
    if col in ("priority", "status"):
        # fixed semantic order for these, else alphabetical
        pass
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
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    if not db.get(Board, payload.board_id):
        raise HTTPException(404, "board not found")
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
    )
    db.add(task)
    db.flush()
    _log(db, "task", task.id, "create", new=payload.title)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "status" and v == "done" and task.status != "done":
            task.completed_at = datetime.utcnow()
        elif k == "status" and v != "done":
            task.completed_at = None
        setattr(task, k, v)
    _log(db, "task", task_id, "update")
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/complete", response_model=TaskOut)
def toggle_complete(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task.status == "done":
        task.status = "not_started"
        task.completed_at = None
        action = "reopen"
    else:
        task.status = "done"
        task.completed_at = datetime.utcnow()
        action = "complete"
    _log(db, "task", task_id, action, field="status")
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/move", response_model=TaskOut)
def move_task(task_id: str, payload: TaskMove, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if not db.get(Board, payload.board_id):
        raise HTTPException(404, "board not found")
    old_board = task.board_id
    task.board_id = payload.board_id
    if payload.position is not None:
        task.position = payload.position
    _log(db, "task", task_id, "move", field="board_id", old=old_board, new=payload.board_id)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    _log(db, "task", task_id, "delete")
    db.delete(task)
    db.commit()


@router.get("/stats/summary")
def stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Task.id))) or 0
    done = db.scalar(select(func.count(Task.id)).where(Task.status == "done")) or 0
    waiting = db.scalar(select(func.count(Task.id)).where(Task.status == "waiting")) or 0
    in_progress = db.scalar(select(func.count(Task.id)).where(Task.status == "in_progress")) or 0
    not_started = db.scalar(select(func.count(Task.id)).where(Task.status == "not_started")) or 0
    return {
        "total": total,
        "done": done,
        "waiting": waiting,
        "in_progress": in_progress,
        "not_started": not_started,
        "completion_rate": round(done / total * 100, 1) if total else 0,
    }
