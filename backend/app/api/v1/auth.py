from __future__ import annotations

from fastapi import APIRouter

from app.core.users_fastapi import auth_router, register_router, users_router
from app.schemas.common import MessageResponse

router = APIRouter()

router.include_router(auth_router, prefix="")
router.include_router(register_router, prefix="")
router.include_router(users_router, prefix="/users")


@router.post("/logout", response_model=MessageResponse)
def logout():
    return MessageResponse(message="Logged out")
