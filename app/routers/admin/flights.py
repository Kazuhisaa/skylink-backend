import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.schemas.flights import FlightCreateWithPricing, FlightRead, FlightUpdate
from app.services import flights_service

router = APIRouter(prefix="/flights", tags=["Admin - Flights"])


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
