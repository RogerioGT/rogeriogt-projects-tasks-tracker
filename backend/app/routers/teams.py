"""Teams router (admin-only): create/manage teams and their members."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_admin
from ..models import BoardAcl, TaskAcl, Team, TeamMember, User
from ..schemas import (
    TeamCreate,
    TeamMemberIn,
    TeamMemberOut,
    TeamOut,
    TeamUpdate,
    TeamWithMembers,
)

router = APIRouter(prefix="/api/teams", tags=["teams"], dependencies=[Depends(get_current_admin)])


def _team_with_members(db: Session, team: Team) -> TeamWithMembers:
    members = db.scalars(select(TeamMember).where(TeamMember.team_id == team.id)).all()
    return TeamWithMembers(
        id=team.id,
        name=team.name,
        created_by=team.created_by,
        created_at=team.created_at,
        members=[TeamMemberOut.model_validate(m) for m in members],
    )


@router.get("", response_model=list[TeamWithMembers])
def list_teams(db: Session = Depends(get_db)):
    teams = db.scalars(select(Team).order_by(Team.name)).all()
    return [_team_with_members(db, t) for t in teams]


@router.post("", response_model=TeamOut, status_code=201)
def create_team(payload: TeamCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if db.scalars(select(Team).where(Team.name == payload.name.strip())).first():
        raise HTTPException(409, "team name already exists")
    team = Team(name=payload.name.strip(), created_by=admin.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.patch("/{team_id}", response_model=TeamOut)
def rename_team(team_id: str, payload: TeamUpdate, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(404, "team not found")
    if payload.name is not None:
        team.name = payload.name.strip()
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: str, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(404, "team not found")
    # FK cleanup first (foreign_keys pragma is ON): members + shares referencing
    # this team, otherwise the team row cannot be deleted.
    for m in db.scalars(select(TeamMember).where(TeamMember.team_id == team_id)).all():
        db.delete(m)
    for acl in db.scalars(select(BoardAcl).where(BoardAcl.team_id == team_id)).all():
        db.delete(acl)
    for acl in db.scalars(select(TaskAcl).where(TaskAcl.team_id == team_id)).all():
        db.delete(acl)
    db.flush()  # delete children before the parent (no ORM relationship defined)
    db.delete(team)
    db.commit()


@router.post("/{team_id}/members", response_model=TeamMemberOut, status_code=201)
def add_member(team_id: str, payload: TeamMemberIn, db: Session = Depends(get_db)):
    if not db.get(Team, team_id):
        raise HTTPException(404, "team not found")
    if not db.get(User, payload.user_id):
        raise HTTPException(404, "user not found")
    existing = db.scalars(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == payload.user_id)
    ).first()
    if existing:
        raise HTTPException(409, "user is already a member")
    if payload.role not in ("member", "admin"):
        raise HTTPException(400, "role must be member or admin")
    member = TeamMember(team_id=team_id, user_id=payload.user_id, role=payload.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{team_id}/members/{user_id}", status_code=204)
def remove_member(team_id: str, user_id: str, db: Session = Depends(get_db)):
    member = db.scalars(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).first()
    if not member:
        raise HTTPException(404, "member not found")
    db.delete(member)
    db.commit()
