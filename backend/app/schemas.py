"""Pydantic schemas (request/response validation)."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    entity_type: str
    entity_id: str
    user_id: str | None
    action: str
    field: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime


# --- Auth / Users ---
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str
    locale: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class RegisterIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    name: str = Field("", max_length=120)
    password: str = Field(..., min_length=4, max_length=128)


class LoginIn(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# --- Sharing ---
class ShareIn(BaseModel):
    """Share a board subtree with a user OR a team."""
    user_id: str | None = None
    team_id: str | None = None
    permission: str = "edit"  # view | edit

    @model_validator(mode="after")
    def _check_target(self):
        if not self.user_id and not self.team_id:
            raise ValueError("user_id or team_id is required")
        if self.user_id and self.team_id:
            raise ValueError("provide user_id OR team_id, not both")
        return self


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    board_id: str
    user_id: str | None
    team_id: str | None
    permission: str
    created_at: datetime


class TaskShareIn(BaseModel):
    user_id: str | None = None
    team_id: str | None = None
    permission: str = "edit"

    @model_validator(mode="after")
    def _check_target(self):
        if not self.user_id and not self.team_id:
            raise ValueError("user_id or team_id is required")
        if self.user_id and self.team_id:
            raise ValueError("provide user_id OR team_id, not both")
        return self


class TaskShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    user_id: str | None
    team_id: str | None
    permission: str
    created_at: datetime


class BatchTaskShareIn(BaseModel):
    task_ids: list[str] = Field(..., min_length=1)
    user_id: str | None = None
    team_id: str | None = None
    permission: str = "edit"


# --- Teams ---
class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)


class TeamMemberIn(BaseModel):
    user_id: str
    role: str = "member"  # member | admin


class TeamMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    team_id: str
    user_id: str
    role: str
    created_at: datetime


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    created_by: str | None
    created_at: datetime


class TeamWithMembers(BaseModel):
    id: str
    name: str
    created_by: str | None
    created_at: datetime
    members: list[TeamMemberOut]


# --- Admin user management ---
class UserCreateIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    name: str = Field("", max_length=120)
    password: str = Field(..., min_length=4, max_length=128)
    is_admin: bool = False


class UserUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = Field(default=None, min_length=4, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=4, max_length=128)
