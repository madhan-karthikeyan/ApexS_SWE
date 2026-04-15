from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["USE_CELERY"] = "false"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import models  # noqa: F401
from app.core.database import Base, engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
