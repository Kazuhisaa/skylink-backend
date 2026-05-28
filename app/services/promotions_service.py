import logging
import uuid
from datetime import date
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.promotions import Promotion
from app.schemas.promotions import PromotionCreate, PromotionUpdate

logger = logging.getLogger(__name__)


async def get_all_promotions(db: AsyncSession) -> List[Promotion]:
    """Return only promotions whose valid_until is today or in the future."""
    today = date.today()
    result = await db.execute(
        select(Promotion)
        .where(Promotion.valid_until >= today)
        .order_by(Promotion.created_at.desc())
    )
    return list(result.scalars().all())


async def get_promotion(promotion_id: uuid.UUID, db: AsyncSession) -> Promotion:
    result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
    promotion = result.scalar_one_or_none()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found.")
    return promotion


async def create_promotion(promotion_data: PromotionCreate, db: AsyncSession) -> Promotion:
    new_promotion = Promotion(**promotion_data.model_dump())
    db.add(new_promotion)
    await db.commit()
    await db.refresh(new_promotion)
    logger.info(f"[ADMIN] Created promotion '{new_promotion.title}' id={new_promotion.id}")
    return new_promotion


async def update_promotion(
    promotion_id: uuid.UUID, body: PromotionUpdate, db: AsyncSession
) -> Promotion:
    result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
    promotion = result.scalar_one_or_none()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found.")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(promotion, field, value)

    await db.commit()
    await db.refresh(promotion)
    logger.info(f"[ADMIN] Updated promotion id={promotion_id}")
    return promotion


async def delete_promotion(promotion_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
    promotion = result.scalar_one_or_none()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found.")

    await db.delete(promotion)
    await db.commit()
    logger.info(f"[ADMIN] Deleted promotion id={promotion_id}")