from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.story import UserStory
from app.schemas.common import StoryCreate, StoryRead, StoryUpdate

router = APIRouter()


@router.post("/", response_model=StoryRead)
def create_story(payload: StoryCreate, db: Session = Depends(get_db)):
    story = UserStory(**payload.model_dump())
    db.add(story)
    db.commit()
    db.refresh(story)
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
def get_story(story_id: str, db: Session = Depends(get_db)):
    story = db.query(UserStory).filter(UserStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return StoryRead(story_id=story.story_id, sprint_id=story.sprint_id, title=story.title, description=story.description, story_points=story.story_points, business_value=story.business_value, risk_score=story.risk_score, required_skill=story.required_skill, depends_on=story.depends_on or [], status=story.status)


@router.put("/{story_id}", response_model=StoryRead)
def update_story(story_id: str, payload: StoryUpdate, db: Session = Depends(get_db)):
    story = db.query(UserStory).filter(UserStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(story, field, value)
    db.commit()
    db.refresh(story)
    return StoryRead(story_id=story.story_id, sprint_id=story.sprint_id, title=story.title, description=story.description, story_points=story.story_points, business_value=story.business_value, risk_score=story.risk_score, required_skill=story.required_skill, depends_on=story.depends_on or [], status=story.status)


@router.delete("/{story_id}")
def delete_story(story_id: str, db: Session = Depends(get_db)):
    story = db.query(UserStory).filter(UserStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    db.delete(story)
    db.commit()
    return {"message": "Story deleted"}
