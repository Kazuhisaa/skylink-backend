import math
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.models.auth import User
from app.schemas.bookings import (
    BookingCreate,
    BookingListRead,
    BookingRead,
    CancelRequest,
    RescheduleRequest,
)
from app.schemas.pagination import PaginatedResponse
from app.services import bookings_service as booking_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])

# ─── Passenger Endpoints ───────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[BookingListRead])
@limiter.limit("60/minute")
async def get_user_bookings(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await booking_service.get_user_bookings(current_user.id, db, page, size)  # type: ignore
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.get("/{booking_id}", response_model=BookingRead)
@limiter.limit("60/minute")
async def get_booking(
    request: Request,
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.get_booking(booking_id, current_user.id, db)  # type: ignore


@router.post("", response_model=BookingRead, status_code=201)
@limiter.limit("20/minute")
async def create_booking(
    request: Request,
    body: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.create_booking(body, current_user.id, db)  # type: ignore


@router.put("/{booking_id}/reschedule", response_model=BookingRead)
@limiter.limit("20/minute")
async def reschedule_booking(
    request: Request,
    booking_id: uuid.UUID,
    body: RescheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.reschedule_booking(booking_id, body, current_user.id, db)  # type: ignore


@router.delete("/{booking_id}", status_code=204)
@limiter.limit("20/minute")
async def cancel_booking(
    request: Request,
    booking_id: uuid.UUID,
    body: CancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await booking_service.cancel_booking(booking_id, body, current_user.id, db)  # type: ignore
