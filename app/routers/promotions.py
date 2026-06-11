import uuid
from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.schemas.promotions import PromotionCreate, PromotionRead, PromotionUpdate
from app.services import promotions_service

router = APIRouter(prefix="/promotions", tags=["Promotions"])


@router.get("", response_model=List[PromotionRead])
@limiter.limit("60/minute")
async def get_all_promotions(request: Request, db: AsyncSession = Depends(get_db)):
    return await promotions_service.get_all_promotions(db)


@router.get("/{promotion_id}", response_model=PromotionRead)
@limiter.limit("60/minute")
async def get_promotion(
    request: Request,
    promotion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await promotions_service.get_promotion(promotion_id, db)
