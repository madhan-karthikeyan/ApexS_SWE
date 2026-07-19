from __future__ import annotations

from io import BytesIO

import pandas as pd

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.minio_client import read_bytes
from app.core.security import require_roles
from app.models.context import Context
from app.models.dataset_upload import DatasetUpload
from app.models.plan import SprintPlan
from app.models.sprint import Sprint
from app.models.story import UserStory
from app.schemas.common import MetricsRead
from app.services.context_extractor import ContextExtractor
from app.services.weight_learning import WeightLearningModel

try:
    from ortools.sat.python import cp_model as _cp_model
except Exception:  # pragma: no cover
    _cp_model = None

try:
    import fastapi_users as _fastapi_users  # noqa: F401
    FASTAPI_USERS_ENABLED = True
except Exception:  # pragma: no cover
    FASTAPI_USERS_ENABLED = False

router = APIRouter()


@router.get("/{team_id}/metrics", response_model=MetricsRead)
async def get_metrics(team_id: str, db: AsyncSession = Depends(get_async_db), _=Depends(require_roles("scrum_master", "product_owner"))):
    result = await db.execute(
        select(Sprint).where(Sprint.team_id == team_id).order_by(Sprint.created_at.asc())
    )
    sprints = result.scalars().all()
    velocities = []
    values = []
    weight_evolution = []
    for sprint in sprints[-5:]:
        result = await db.execute(
            select(UserStory).where(UserStory.sprint_id == sprint.sprint_id)
        )
        stories = result.scalars().all()
        velocities.append(float(sum(s.story_points for s in stories)))
        values.append(float(sum(s.business_value for s in stories)))
        result = await db.execute(
            select(Context).where(Context.team_id == team_id).order_by(Context.computed_at.asc()).limit(1)
        )
        context = result.scalar_one_or_none()
        if context:
            weight_evolution.append({"urgency_weight": context.urgency_weight, "value_weight": context.value_weight, "alignment_weight": context.alignment_weight})

    result = await db.execute(
        select(UserStory)
        .join(Sprint, Sprint.sprint_id == UserStory.sprint_id)
        .where(Sprint.team_id == team_id, UserStory.status == "backlog")
    )
    selected = result.scalars().all()
    risk_selected = sum(s.risk_score for s in selected) / max(len(selected), 1)
    risk_rejected = max((s.risk_score for s in selected), default=0.0)

    learning_sample_count = 0
    learning_dataset_sources_count = 0
    learning_mae = None
    learning_r2 = None
    learning_feature_importance: dict[str, float] = {}
    learning_model_type = "unknown"

    result = await db.execute(
        select(DatasetUpload)
        .where(DatasetUpload.team_id == team_id)
        .order_by(DatasetUpload.uploaded_at.desc())
        .limit(1)
    )
    latest_dataset = result.scalar_one_or_none()
    if latest_dataset and latest_dataset.file_path:
        try:
            result = await db.execute(
                select(DatasetUpload)
                .where(DatasetUpload.team_id == team_id)
                .order_by(DatasetUpload.uploaded_at.asc())
            )
            uploads = result.scalars().all()
            frames: list[pd.DataFrame] = []
            seen_paths: set[str] = set()
            for upload in uploads:
                if not upload.file_path or upload.file_path in seen_paths:
                    continue
                seen_paths.add(upload.file_path)
                if upload.file_path.startswith("s3://"):
                    key = upload.file_path.split("s3://", 1)[1].split("/", 1)[1]
                    data = read_bytes(key)
                    frame = pd.read_csv(BytesIO(data))
                else:
                    frame = pd.read_csv(upload.file_path)
                if frame.empty:
                    continue
                frames.append(frame)

            df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            learning_dataset_sources_count = len(frames)

            if "story_points" in df.columns:
                total_story_points = float(df["story_points"].fillna(0).sum())
            else:
                total_story_points = 30.0
            team_capacity = int(max(total_story_points, 1.0))
            extracted_context = ContextExtractor().extract(df, team_capacity)
            _, learning_metrics = WeightLearningModel().train_with_metrics(df, extracted_context)
            learning_sample_count = int(learning_metrics.get("sample_count") or 0)
            learning_mae = learning_metrics.get("mae")
            learning_r2 = learning_metrics.get("r2")
            learning_feature_importance = {
                str(k): float(v) for k, v in (learning_metrics.get("feature_importance") or {}).items()
            }
            learning_model_type = str(learning_metrics.get("model_type") or "unknown")
        except Exception:
            pass

    return MetricsRead(
        team_id=team_id,
        sprint_velocity=velocities,
        business_value=values,
        risk_selected=risk_selected,
        risk_rejected=risk_rejected,
        weight_evolution=weight_evolution,
        learning_sample_count=learning_sample_count,
        learning_dataset_sources_count=learning_dataset_sources_count,
        learning_mae=learning_mae,
        learning_r2=learning_r2,
        learning_feature_importance=learning_feature_importance,
        learning_model_type=learning_model_type,
    )


@router.get("/{team_id}/capabilities")
def get_capabilities(team_id: str):
    return {
        "team_id": team_id,
        "explainability_engine": {
            "rule_based": True,
            "shap_enabled": False,
        },
        "optimization_engine": {
            "pulp_enabled": True,
            "ortools_enabled": _cp_model is not None,
        },
        "auth": {
            "fastapi_users_enabled": FASTAPI_USERS_ENABLED,
        },
    }
