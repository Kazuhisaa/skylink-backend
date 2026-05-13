import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.flights import Flight, FlightSeatPricing, Airport, Aircraft, SeatClass
from app.schemas.flights import FlightCreateWithPricing, FlightUpdate, FlightSeatPricingCreate

logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────────

async def _get_flight_with_relations(flight_id: uuid.UUID, db: AsyncSession) -> Flight:
    result = await db.execute(
        select(Flight)
        .where(Flight.id == flight_id)
        .options(
            selectinload(Flight.origin_airport),
            selectinload(Flight.destination_airport),
            selectinload(Flight.aircraft),
            selectinload(Flight.seat_pricing).selectinload(FlightSeatPricing.seat_class),
        )
    )
    flight = result.scalar_one_or_none()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found.")
    return flight


async def _validate_aircraft(aircraft_id: int, db: AsyncSession) -> Aircraft:
    result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = result.scalar_one_or_none()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found.")
    return aircraft


async def _validate_airport(airport_id: int, db: AsyncSession) -> Airport:
    result = await db.execute(select(Airport).where(Airport.id == airport_id))
    airport = result.scalar_one_or_none()
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found.")
    return airport


# ─── Passenger Services ────────────────────────────────────────────────────────

async def search_flights(
    db: AsyncSession,
    origin: str | None = None,
    destination: str | None = None,
    date=None,
    status: str | None = None,
    page: int = 1,
    size: int = 10,
) -> tuple[list[Flight], int]:
    query = (
        select(Flight)
        .options(
            selectinload(Flight.origin_airport),
            selectinload(Flight.destination_airport),
            selectinload(Flight.aircraft),
            selectinload(Flight.seat_pricing).selectinload(FlightSeatPricing.seat_class),
        )
    )
    if origin:
        query = query.join(Flight.origin_airport, Flight.origin_airport_id == Airport.id).where(
            Airport.iata_code == origin.upper()
        )
    if destination:
        query = query.join(Flight.destination_airport, Flight.destination_airport_id == Airport.id).where(
            Airport.iata_code == destination.upper()
        )
    if date:
        query = query.where(Flight.departure_time >= date)
    if status:
        query = query.where(Flight.status == status)

    # Total count query
    count_query = select(func.count()).select_from(Flight)
    if origin:
        count_query = count_query.join(Flight.origin_airport, Flight.origin_airport_id == Airport.id).where(
            Airport.iata_code == origin.upper()
        )
    if destination:
        count_query = count_query.join(Flight.destination_airport, Flight.destination_airport_id == Airport.id).where(
            Airport.iata_code == destination.upper()
        )
    if date:
        count_query = count_query.where(Flight.departure_time >= date)
    if status:
        count_query = count_query.where(Flight.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return items, total  # type: ignore


async def get_flight(flight_id: uuid.UUID, db: AsyncSession) -> Flight:
    return await _get_flight_with_relations(flight_id, db)


# ─── Admin Services ────────────────────────────────────────────────────────────

async def create_flight(
    body: FlightCreateWithPricing,
    created_by: uuid.UUID,
    db: AsyncSession,
    seat_pricing: list[FlightSeatPricingCreate] | None = None,
) -> Flight:
    # Validate references exist
    await _validate_aircraft(body.aircraft_id, db)
    await _validate_airport(body.origin_airport_id, db)
    await _validate_airport(body.destination_airport_id, db)

    if body.origin_airport_id == body.destination_airport_id:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination airports cannot be the same."
        )

    # Check duplicate flight number
    existing = await db.execute(
        select(Flight).where(Flight.flight_number == body.flight_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Flight number already exists.")

    flight = Flight(
        flight_number=body.flight_number,
        aircraft_id=body.aircraft_id,
        origin_airport_id=body.origin_airport_id,
        destination_airport_id=body.destination_airport_id,
        departure_time=body.departure_time,
        arrival_time=body.arrival_time,
        status=body.status,
        created_by=created_by,
    )
    db.add(flight)
    await db.flush()  # get flight.id

    # Add seat pricing if provided
    if seat_pricing:
        for pricing in seat_pricing:
            # validate seat class exists
            sc_result = await db.execute(
                select(SeatClass).where(SeatClass.id == pricing.seat_class_id)
            )
            if not sc_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=404,
                    detail=f"Seat class {pricing.seat_class_id} not found."
                )
            db.add(FlightSeatPricing(
                flight_id=flight.id,
                seat_class_id=pricing.seat_class_id,
                total_seats=pricing.total_seats,
                available_seats=pricing.available_seats,
                price=pricing.price,
            ))

    await db.commit()
    logger.info(f"[FLIGHT] Created flight {flight.flight_number} by admin {created_by}")
    return await _get_flight_with_relations(flight.id, db)          # type: ignore


async def update_flight(
    flight_id: uuid.UUID,
    body: FlightUpdate,
    db: AsyncSession,
) -> Flight:
    result = await db.execute(select(Flight).where(Flight.id == flight_id))
    flight = result.scalar_one_or_none()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found.")

    updates = body.model_dump(exclude_none=True)

    # Check duplicate flight number if being updated
    if "flight_number" in updates and updates["flight_number"] != flight.flight_number:
        existing = await db.execute(
            select(Flight).where(Flight.flight_number == updates["flight_number"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Flight number already exists.")

    # Validate if aircraft/airports are being updated
    if "aircraft_id" in updates:
        await _validate_aircraft(updates["aircraft_id"], db)
    if "origin_airport_id" in updates:
        await _validate_airport(updates["origin_airport_id"], db)
    if "destination_airport_id" in updates:
        await _validate_airport(updates["destination_airport_id"], db)

    origin = updates.get("origin_airport_id", flight.origin_airport_id)
    destination = updates.get("destination_airport_id", flight.destination_airport_id)
    if origin == destination:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination airports cannot be the same."
        )

    for field, value in updates.items():
        setattr(flight, field, value)

    await db.commit()
    logger.info(f"[FLIGHT] Updated flight {flight.flight_number}")
    return await _get_flight_with_relations(flight_id, db)  # type: ignore


async def delete_flight(flight_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(select(Flight).where(Flight.id == flight_id))
    flight = result.scalar_one_or_none()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found.")

    # Prevent deleting flights that have bookings
    from app.models.bookings import Booking
    bookings_result = await db.execute(
        select(Booking).where(Booking.flight_id == flight_id)
    )
    if bookings_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Cannot delete flight with existing bookings."
        )

    await db.delete(flight)
    await db.commit()
    logger.info(f"[FLIGHT] Deleted flight {flight.flight_number}")
