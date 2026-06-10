import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.models.auth import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.users import UserRead, UserStatusUpdate, UserUpdate
from app.services import users_service

router = APIRouter(prefix="/users", tags=["Users"])


# ─── Passenger Endpoints ───────────────────────────────────────────────────────


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


# ─── Admin Endpoints ───────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[UserRead], dependencies=[Depends(require_admin)])
@limiter.limit("60/minute")
async def get_all_users(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await users_service.get_all_users(db, page, size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(require_admin)])
@limiter.limit("60/minute")
async def get_user(request: Request, user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await users_service.get_user(user_id, db)


@router.put("/{user_id}/status", response_model=UserRead, dependencies=[Depends(require_admin)])
@limiter.limit("20/minute")
async def update_user_status(
    request: Request,
    user_id: uuid.UUID,
    body: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await users_service.update_user_status(user_id, body, db)


@router.delete("/{user_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("20/minute")
async def delete_user(request: Request, user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await users_service.delete_user(user_id, db)
