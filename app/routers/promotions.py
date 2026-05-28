from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.database import get_db
from app.schemas.promotions import PromotionRead, PromotionCreate, PromotionUpdate
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
async def get_promotion(
    request: Request,
    promotion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await promotions_service.get_promotion(promotion_id, db)


@router.post("", response_model=PromotionRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_promotion(
    request: Request,
    promotion_data: PromotionCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    return await promotions_service.create_promotion(promotion_data, db)


@router.put("/{promotion_id}", response_model=PromotionRead)
@limiter.limit("10/minute")
async def update_promotion(
    request: Request,
    promotion_id: uuid.UUID,
    body: PromotionUpdate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    return await promotions_service.update_promotion(promotion_id, body, db)


@router.delete("/{promotion_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_promotion(
    request: Request,
    promotion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    await promotions_service.delete_promotion(promotion_id, db)