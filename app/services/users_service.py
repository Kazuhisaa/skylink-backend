import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


from app.auth.models import User
from app.schemas.users import UserProfileUpdate

logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_with_role(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.role))
    )
    user = result.scalar_one()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


# ─── Profile Services ────────────────────────────────────────────────────────

async def get_profile(user_id: uuid.UUID, db: AsyncSession) -> User:
    return await _get_user_with_role(user_id, db)


async def update_profile(
    user_id: uuid.UUID,
    update_data: UserProfileUpdate,
    db: AsyncSession,
) -> User:
    user = await _get_user_with_role(user_id, db)

    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    logger.info(f"[USER] Updated profile for user {user_id}")
    return await _get_user_with_role(user_id, db)


# ─── Admin Services ────────────────────────────────────────────────────────────

async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).options(selectinload(User.role)).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    logger.info("[ADMIN] Fetched all users")
    return list(users)


async def get_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    user = await _get_user_with_role(user_id, db)
    logger.info(f"[ADMIN] Fetched user {user_id}")
    return user