from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.database import get_db
from app.schemas.promotions import PromotionRead, PromotionCreate
from app.services import promotions_service
from app.core.limiter import limiter
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/promotions", tags=["Promotions"])

@router.get("", response_model=List[PromotionRead])
@limiter.limit("60/minute")
async def get_all_promotions(request: Request, db: AsyncSession = Depends(get_db)):
    return await promotions_service.get_all_promotions(db)

@router.get("/{promotion_id}", response_model=PromotionRead)
@limiter.limit("60/minute")
async def get_promotion(request: Request, promotion_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await promotions_service.get_promotion(promotion_id, db)

@router.post("", response_model=PromotionRead)
@limiter.limit("10/minute")
async def create_promotion(
    request: Request, 
    promotion_data: PromotionCreate, 
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin)
):
    return await promotions_service.create_promotion(promotion_data, db)
