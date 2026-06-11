from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.schemas.admin.airports import AirportCreate, AirportUpdate
from app.schemas.flights import AirportRead
from app.services.admin import airport_service

router = APIRouter(prefix="/admin", tags=["Admin - Airports"])


@router.get("/airports/public", response_model=list[AirportRead])
@limiter.limit("60/minute")
async def list_airports_public(request: Request, db: AsyncSession = Depends(get_db)):
    return await airport_service.get_airports(db)


@router.get(
    "/airports/public/{iata_code}", response_model=AirportRead
)  # add this — no auth required
@limiter.limit("60/minute")
async def get_airport_public(request: Request, iata_code: str, db: AsyncSession = Depends(get_db)):
    return await airport_service.get_airport_by_iata(iata_code, db)
