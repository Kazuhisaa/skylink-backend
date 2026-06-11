import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.database import get_db
from app.schemas.flights import FlightListRead, FlightRead
from app.schemas.pagination import PaginatedResponse
from app.services import flights_service

router = APIRouter(prefix="/flights", tags=["Flights"])

...
# ─── Passenger ─────────────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[FlightListRead])
@limiter.limit("60/minute")
async def search_flights(
    request: Request,
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await flights_service.search_flights(
        db, origin, destination, date, status, page, size
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.get("/{flight_id}", response_model=FlightRead)
@limiter.limit("60/minute")
async def get_flight(request: Request, flight_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await flights_service.get_flight(flight_id, db)
