from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.database import get_db
from app.models.auth import User
from app.schemas.bookings import PNRStatusResult
from app.services import bookings_service as booking_service

router = APIRouter(prefix="/pnr", tags=["PNR"])


@router.get("/status", response_model=PNRStatusResult)
@limiter.limit("30/minute")
async def get_pnr_status(
    request: Request,
    pnr: str = Query(..., min_length=8, max_length=8),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.get_booking_by_pnr(pnr, db)


@router.get("/public-status", response_model=PNRStatusResult)
@limiter.limit("10/minute")
async def get_pnr_public_status(
    request: Request,
    pnr: str = Query(..., min_length=8, max_length=8),
    lastName: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await booking_service.get_booking_by_pnr_public(pnr, lastName, db)
