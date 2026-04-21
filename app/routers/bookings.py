from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.schemas.bookings import (
    BookingCreate, BookingRead, BookingListRead,
    RescheduleRequest, CancelRequest
)
from app.services import bookings_service as booking_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ─── Passenger Endpoints ───────────────────────────────────────────────────────

@router.get("", response_model=list[BookingListRead])
async def get_user_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.get_user_bookings(current_user.id, db)  # type: ignore


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.get_booking(booking_id, current_user.id, db)  # type: ignore


@router.post("", response_model=BookingRead, status_code=201)
async def create_booking(
    body: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.create_booking(body, current_user.id, db)  # type: ignore


@router.put("/{booking_id}/reschedule", response_model=BookingRead)
async def reschedule_booking(
    booking_id: uuid.UUID,
    body: RescheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await booking_service.reschedule_booking(booking_id, body, current_user.id, db)  # type: ignore


@router.delete("/{booking_id}", status_code=204)
async def cancel_booking(
    booking_id: uuid.UUID,
    body: CancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await booking_service.cancel_booking(booking_id, body, current_user.id, db)  # type: ignore


# ─── Admin Endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/all", response_model=list[BookingListRead], dependencies=[Depends(require_admin)])
async def get_all_bookings(
    db: AsyncSession = Depends(get_db),
):
    return await booking_service.get_all_bookings(db)