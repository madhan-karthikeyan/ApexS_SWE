from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.sprint import Sprint
from app.models.story import UserStory
from app.schemas.common import SprintCreate, SprintRead, StoryRead

router = APIRouter()


@router.post("/", response_model=SprintRead)
async def create_sprint(payload: SprintCreate, db: AsyncSession = Depends(get_async_db)):
    sprint = Sprint(team_id=payload.team_id, goal=payload.goal, start_date=payload.start_date, end_date=payload.end_date, capacity=payload.capacity, status=payload.status)
    db.add(sprint)
    await db.commit()
    await db.refresh(sprint)
    return SprintRead(sprint_id=sprint.sprint_id, team_id=sprint.team_id, goal=sprint.goal, start_date=sprint.start_date, end_date=sprint.end_date, capacity=sprint.capacity, status=sprint.status)


@router.get("/{sprint_id}", response_model=SprintRead)
async def get_sprint(sprint_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Sprint).where(Sprint.sprint_id == sprint_id))
    sprint = result.scalar_one_or_none()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return SprintRead(sprint_id=sprint.sprint_id, team_id=sprint.team_id, goal=sprint.goal, start_date=sprint.start_date, end_date=sprint.end_date, capacity=sprint.capacity, status=sprint.status)


@router.get("/{sprint_id}/stories", response_model=list[StoryRead])
async def get_sprint_stories(sprint_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(UserStory).where(UserStory.sprint_id == sprint_id))
    stories = result.scalars().all()
    return [StoryRead(story_id=s.story_id, sprint_id=s.sprint_id, title=s.title, description=s.description, story_points=s.story_points, business_value=s.business_value, risk_score=s.risk_score, required_skill=s.required_skill, depends_on=s.depends_on or [], status=s.status) for s in stories]
