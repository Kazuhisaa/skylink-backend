import logging
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.promotions import Promotion
from app.schemas.promotions import PromotionCreate

logger = logging.getLogger(__name__)

async def get_all_promotions(db: AsyncSession) -> List[Promotion]:
    result = await db.execute(select(Promotion).order_by(Promotion.created_at.desc()))
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
    return new_promotion
