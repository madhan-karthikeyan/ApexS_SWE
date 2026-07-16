from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
	"apex_sprint_planner",
	broker=settings.redis_url,
	backend=settings.redis_url,
	include=["app.workers.planning_task"],
)
celery_app.conf.update(
	task_always_eager=False,
	task_track_started=True,
	task_serializer="json",
	result_serializer="json",
	accept_content=["json"],
)
