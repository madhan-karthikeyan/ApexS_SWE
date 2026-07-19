from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.context import Context as ContextModel
from app.models.dataset_upload import DatasetUpload
from app.schemas.common import ContextExtractRequest, ContextRead
from app.services.context_extractor import ContextExtractor
from app.services.weight_learning import WeightLearningModel

router = APIRouter()


@router.post("/extract", response_model=ContextRead)
async def extract_context(payload: ContextExtractRequest, db: AsyncSession = Depends(get_async_db)):
    upload = None
    if payload.upload_id:
        result = await db.execute(
            select(DatasetUpload).where(DatasetUpload.upload_id == payload.upload_id)
        )
        upload = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(DatasetUpload)
            .where(DatasetUpload.team_id == payload.team_id)
            .order_by(DatasetUpload.uploaded_at.desc())
            .limit(1)
        )
        upload = result.scalar_one_or_none()
    if not upload or not upload.file_path:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if upload.file_path.startswith("s3://"):
        from app.core.minio_client import read_bytes

        data = read_bytes(upload.file_path.split("s3://", 1)[1].split("/", 1)[1])
        df = pd.read_csv(BytesIO(data))
    else:
        df = pd.read_csv(upload.file_path)
    capacity = payload.team_capacity or 1
    context = ContextExtractor().extract(df, capacity)
    row = ContextModel(team_id=payload.team_id, urgency_weight=context.urgency_weight, value_weight=context.value_weight, alignment_weight=context.alignment_weight)
    db.add(row)
    await db.commit()
    return ContextRead(team_id=payload.team_id, urgency_weight=row.urgency_weight, value_weight=row.value_weight, alignment_weight=row.alignment_weight, computed_at=row.computed_at)


@router.get("/{team_id}/latest", response_model=ContextRead)
async def latest_context(team_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(ContextModel)
        .where(ContextModel.team_id == team_id)
        .order_by(ContextModel.computed_at.desc())
        .limit(1)
    )
    context = result.scalar_one_or_none()
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    return ContextRead(team_id=context.team_id, urgency_weight=context.urgency_weight, value_weight=context.value_weight, alignment_weight=context.alignment_weight, computed_at=context.computed_at)
