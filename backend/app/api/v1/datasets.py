from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.minio_client import read_bytes, save_bytes
from app.models.dataset_upload import DatasetUpload
from app.models.team import ScrumTeam
from app.schemas.common import DatasetPreviewResponse, DatasetUploadRead

router = APIRouter()


REQUIRED_COLUMNS = ["story_id", "story_points", "business_value", "risk_score"]


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...), team_id: str = Form(...), db: Session = Depends(get_db)):
    content = await file.read()

    team = db.query(ScrumTeam).filter(ScrumTeam.team_id == str(team_id)).first()
    if not team:
        raise HTTPException(status_code=400, detail=f"Invalid team_id: {team_id}")

    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {exc}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    original_name = file.filename or "dataset.csv"
    safe_name = Path(original_name).name or "dataset.csv"
    path = f"{team_id}/{uuid4()}_{safe_name}"
    stored_path = save_bytes(path, content)
    upload = DatasetUpload(team_id=str(team_id), filename=safe_name, file_path=stored_path, row_count=len(df), is_valid=True)
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return {
        "upload_id": upload.upload_id,
        "rows": len(df),
        "preview": df.head(10).fillna("").to_dict(orient="records"),
        "columns": list(df.columns),
        "is_valid": True,
        "errors": [],
    }


@router.get("/{team_id}", response_model=list[DatasetUploadRead])
def list_datasets(team_id: str, db: Session = Depends(get_db)):
    uploads = db.query(DatasetUpload).filter(DatasetUpload.team_id == team_id).all()
    return [
        {
            "upload_id": u.upload_id,
            "team_id": u.team_id,
            "filename": u.filename,
            "file_path": u.file_path,
            "row_count": u.row_count,
            "is_valid": u.is_valid,
            "uploaded_at": u.uploaded_at,
        }
        for u in uploads
    ]


@router.get("/{upload_id}/preview")
def preview_dataset(upload_id: str, db: Session = Depends(get_db)):
    upload = db.query(DatasetUpload).filter(DatasetUpload.upload_id == upload_id).first()
    if not upload or not upload.file_path:
        raise HTTPException(status_code=404, detail="Upload not found")
    path = upload.file_path
    if path.startswith("s3://"):
        data = read_bytes(path.split("s3://", 1)[1].split("/", 1)[1])
        df = pd.read_csv(BytesIO(data))
    else:
        df = pd.read_csv(path)
    return DatasetPreviewResponse(
        upload_id=upload.upload_id,
        rows=len(df),
        preview=df.head(10).fillna("").to_dict(orient="records"),
        columns=list(df.columns),
        is_valid=bool(upload.is_valid),
        errors=[],
    )
