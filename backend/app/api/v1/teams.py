from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.team import ScrumTeam
from app.schemas.common import TeamCreate, TeamRead

router = APIRouter()


@router.get("/", response_model=list[TeamRead])
async def list_teams(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(ScrumTeam))
    teams = result.scalars().all()
    return [TeamRead(team_id=t.team_id, name=t.name, team_size=t.team_size, capacity=t.capacity, skills=t.skills, created_at=t.created_at) for t in teams]


@router.post("/", response_model=TeamRead)
async def create_team(payload: TeamCreate, db: AsyncSession = Depends(get_async_db)):
    team = ScrumTeam(name=payload.name, team_size=payload.team_size, capacity=payload.capacity, skills=payload.skills)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return TeamRead(team_id=team.team_id, name=team.name, team_size=team.team_size, capacity=team.capacity, skills=team.skills, created_at=team.created_at)


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(team_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(ScrumTeam).where(ScrumTeam.team_id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return TeamRead(team_id=team.team_id, name=team.name, team_size=team.team_size, capacity=team.capacity, skills=team.skills, created_at=team.created_at)
