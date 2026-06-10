import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.schemas.admin.airports import AirportCreate, AirportUpdate

from app.models.flights import Airport

logger = logging.getLogger(__name__)




# ─── Airport ───────────────────────────────────────────────────────────────────

async def create_airport(body: AirportCreate, db: AsyncSession) -> Airport:
    existing = await db.execute(select(Airport).where(Airport.iata_code == body.iata_code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Airport with this IATA code already exists.")
    airport = Airport(
        iata_code=body.iata_code.upper(),
        name=body.name,
        city=body.city,
        country=body.country,
        timezone=body.timezone,
        about=body.about,             
        highlights=body.highlights,   
        best_time=body.best_time,      
        image_url=body.image_url,      
    )
    db.add(airport)
    await db.commit()
    await db.refresh(airport)
    logger.info(f"[ADMIN] Created airport {airport.iata_code}")
    return airport

async def get_airports(db: AsyncSession) -> list[Airport]:
    result = await db.execute(select(Airport).order_by(Airport.iata_code))
    return list(result.scalars().all())

async def get_airport_by_iata(iata_code: str, db: AsyncSession) -> Airport:
    result = await db.execute(
        select(Airport).where(Airport.iata_code == iata_code.upper())
    )
    airport = result.scalar_one_or_none()
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found.")
    return airport

async def update_airport(airport_id: int, body: AirportUpdate, db: AsyncSession) -> Airport:
    result = await db.execute(select(Airport).where(Airport.id == airport_id))
    airport = result.scalar_one_or_none()
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(airport, field, value)
    await db.commit()
    await db.refresh(airport)
    logger.info(f"[ADMIN] Updated airport {airport_id}")
    return airport

async def delete_airport(airport_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(Airport).where(Airport.id == airport_id))
    airport = result.scalar_one_or_none()
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found.")
    from app.models.flights import Flight
    in_use = await db.execute(
        select(Flight).where(
            (Flight.origin_airport_id == airport_id) |
            (Flight.destination_airport_id == airport_id)
        )
    )
    if in_use.scalars().first():
        raise HTTPException(status_code=409, detail="Cannot delete airport with existing flights.")
    await db.delete(airport)
    await db.commit()
    logger.info(f"[ADMIN] Deleted airport {airport_id}")
