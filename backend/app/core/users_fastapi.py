from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.db import BaseUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_backend import auth_backend
from app.core.config import settings
from app.core.database import get_async_db
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth_fastapi_users import UserCreate, UserRead, UserUpdate


class UserDatabaseAdapter(BaseUserDatabase[User, str]):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: str):
        result = await self.db.execute(select(User).where(User.id == str(id)))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_oauth_account(self, oauth: str, account_id: str):
        return None

    async def create(self, create_dict: dict):
        user = User(
            email=create_dict["email"],
            hashed_password=create_dict["hashed_password"],
            role=create_dict.get("role", "scrum_master"),
            is_active=create_dict.get("is_active", True),
            is_superuser=create_dict.get("is_superuser", False),
            is_verified=create_dict.get("is_verified", False),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, update_dict: dict):
        for key, value in update_dict.items():
            setattr(user, key, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User):
        await self.db.delete(user)
        await self.db.commit()

    async def add_oauth_account(self, user: User, create_dict: dict):
        return user

    async def update_oauth_account(self, user: User, oauth_account, update_dict: dict):
        return user


async def get_user_db(db=Depends(get_async_db)) -> AsyncGenerator[UserDatabaseAdapter, None]:
    yield UserDatabaseAdapter(db)


class UserManager(BaseUserManager[User, str]):
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    def parse_id(self, value):
        return str(value)

    async def create(self, user_create: UserCreate, safe: bool = False, request=None):
        user_dict = user_create.create_update_dict()
        password = user_dict.pop("password")
        user_dict["hashed_password"] = hash_password(password)
        user_dict.setdefault("is_active", True)
        user_dict.setdefault("is_superuser", False)
        user_dict.setdefault("is_verified", False)
        created_user = await self.user_db.create(user_dict)
        await self.on_after_register(created_user, request)
        return created_user


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, str](
    get_user_manager,
    [auth_backend],
)

auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)
users_router = fastapi_users.get_users_router(UserRead, UserUpdate)
