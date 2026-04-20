from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.schemas.users import UserProfileUpdate, UserProfileRead
from app.services import users_service
from uuid import UUID

router = APIRouter(prefix="/users", tags=["Users"])


# ─── Profile Endpoints ────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfileRead)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await users_service.get_profile(current_user.id, db)


@router.put("/me", response_model=UserProfileRead)
async def update_my_profile(
    body: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await users_service.update_profile(current_user.id, body, db)


# ─── Admin Endpoints ──────────────────────────────────────────────────────────

@router.get("/admin/all", response_model=list[UserProfileRead], dependencies=[Depends(require_admin)])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all users with their role information. Admin only."""
    return await users_service.get_all_users(db)
    

@router.get("/admin/{user_id}", response_model=UserProfileRead, dependencies=[Depends(require_admin)])
async def get_user_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a specific user's profile by ID. Admin only."""
    return await users_service.get_user(user_id, db)
   
