from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.auth.dependencies import require_admin
from app.schemas.admin import BookingReportRead, AirportCreate, AircraftCreate, SeatClassCreate, AircraftSeatCreate, AircraftSeatRead, AirportUpdate, AircraftUpdate, SeatClassUpdate, RouteReportRead, CancellationReportRead, UserGrowthReportRead, ActivityLogListRead  

from app.schemas.flights import AirportRead, AircraftRead, SeatClassRead

from app.services import admin_service
from app.core.limiter import limiter



router = APIRouter(prefix="/admin", tags=["Admin"])



# ─── Reports ─────────────────────────────────────────────────────────────

@router.get("/reports", response_model=BookingReportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_booking_report(
    request: Request,
    date_from: Optional[datetime] = Query(None, description="Filter from date e.g. 2026-05-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="Filter to date e.g. 2026-05-31T23:59:59Z"),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_booking_report(db, date_from, date_to)

@router.get("/reports/routes", response_model=RouteReportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_route_report(
    request: Request,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_route_report(db, date_from, date_to)



# ─── Cancellation Report ──────────────────────────────────────────────────────────────────

@router.get("/reports/cancellations", response_model=CancellationReportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_cancellation_report(
    request: Request,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_cancellation_report(db, date_from, date_to)



# ─── User Growth ──────────────────────────────────────────────────────────────────

@router.get("/reports/user-growth", response_model=UserGrowthReportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_user_growth_report(
    request: Request,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_user_growth_report(db, date_from, date_to)



# ─── Activity Log ──────────────────────────────────────────────────────────────────

@router.get("/activity-logs", response_model=ActivityLogListRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_activity_logs(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(8, ge=1, le=100),
    search: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_activity_logs(db, page, size, search, date_from, date_to)

# ─── Airports ──────────────────────────────────────────────────────────────────
@router.get("/airports/public/{iata_code}", response_model=AirportRead)  # add this — no auth required
@limiter.limit("60/minute")
async def get_airport_public(request: Request, iata_code: str, db: AsyncSession = Depends(get_db)):
    return await admin_service.get_airport_by_iata(iata_code, db)

@router.get("/airports", response_model=list[AirportRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_airports(request: Request, db: AsyncSession = Depends(get_db)):
    return await admin_service.get_airports(db)

@router.post("/airports", response_model=AirportRead, status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_airport(request: Request, body: AirportCreate, db: AsyncSession = Depends(get_db)):
    return await admin_service.create_airport(body, db)

@router.put("/airports/{airport_id}", response_model=AirportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def edit_airport(request: Request, airport_id: int, body: AirportUpdate, db: AsyncSession = Depends(get_db)):
    return await admin_service.update_airport(airport_id, body, db)

@router.delete("/airports/{airport_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_airport(request: Request, airport_id: int, db: AsyncSession = Depends(get_db)):
    await admin_service.delete_airport(airport_id, db)



# ─── Aircraft ──────────────────────────────────────────────────────────────────

@router.get("/aircraft", response_model=list[AircraftRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_aircraft(request: Request, db: AsyncSession = Depends(get_db)):
    return await admin_service.get_aircraft(db)

@router.post("/aircraft", response_model=AircraftRead, status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_aircraft(request: Request, body: AircraftCreate, db: AsyncSession = Depends(get_db)):
    return await admin_service.create_aircraft(body, db)

@router.put("/aircraft/{aircraft_id}", response_model=AircraftRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def edit_aircraft(request: Request, aircraft_id: int, body: AircraftUpdate, db: AsyncSession = Depends(get_db)):
    return await admin_service.update_aircraft(aircraft_id, body, db)

@router.delete("/aircraft/{aircraft_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_aircraft(request: Request, aircraft_id: int, db: AsyncSession = Depends(get_db)):
    await admin_service.delete_aircraft(aircraft_id, db)



# ─── Seat Classes ──────────────────────────────────────────────────────────────

@router.get("/seat-classes", response_model=list[SeatClassRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_seat_classes(request: Request, db: AsyncSession = Depends(get_db)):
    return await admin_service.get_seat_classes(db)

@router.post("/seat-classes", response_model=SeatClassRead, status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_seat_class(request: Request, body: SeatClassCreate, db: AsyncSession = Depends(get_db)):
    return await admin_service.create_seat_class(body, db)

@router.put("/seat-classes/{seat_class_id}", response_model=SeatClassRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def edit_seat_class(request: Request, seat_class_id: int, body: SeatClassUpdate, db: AsyncSession = Depends(get_db)):
    return await admin_service.update_seat_class(seat_class_id, body, db)

@router.delete("/seat-classes/{seat_class_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_seat_class(request: Request, seat_class_id: int, db: AsyncSession = Depends(get_db)):
    await admin_service.delete_seat_class(seat_class_id, db)



# ─── Aircraft Seats ─────────────────────────────────────────────────────────────

@router.get("/aircraft/{aircraft_id}/seats", response_model=list[AircraftSeatRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_aircraft_seats(request: Request, aircraft_id: int, db: AsyncSession = Depends(get_db)):
    return await admin_service.get_aircraft_seats(aircraft_id, db)

@router.post("/aircraft/{aircraft_id}/seats", response_model=list[AircraftSeatRead], status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_aircraft_seats(request: Request, aircraft_id: int, body: list[AircraftSeatCreate], db: AsyncSession = Depends(get_db)):
    return await admin_service.create_aircraft_seats(aircraft_id, body, db)

@router.delete("/aircraft/seats/{seat_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_aircraft_seat(request: Request, seat_id: int, db: AsyncSession = Depends(get_db)):
    await admin_service.delete_aircraft_seat(seat_id, db)