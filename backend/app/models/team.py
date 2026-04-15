from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class ScrumTeam(Base):
    __tablename__ = "scrum_teams"

    team_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    team_size: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sprints = relationship("Sprint", back_populates="team", cascade="all, delete-orphan")
    contexts = relationship("Context", back_populates="team", cascade="all, delete-orphan")
    uploads = relationship("DatasetUpload", back_populates="team", cascade="all, delete-orphan")
