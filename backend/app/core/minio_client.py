from __future__ import annotations

from io import BytesIO
from pathlib import Path

import boto3
from botocore.config import Config

from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        # Fail fast when MinIO is unavailable so local file fallback is immediate.
        config=Config(connect_timeout=1, read_timeout=2, retries={"max_attempts": 0}),
    )


def ensure_bucket():
    try:
        client = get_s3_client()
        buckets = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
        if settings.minio_bucket not in buckets:
            client.create_bucket(Bucket=settings.minio_bucket)
    except Exception:
        return False
    return True


def save_bytes(path: str, data: bytes) -> str:
    try:
        client = get_s3_client()
        client.put_object(Bucket=settings.minio_bucket, Key=path, Body=BytesIO(data))
        return f"s3://{settings.minio_bucket}/{path}"
    except Exception:
        local_root = Path("./storage")
        file_path = local_root / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return str(file_path)


def read_bytes(path: str) -> bytes:
    try:
        client = get_s3_client()
        obj = client.get_object(Bucket=settings.minio_bucket, Key=path)
        return obj["Body"].read()
    except Exception:
        file_path = Path(path)
        if file_path.exists():
            return file_path.read_bytes()
        local_path = Path("./storage") / path
        return local_path.read_bytes()
