import math

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.schemas.bookings import (
    BookingListRead,
)
from app.schemas.pagination import PaginatedResponse
from app.services import bookings_service as booking_service

router = APIRouter(prefix="/bookings", tags=["Admin - Bookings"])


@router.get(
    "/admin/all",
    response_model=PaginatedResponse[BookingListRead],
    dependencies=[Depends(require_admin)],
)
@limiter.limit("60/minute")
async def get_all_bookings(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = Query(None),
    departure_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await booking_service.get_all_bookings(db, page, size, status, search, departure_date)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )
