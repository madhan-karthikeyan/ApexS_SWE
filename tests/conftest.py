from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["USE_CELERY"] = "false"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

for path in (str(BACKEND),):
    if path not in sys.path:
        sys.path.insert(0, path)

import pytest

from app.core.database import Base, engine
from app import models  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
