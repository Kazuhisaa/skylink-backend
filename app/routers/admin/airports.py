from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


from app.database import get_db
from app.core.dependencies import require_admin

from app.schemas.admin.airports import AirportCreate, AirportUpdate
from app.schemas.flights import AirportRead
from app.services.admin import airport_service
from app.core.limiter import limiter

router = APIRouter(prefix="/admin", tags=["Admin - Airports"])

# ─── Airports ──────────────────────────────────────────────────────────────────
@router.get("/airports/public/{iata_code}", response_model=AirportRead)  # add this — no auth required
@limiter.limit("60/minute")
async def get_airport_public(request: Request, iata_code: str, db: AsyncSession = Depends(get_db)):
    return await airport_service.get_airport_by_iata(iata_code, db)

@router.get("/airports/public", response_model=list[AirportRead])
@limiter.limit("60/minute")
async def list_airports_public(request: Request, db: AsyncSession = Depends(get_db)):
    return await airport_service.get_airports(db)

@router.get("/airports", response_model=list[AirportRead], dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def list_airports(request: Request, db: AsyncSession = Depends(get_db)):
    return await airport_service.get_airports(db)

@router.post("/airports", response_model=AirportRead, status_code=201, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def add_airport(request: Request, body: AirportCreate, db: AsyncSession = Depends(get_db)):
    return await airport_service.create_airport(body, db)

@router.put("/airports/{airport_id}", response_model=AirportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def edit_airport(request: Request, airport_id: int, body: AirportUpdate, db: AsyncSession = Depends(get_db)):
    return await airport_service.update_airport(airport_id, body, db)

@router.delete("/airports/{airport_id}", status_code=204, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def remove_airport(request: Request, airport_id: int, db: AsyncSession = Depends(get_db)):
    await airport_service.delete_airport(airport_id, db)

