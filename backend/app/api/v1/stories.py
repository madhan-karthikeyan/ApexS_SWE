from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.story import UserStory
from app.schemas.common import StoryCreate, StoryRead, StoryUpdate

router = APIRouter()


@router.post("/", response_model=StoryRead)
async def create_story(payload: StoryCreate, db: AsyncSession = Depends(get_async_db)):
    story = UserStory(**payload.model_dump())
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return StoryRead(**{
        "story_id": story.story_id,
        "sprint_id": story.sprint_id,
        "title": story.title,
        "description": story.description,
        "story_points": story.story_points,
        "business_value": story.business_value,
        "risk_score": story.risk_score,
        "required_skill": story.required_skill,
        "depends_on": story.depends_on or [],
        "status": story.status,
    })


@router.get("/{story_id}", response_model=StoryRead)
async def get_story(story_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(UserStory).where(UserStory.story_id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return StoryRead(story_id=story.story_id, sprint_id=story.sprint_id, title=story.title, description=story.description, story_points=story.story_points, business_value=story.business_value, risk_score=story.risk_score, required_skill=story.required_skill, depends_on=story.depends_on or [], status=story.status)


@router.put("/{story_id}", response_model=StoryRead)
async def update_story(story_id: str, payload: StoryUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(UserStory).where(UserStory.story_id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(story, field, value)
    await db.commit()
    await db.refresh(story)
    return StoryRead(story_id=story.story_id, sprint_id=story.sprint_id, title=story.title, description=story.description, story_points=story.story_points, business_value=story.business_value, risk_score=story.risk_score, required_skill=story.required_skill, depends_on=story.depends_on or [], status=story.status)


@router.delete("/{story_id}")
async def delete_story(story_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(UserStory).where(UserStory.story_id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    await db.delete(story)
    await db.commit()
    return {"message": "Story deleted"}
