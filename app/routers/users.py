from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.database import get_db
from app.models.auth import User
from app.schemas.users import UserRead, UserUpdate
from app.services import users_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
@limiter.limit("60/minute")
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await users_service.get_me(current_user.id, db)  # type: ignore


@router.put("/me", response_model=UserRead)
@limiter.limit("20/minute")
async def update_me(
    request: Request,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await users_service.update_me(current_user.id, body, db)  # type: ignore
