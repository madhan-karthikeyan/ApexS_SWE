from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sprint import Sprint
from app.models.story import UserStory
from app.schemas.common import SprintCreate, SprintRead, StoryRead

router = APIRouter()


@router.post("/", response_model=SprintRead)
def create_sprint(payload: SprintCreate, db: Session = Depends(get_db)):
    sprint = Sprint(team_id=payload.team_id, goal=payload.goal, start_date=payload.start_date, end_date=payload.end_date, capacity=payload.capacity, status=payload.status)
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return SprintRead(sprint_id=sprint.sprint_id, team_id=sprint.team_id, goal=sprint.goal, start_date=sprint.start_date, end_date=sprint.end_date, capacity=sprint.capacity, status=sprint.status)


@router.get("/{sprint_id}", response_model=SprintRead)
def get_sprint(sprint_id: str, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.sprint_id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return SprintRead(sprint_id=sprint.sprint_id, team_id=sprint.team_id, goal=sprint.goal, start_date=sprint.start_date, end_date=sprint.end_date, capacity=sprint.capacity, status=sprint.status)


@router.get("/{sprint_id}/stories", response_model=list[StoryRead])
def get_sprint_stories(sprint_id: str, db: Session = Depends(get_db)):
    stories = db.query(UserStory).filter(UserStory.sprint_id == sprint_id).all()
    return [StoryRead(story_id=s.story_id, sprint_id=s.sprint_id, title=s.title, description=s.description, story_points=s.story_points, business_value=s.business_value, risk_score=s.risk_score, required_skill=s.required_skill, depends_on=s.depends_on or [], status=s.status) for s in stories]
