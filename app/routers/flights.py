from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.schemas.flights import FlightCreate, FlightUpdate, FlightRead, FlightListRead, FlightCreateWithPricing
from app.services import flights_service
from app.core.limiter import limiter

router = APIRouter(prefix="/flights", tags=["Flights"])


# ─── Passenger ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[FlightListRead])
@limiter.limit("60/minute")
async def search_flights(
    request: Request,
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await flights_service.search_flights(db, origin, destination, date, status)


@router.get("/{flight_id}", response_model=FlightRead)
@limiter.limit("60/minute")
async def get_flight(request: Request, flight_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await flights_service.get_flight(flight_id, db)


# ─── Admin ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=FlightRead, status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
async def create_flight(
    body: FlightCreateWithPricing,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await flights_service.create_flight(body, current_user.id, db, body.seat_pricing)


@router.put("/{flight_id}", response_model=FlightRead, dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
async def update_flight(
    flight_id: uuid.UUID,
    body: FlightUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await flights_service.update_flight(flight_id, body, db)


@router.delete("/{flight_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
async def delete_flight(request: Request, flight_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await flights_service.delete_flight(flight_id, db)