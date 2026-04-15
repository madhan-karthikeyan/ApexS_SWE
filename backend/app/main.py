from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import auth, teams, datasets, sprints, stories, plans, reports
from app.api.v1.context import router as context_router
from app.core.config import settings, get_cors_origins
from app.core.database import Base, engine
from app.core.minio_client import ensure_bucket
from app.models.team import ScrumTeam
from app.workers.planning_task import celery_app

try:
    import redis
except Exception:  # pragma: no cover
    redis = None

app = FastAPI(title="Explainable Sprint Planner API", version="1.0.0")
logger = logging.getLogger("apexs.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_START_TS = time.time()
_REQUEST_COUNT = 0

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["Teams"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(sprints.router, prefix="/api/v1/sprints", tags=["Sprints"])
app.include_router(stories.router, prefix="/api/v1/stories", tags=["Stories"])
app.include_router(plans.router, prefix="/api/v1/plans", tags=["Plans"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(context_router, prefix="/api/v1/context", tags=["Context"])


@app.middleware("http")
async def request_log_middleware(request, call_next):
    global _REQUEST_COUNT
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    _REQUEST_COUNT += 1
    logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.on_event("startup")
def startup_event():
    # Keep local/dev startup resilient by creating schema when migrations are absent.
    Base.metadata.create_all(bind=engine)
    ensure_bucket()
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        default_team_id = "00000000-0000-0000-0000-000000000001"
        try:
            existing = db.query(ScrumTeam).filter(ScrumTeam.team_id == default_team_id).first()
            if not existing:
                db.add(ScrumTeam(team_id=default_team_id, name="ApexS Default Team", team_size=5, capacity=30, skills=["Backend", "Frontend", "Database", "Testing"]))
                db.commit()
        except Exception:
            # In production, schema should be created via Alembic before startup.
            db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Explainable Sprint Planner API"}


@app.get("/health")
def health():
    db_ok = True
    redis_ok = True
    minio_ok = ensure_bucket()

    try:
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_ok = False

    if redis is not None:
        try:
            redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1).ping()
        except Exception:
            redis_ok = False

    checks = {
        "database": db_ok,
        "redis": redis_ok,
        "minio": minio_ok,
        "celery_enabled": bool(settings.use_celery and celery_app is not None),
    }
    status = "ok" if db_ok and minio_ok and (redis_ok or not settings.use_celery) else "degraded"
    return {
        "status": status,
        "checks": checks,
        "uptime_seconds": int(time.time() - _START_TS),
        "request_count": _REQUEST_COUNT,
    }
