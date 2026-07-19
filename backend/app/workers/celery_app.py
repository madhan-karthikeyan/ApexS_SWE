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
	task_acks_late=True,
	task_reject_on_worker_lost=True,
	task_soft_time_limit=600,
	task_time_limit=660,
	broker_transport_options={
		"max_retries": 3,
		"interval_start": 5,
		"interval_step": 10,
		"interval_max": 60,
	},
	result_expires=86400,
)
