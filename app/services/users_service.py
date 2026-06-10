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
) -> tuple[list[dict], int]:
    from app.models.bookings import Booking
    # Count total
    count_query = select(func.count()).select_from(User)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    # Query with bookings count
    query = (
        select(User, func.count(Booking.id).label("bookings_count"))
        .outerjoin(Booking, Booking.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    rows = result.all()
    items = []
    for user, bookings_count in rows:
        user_dict = {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role_id": user.role_id,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "bookings_count": bookings_count,
        }
        items.append(user_dict)
    return items, total  


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
