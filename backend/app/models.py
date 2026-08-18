"""SQLAlchemy models. Future-proofed for multi-user, sharing, and history."""
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(5), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Board(Base):
    """A container: Section, Company, Project, or Sub-project.

    Nests via parent_id for unlimited hierarchy. parent_id == None -> top-level Section.
    """

    __tablename__ = "boards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("boards.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="project")  # section|company|project
    color: Mapped[str] = mapped_column(String(16), default="#64748b")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    parent: Mapped["Board | None"] = relationship(
        "Board", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Board"]] = relationship(
        "Board", back_populates="parent", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="board", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    board_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("boards.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # not_started | in_progress | waiting | done
    status: Mapped[str] = mapped_column(String(20), default="not_started")
    # high | medium | low | none
    priority: Mapped[str] = mapped_column(String(10), default="none")
    assignee: Mapped[str | None] = mapped_column(String(120), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)  # 0 = top (newest)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    board: Mapped["Board"] = relationship("Board", back_populates="tasks")


class Event(Base):
    """Audit history: who changed what, when. Append-only."""

    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_type: Mapped[str] = mapped_column(String(20))  # task | board
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(40))  # create|update|complete|move|delete
    field: Mapped[str | None] = mapped_column(String(40), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class BoardAcl(Base):
    """Sharing: which user OR team has what access to which board subtree."""

    __tablename__ = "board_acl"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    board_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("boards.id"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    team_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("teams.id"), nullable=True, index=True
    )
    permission: Mapped[str] = mapped_column(String(10), default="view")  # view | edit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Status(Base):
    """A workflow status option. Admins and users can add their own; the 4
    defaults are seeded. Tasks store the status NAME as a free string, so
    deleting a status does not break existing tasks."""

    __tablename__ = "statuses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="#64748b")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Team(Base):
    """A named group of users the admin shares boards/tasks with."""

    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class TeamMember(Base):
    __tablename__ = "team_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(10), default="member")  # member | admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class TaskAcl(Base):
    """Sharing for a single task (user or team), independent of the board tree."""

    __tablename__ = "task_acl"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    team_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("teams.id"), nullable=True, index=True
    )
    permission: Mapped[str] = mapped_column(String(10), default="view")  # view | edit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
