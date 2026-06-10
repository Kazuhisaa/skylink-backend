from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import require_admin

from app.schemas.admin.aircraft import AircraftSeatCreate, AircraftCreate, AircraftUpdate, SeatClassCreate, SeatClassRead, SeatClassUpdate, AircraftSeatRead

from app.schemas.flights import AircraftRead

from app.services.admin import aircraft_service
from app.core.limiter import limiter



router = APIRouter(prefix="/admin", tags=["Admin - Airports"])


@router.get("/aircraft", response_model=list[AircraftRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_aircraft(request: Request, db: AsyncSession = Depends(get_db)):
    return await aircraft_service.get_aircraft(db)

@router.post("/aircraft", response_model=AircraftRead, status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_aircraft(request: Request, body: AircraftCreate, db: AsyncSession = Depends(get_db)):
    return await aircraft_service.create_aircraft(body, db)

@router.put("/aircraft/{aircraft_id}", response_model=AircraftRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def edit_aircraft(request: Request, aircraft_id: int, body: AircraftUpdate, db: AsyncSession = Depends(get_db)):
    return await aircraft_service.update_aircraft(aircraft_id, body, db)

@router.delete("/aircraft/{aircraft_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_aircraft(request: Request, aircraft_id: int, db: AsyncSession = Depends(get_db)):
    await aircraft_service.delete_aircraft(aircraft_id, db)



# ─── Seat Classes ──────────────────────────────────────────────────────────────

@router.get("/seat-classes", response_model=list[SeatClassRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_seat_classes(request: Request, db: AsyncSession = Depends(get_db)):
    return await aircraft_service.get_seat_classes(db)

@router.post("/seat-classes", response_model=SeatClassRead, status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_seat_class(request: Request, body: SeatClassCreate, db: AsyncSession = Depends(get_db)):
    return await aircraft_service.create_seat_class(body, db)

@router.put("/seat-classes/{seat_class_id}", response_model=SeatClassRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def edit_seat_class(request: Request, seat_class_id: int, body: SeatClassUpdate, db: AsyncSession = Depends(get_db)):
    return await aircraft_service.update_seat_class(seat_class_id, body, db)

@router.delete("/seat-classes/{seat_class_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_seat_class(request: Request, seat_class_id: int, db: AsyncSession = Depends(get_db)):
    await aircraft_service.delete_seat_class(seat_class_id, db)



# ─── Aircraft Seats ─────────────────────────────────────────────────────────────

@router.get("/aircraft/{aircraft_id}/seats", response_model=list[AircraftSeatRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_aircraft_seats(request: Request, aircraft_id: int, db: AsyncSession = Depends(get_db)):
    return await aircraft_service.get_aircraft_seats(aircraft_id, db)

@router.post("/aircraft/{aircraft_id}/seats", response_model=list[AircraftSeatRead], status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_aircraft_seats(request: Request, aircraft_id: int, body: list[AircraftSeatCreate], db: AsyncSession = Depends(get_db)):
    return await aircraft_service.create_aircraft_seats(aircraft_id, body, db)

@router.delete("/aircraft/seats/{seat_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_aircraft_seat(request: Request, seat_id: int, db: AsyncSession = Depends(get_db)):
    await aircraft_service.delete_aircraft_seat(seat_id, db)