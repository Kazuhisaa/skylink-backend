import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.bookings import Booking
from app.schemas.admin import BookingReportRead

logger = logging.getLogger(__name__)

from app.models.flights import Airport, Aircraft, SeatClass, FlightSeatPricing
from app.schemas.admin import AirportCreate, AircraftCreate, SeatClassCreate, AirportUpdate, AircraftUpdate, SeatClassUpdate
from fastapi import HTTPException

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
    )
    db.add(airport)
    await db.commit()
    await db.refresh(airport)
    logger.info(f"[ADMIN] Created airport {airport.iata_code}")
    return airport

async def get_airports(db: AsyncSession) -> list[Airport]:
    result = await db.execute(select(Airport).order_by(Airport.iata_code))
    return list(result.scalars().all())

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

# ─── Aircraft ──────────────────────────────────────────────────────────────────

async def create_aircraft(body: AircraftCreate, db: AsyncSession) -> Aircraft:
    existing = await db.execute(select(Aircraft).where(Aircraft.registration == body.registration))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Aircraft with this registration already exists.")
    aircraft = Aircraft(
        model=body.model,
        total_seats=body.total_seats,
        registration=body.registration,
    )
    db.add(aircraft)
    await db.commit()
    await db.refresh(aircraft)
    logger.info(f"[ADMIN] Created aircraft {aircraft.registration}")
    return aircraft

async def get_aircraft(db: AsyncSession) -> list[Aircraft]:
    result = await db.execute(select(Aircraft).order_by(Aircraft.model))
    return list(result.scalars().all())

async def update_aircraft(aircraft_id: int, body: AircraftUpdate, db: AsyncSession) -> Aircraft:
    result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = result.scalar_one_or_none()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found.")
    if body.registration:
        existing = await db.execute(
            select(Aircraft).where(
                Aircraft.registration == body.registration,
                Aircraft.id != aircraft_id
            )
        )

        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Aircraft already exists.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(aircraft, field, value)
    await db.commit()
    await db.refresh(aircraft)
    logger.info(f"[ADMIN] Updated aircraft {aircraft_id}")
    return aircraft

async def delete_aircraft(aircraft_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = result.scalar_one_or_none()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found.")
    from app.models.flights import Flight
    in_use = await db.execute(select(Flight).where(Flight.aircraft_id == aircraft_id))
    if in_use.scalars().first():
        raise HTTPException(status_code=409, detail="Cannot delete aircraft with existing flights.")
    await db.delete(aircraft)
    await db.commit()
    logger.info(f"[ADMIN] Deleted aircraft {aircraft_id}")

# ─── Seat Class ────────────────────────────────────────────────────────────────

async def create_seat_class(body: SeatClassCreate, db: AsyncSession) -> SeatClass:
    existing = await db.execute(select(SeatClass).where(SeatClass.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Seat class with this name already exists.")
    seat_class = SeatClass(name=body.name)
    db.add(seat_class)
    await db.commit()
    await db.refresh(seat_class)
    logger.info(f"[ADMIN] Created seat class {seat_class.name}")
    return seat_class

async def get_seat_classes(db: AsyncSession) -> list[SeatClass]:
    result = await db.execute(select(SeatClass).order_by(SeatClass.name))
    return list(result.scalars().all())

async def update_seat_class(seat_class_id: int, body: SeatClassUpdate, db: AsyncSession) -> SeatClass:
    result = await db.execute(select(SeatClass).where(SeatClass.id == seat_class_id))
    seat_class = result.scalar_one_or_none()
    if not seat_class:
        raise HTTPException(status_code=404, detail="Seat class not found.")
    if body.name:
        existing = await db.execute(select(SeatClass).where(SeatClass.name == body.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Seat class with this name already exists.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(seat_class, field, value)
    await db.commit()
    await db.refresh(seat_class)
    logger.info(f"[ADMIN] Updated seat class {seat_class_id}")
    return seat_class

async def delete_seat_class(seat_class_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(SeatClass).where(SeatClass.id == seat_class_id))
    seat_class = result.scalar_one_or_none()

    if not seat_class:
        raise HTTPException(status_code=404, detail="Seat class not found.")

    in_use = await db.execute(select(FlightSeatPricing).where(FlightSeatPricing.seat_class_id == seat_class_id ))

    if in_use.scalars().first():
        raise HTTPException(status_code=409, detail="Cannot delete seat class in use by flights.")

    booking_in_use = await db.execute(select(Booking).where(Booking.seat_class_id == seat_class_id))

    if booking_in_use.scalars().first():
        raise HTTPException(status_code=409, detail="Cannot delete seat class used by bookings.")

    await db.delete(seat_class)
    await db.commit()

    logger.info(f"[ADMIN] Deleted seat class {seat_class_id}")

async def get_booking_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> BookingReportRead:

    query = select(Booking)

    if date_from:
        query = query.where(Booking.booked_at >= date_from)
    if date_to:
        query = query.where(Booking.booked_at <= date_to)

    result = await db.execute(query)
    bookings = result.scalars().all()

    total_bookings = len(bookings)
    confirmed = [b for b in bookings if b.status == "confirmed"]  # type: ignore
    cancelled = [b for b in bookings if b.status == "cancelled"]  # type: ignore

    total_revenue = sum(b.total_price for b in bookings)  # type: ignore
    confirmed_revenue = sum(b.total_price for b in confirmed)  # type: ignore

    logger.info(f"[ADMIN] Report generated — total={total_bookings} revenue={total_revenue}")

    return BookingReportRead(
        total_bookings=total_bookings,
        confirmed_bookings=len(confirmed),
        cancelled_bookings=len(cancelled),
        total_revenue=total_revenue,            # type: ignore
        confirmed_revenue=confirmed_revenue,    # type: ignore
        date_from=date_from,
        date_to=date_to,
    )


