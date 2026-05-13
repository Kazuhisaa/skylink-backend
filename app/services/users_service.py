import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.auth.models import User
from app.schemas.users import UserUpdate, UserStatusUpdate

logger = logging.getLogger(__name__)


async def get_me(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


async def update_me(user_id: uuid.UUID, body: UserUpdate, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    logger.info(f"[USER] Updated profile for user {user_id}")
    return user


async def get_all_users(
    db: AsyncSession,
    page: int = 1,
    size: int = 10
) -> tuple[list[User], int]:
    # Base query
    query = select(User).order_by(User.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(User)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return items, total  # type: ignore


async def get_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


async def update_user_status(
    user_id: uuid.UUID, body: UserStatusUpdate, db: AsyncSession
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = body.is_active  # type: ignore
    await db.commit()
    await db.refresh(user)
    logger.info(f"[ADMIN] Updated status for user {user_id} → is_active={body.is_active}")
    return user


async def delete_user(user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    await db.delete(user)
    await db.commit()
    logger.info(f"[ADMIN] Deleted user {user_id}")
