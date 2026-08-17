"""Pydantic schemas (request/response validation)."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --- Boards ---
class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: str | None = None
    kind: str = "project"
    color: str | None = None
    sort_order: int = 0


class BoardUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    kind: str | None = None
    color: str | None = None
    sort_order: int | None = None


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    parent_id: str | None
    name: str
    kind: str
    color: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


# --- Tasks ---
class TaskCreate(BaseModel):
    board_id: str
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    status: str = "not_started"
    priority: str = "none"
    assignee: str | None = None
    due_date: date | None = None
    tags: list[str] | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee: str | None = None
    due_date: date | None = None
    tags: list[str] | None = None
    position: int | None = None
    board_id: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    board_id: str
    title: str
    description: str | None
    status: str
    priority: str
    assignee: str | None
    due_date: date | None
    tags: list[str] | None
    position: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskMove(BaseModel):
    board_id: str
    position: int | None = None
