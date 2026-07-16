from __future__ import annotations

from io import BytesIO
from threading import Lock
from typing import Any
from uuid import uuid4

import pandas as pd

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.minio_client import read_bytes
from app.models import Context, DatasetUpload, SprintPlan, UserStory
from app.services.context_extractor import ContextExtractor
from app.services.explainability_engine import ExplainabilityEngine
from app.services.optimization_engine import OptimizationEngine
from app.services.preprocessing import normalize_skill, normalize_status, parse_depends_on
from app.services.weight_learning import WeightLearningModel

run_sprint_planning: Any = None

try:
    from .celery_app import celery_app
except Exception:  # pragma: no cover
    celery_app = None

try:
    from celery.result import AsyncResult
except Exception:  # pragma: no cover
    AsyncResult = None

_JOB_STORE: dict[str, dict[str, Any]] = {}
_JOB_LOCK = Lock()


def set_job_state(job_id: str, status: str, progress: int, step: str, plan_id: str | None = None, error: str | None = None):
    with _JOB_LOCK:
        _JOB_STORE[job_id] = {"status": status, "progress": progress, "step": step, "plan_id": plan_id, "error": error}


def get_job_state(job_id: str):
    with _JOB_LOCK:
        local = _JOB_STORE.get(job_id)
    if local:
        return local

    if celery_app is not None and AsyncResult is not None:
        result = AsyncResult(job_id, app=celery_app)
        state = result.state or "PENDING"
        info = result.info if isinstance(result.info, dict) else {}

        if state == "PENDING":
            return {"status": "pending", "progress": 0, "step": "Queued", "plan_id": None, "error": None}
        if state in {"STARTED", "PROGRESS"}:
            return {
                "status": "processing",
                "progress": int(info.get("progress", 0)),
                "step": str(info.get("step", "Processing")),
                "plan_id": info.get("plan_id"),
                "error": None,
            }
        if state == "SUCCESS":
            payload = result.result if isinstance(result.result, dict) else {}
            return {
                "status": "complete",
                "progress": int(payload.get("progress", 100)),
                "step": "done",
                "plan_id": payload.get("plan_id"),
                "error": None,
            }
        return {
            "status": "failed",
            "progress": 100,
            "step": "failed",
            "plan_id": None,
            "error": str(result.result or result.info or "Unknown task error"),
        }

    return {"status": "pending", "progress": 0, "step": "Queued", "plan_id": None, "error": None}


def load_dataset(dataset_path: str) -> pd.DataFrame:
    if dataset_path.startswith("s3://"):
        dataset_path = dataset_path.split("s3://", 1)[1]
        bucket, key = dataset_path.split("/", 1)
        data = read_bytes(key)
        return pd.read_csv(BytesIO(data))
    if dataset_path.endswith(".csv"):
        return pd.read_csv(dataset_path)
    return pd.DataFrame()


def load_team_historical_dataset(team_id: str, db, include_path: str | None = None) -> pd.DataFrame:
    uploads = (
        db.query(DatasetUpload)
        .filter(DatasetUpload.team_id == team_id)
        .order_by(DatasetUpload.uploaded_at.asc())
        .all()
    )

    frames: list[pd.DataFrame] = []
    seen_paths: set[str] = set()

    for upload in uploads:
        path = upload.file_path
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        try:
            frame = load_dataset(path)
        except Exception:
            continue
        if frame.empty:
            continue
        frame = frame.copy()
        frame["_source_upload_id"] = upload.upload_id
        frames.append(frame)

    if not frames and include_path:
        try:
            fallback = load_dataset(include_path)
            if not fallback.empty:
                frames.append(fallback)
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    if {"story_id", "sprint_id"}.issubset(set(combined.columns)):
        combined = combined.drop_duplicates(subset=["story_id", "sprint_id"], keep="last")
    elif "story_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["story_id"], keep="last")

    return combined


def load_stories_from_db(sprint_id: str, db=None) -> list[UserStory]:
    session = db or SessionLocal()
    try:
        return session.query(UserStory).filter(UserStory.sprint_id == sprint_id).all()
    finally:
        if db is None:
            session.close()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _to_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def _chunked(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upsert_sprint_stories_from_dataset(sprint_id: str, df: pd.DataFrame, db, progress_callback=None) -> int:
    required = {"story_id", "story_points", "business_value", "risk_score"}
    if not required.issubset(set(df.columns)):
        return 0

    rows = df.to_dict(orient="records")
    latest_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        story_id = _to_str(row.get("story_id"))
        if story_id:
            latest_by_id[story_id] = row

    story_ids = list(latest_by_id.keys())
    if not story_ids:
        return 0

    if progress_callback is not None:
        progress_callback(22, "syncing_lookup")

    existing_ids: set[str] = set()
    for chunk in _chunked(story_ids, 3000):
        chunk_rows = db.query(UserStory.story_id).filter(UserStory.story_id.in_(chunk)).all()
        for (existing_id,) in chunk_rows:
            existing_ids.add(existing_id)

    if progress_callback is not None:
        progress_callback(28, "syncing_prepare")

    insert_mappings: list[dict[str, Any]] = []
    update_mappings: list[dict[str, Any]] = []
    upserted = 0
    total_ids = len(story_ids)
    for idx, (story_id, row) in enumerate(latest_by_id.items(), start=1):
        title = _to_str(row.get("title"), f"Story {story_id}")

        payload = {
            "story_id": story_id,
            "sprint_id": sprint_id,
            "title": title,
            "description": _to_str(row.get("description"), "") or None,
            "story_points": max(_to_int(row.get("story_points"), 1), 1),
            "business_value": _to_float(row.get("business_value"), 0.0),
            "risk_score": _to_float(row.get("risk_score"), 0.0),
            # Normalize skill/status/dependency fields at ingestion for consistent downstream behavior.
            "required_skill": normalize_skill(_to_str(row.get("required_skill"), "")),
            "depends_on": parse_depends_on(row.get("depends_on")),
            "status": normalize_status(_to_str(row.get("status"), "backlog")) or "backlog",
        }

        if story_id in existing_ids:
            update_mappings.append(payload)
        else:
            insert_mappings.append(payload)
        upserted += 1

        if progress_callback is not None and (idx % 10000 == 0 or idx == total_ids):
            ratio = idx / total_ids if total_ids else 1.0
            progress = 28 + int(ratio * 5)
            progress_callback(min(progress, 33), "syncing_prepare")

    if progress_callback is not None:
        progress_callback(34, "syncing_write")

    if insert_mappings:
        db.bulk_insert_mappings(UserStory, insert_mappings)
    if update_mappings:
        db.bulk_update_mappings(UserStory, update_mappings)

    db.commit()
    return upserted


def save_plan_to_db(sprint_id: str, result, explanations, weights, db=None):
    session = db or SessionLocal()
    try:
        plan = SprintPlan(
            sprint_id=sprint_id,
            selected_stories=[s.story_id for s in result.selected_stories],
            total_value=result.total_value,
            total_risk=result.total_risk,
            capacity_used=result.capacity_used,
            status="draft",
        )
        session.add(plan)
        session.flush()
        for exp in explanations:
            exp.plan_id = plan.plan_id
            session.add(exp)
        session.commit()
        session.refresh(plan)
        return plan.plan_id
    finally:
        if db is None:
            session.close()


def execute_planning_pipeline(
    sprint_id: str,
    team_id: str,
    dataset_path: str,
    capacity: int,
    risk_threshold: float,
    available_skills: list[str],
    job_id: str | None = None,
    progress_callback=None,
):
    db = SessionLocal()

    def report(status: str, progress: int, step: str, plan_id: str | None = None, error: str | None = None):
        if progress_callback is not None:
            progress_callback(status, progress, step, plan_id=plan_id, error=error)
        if job_id:
            set_job_state(job_id, status, progress, step, plan_id=plan_id, error=error)

    try:
        report("processing", 10, "loading")
        latest_df = load_dataset(dataset_path)
        report("processing", 20, "syncing_stories")
        upsert_sprint_stories_from_dataset(
            sprint_id,
            latest_df,
            db,
            progress_callback=lambda progress, step: report("processing", progress, step),
        )

        report("processing", 35, "loading_history")
        historical_df = load_team_historical_dataset(team_id, db=db, include_path=dataset_path)
        learning_df = historical_df if not historical_df.empty else latest_df

        report("processing", 50, "extracting")
        context = ContextExtractor().extract(learning_df, capacity)
        context_row = Context(team_id=team_id, urgency_weight=context.urgency_weight, value_weight=context.value_weight, alignment_weight=context.alignment_weight)
        db.add(context_row)
        db.commit()

        report("processing", 65, "learning")
        weights = WeightLearningModel().train(learning_df, context)
        report("processing", 80, "optimizing")
        stories = load_stories_from_db(sprint_id, db=db)
        result = OptimizationEngine().solve(stories, weights, capacity, risk_threshold, available_skills)
        report("processing", 90, "explaining")
        explanations = ExplainabilityEngine().generate(result, weights)
        plan_id = save_plan_to_db(sprint_id, result, explanations, weights, db=db)
        report("complete", 100, "done", plan_id=str(plan_id))
        return {"status": "SUCCESS", "plan_id": str(plan_id), "progress": 100}
    except Exception as exc:
        report("failed", 100, "failed", error=str(exc))
        raise
    finally:
        db.close()


if celery_app is not None:
    @celery_app.task(bind=True, name="run_sprint_planning")
    def run_sprint_planning(self, sprint_id: str, team_id: str, dataset_path: str, capacity: int, risk_threshold: float, available_skills: list[str]):
        def task_progress(status: str, progress: int, step: str, plan_id: str | None = None, error: str | None = None):
            meta = {"status": status, "progress": progress, "step": step, "plan_id": plan_id, "error": error}
            if status == "failed":
                self.update_state(state="FAILURE", meta=meta)
            elif status == "complete":
                self.update_state(state="SUCCESS", meta=meta)
            else:
                self.update_state(state="PROGRESS", meta=meta)

        return execute_planning_pipeline(
            sprint_id,
            team_id,
            dataset_path,
            capacity,
            risk_threshold,
            available_skills,
            job_id=getattr(self.request, "id", None),
            progress_callback=task_progress,
        )


def run_async_job(sprint_id: str, team_id: str, dataset_path: str, capacity: int, risk_threshold: float, available_skills: list[str]) -> str:
    if celery_app is not None and settings.use_celery and run_sprint_planning is not None:
        try:
            delay_fn = getattr(run_sprint_planning, "delay", None)
            if not callable(delay_fn):
                raise RuntimeError("Celery task dispatcher is unavailable")
            async_result = delay_fn(sprint_id, team_id, dataset_path, capacity, risk_threshold, available_skills)
            return async_result.id
        except Exception as exc:
            if not settings.allow_thread_fallback:
                raise RuntimeError("Failed to enqueue planning task in Celery") from exc

    if settings.use_celery and celery_app is None and not settings.allow_thread_fallback:
        raise RuntimeError("Celery is enabled but unavailable")

    if settings.use_celery and not settings.allow_thread_fallback:
        raise RuntimeError("Celery dispatch unavailable and thread fallback is disabled")

    job_id = str(uuid4())
    set_job_state(job_id, "processing", 0, "Queued")
    from threading import Thread

    thread = Thread(
        target=execute_planning_pipeline,
        args=(sprint_id, team_id, dataset_path, capacity, risk_threshold, available_skills, job_id),
        daemon=True,
    )
    thread.start()
    return job_id
