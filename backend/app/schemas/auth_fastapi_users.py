from __future__ import annotations

from fastapi_users import schemas


class UserRead(schemas.BaseUser[str]):
    role: str


class UserCreate(schemas.BaseUserCreate):
    role: str = "scrum_master"


class UserUpdate(schemas.BaseUserUpdate):
    role: str | None = None
