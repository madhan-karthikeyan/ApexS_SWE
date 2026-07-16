from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.team import ScrumTeam
from app.schemas.common import TeamCreate, TeamRead

router = APIRouter()


@router.get("/", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db)):
    teams = db.query(ScrumTeam).all()
    return [TeamRead(team_id=t.team_id, name=t.name, team_size=t.team_size, capacity=t.capacity, skills=t.skills, created_at=t.created_at) for t in teams]


@router.post("/", response_model=TeamRead)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)):
    team = ScrumTeam(name=payload.name, team_size=payload.team_size, capacity=payload.capacity, skills=payload.skills)
    db.add(team)
    db.commit()
    db.refresh(team)
    return TeamRead(team_id=team.team_id, name=team.name, team_size=team.team_size, capacity=team.capacity, skills=team.skills, created_at=team.created_at)


@router.get("/{team_id}", response_model=TeamRead)
def get_team(team_id: str, db: Session = Depends(get_db)):
    team = db.query(ScrumTeam).filter(ScrumTeam.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return TeamRead(team_id=team.team_id, name=team.name, team_size=team.team_size, capacity=team.capacity, skills=team.skills, created_at=team.created_at)
