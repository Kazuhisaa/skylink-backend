import logging

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bookings import Booking
from app.models.flights import Aircraft, AircraftSeat, FlightSeatPricing, SeatClass
from app.schemas.admin.aircraft import (
    AircraftCreate,
    AircraftSeatCreate,
    AircraftUpdate,
    SeatClassCreate,
    SeatClassUpdate,
)

logger = logging.getLogger(__name__)


# ─── Aircraft ──────────────────────────────────────────────────────────────────


async def create_aircraft(body: AircraftCreate, db: AsyncSession) -> Aircraft:
    existing = await db.execute(select(Aircraft).where(Aircraft.registration == body.registration))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Aircraft with this registration already exists."
        )

    total_calculated_seats = sum(config.quantity for config in body.seat_configurations)

    aircraft = Aircraft(
        model=body.model,
        total_seats=total_calculated_seats,
        registration=body.registration,
    )
    db.add(aircraft)
    await db.flush()  # get aircraft.id

    # Automatic Seat Generation (Row + Letter Pattern: A, B, C, D, E, F)
    letters = ["A", "B", "C", "D", "E", "F"]
    current_row = 1
    letter_idx = 0

    for config in body.seat_configurations:
        for _ in range(config.quantity):
            seat_number = f"{current_row}{letters[letter_idx]}"
            db.add(
                AircraftSeat(
                    aircraft_id=aircraft.id,
                    seat_class_id=config.seat_class_id,
                    seat_number=seat_number,
                )
            )

            # Move to next seat/row
            letter_idx += 1
            if letter_idx >= len(letters):
                letter_idx = 0
                current_row += 1

        # Start next class on a new row
        if letter_idx != 0:
            letter_idx = 0
            current_row += 1

    await db.commit()

    # Re-fetch with seats loaded to avoid MissingGreenlet error in response
    result = await db.execute(
        select(Aircraft).options(selectinload(Aircraft.seats)).where(Aircraft.id == aircraft.id)
    )
    aircraft = result.scalar_one()

    logger.info(
        f"[ADMIN] Created aircraft {aircraft.registration} with {total_calculated_seats} auto-generated seats"
    )
    return aircraft


from sqlalchemy.orm import selectinload


async def get_aircraft(db: AsyncSession) -> list[Aircraft]:
    result = await db.execute(
        select(Aircraft).options(selectinload(Aircraft.seats)).order_by(Aircraft.model)
    )
    return list(result.scalars().all())


async def update_aircraft(aircraft_id: int, body: AircraftUpdate, db: AsyncSession) -> Aircraft:
    result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = result.scalar_one_or_none()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found.")
    if body.registration:
        existing = await db.execute(
            select(Aircraft).where(
                Aircraft.registration == body.registration, Aircraft.id != aircraft_id
            )
        )

        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Aircraft already exists.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(aircraft, field, value)
    await db.commit()

    # Re-fetch with seats loaded to avoid MissingGreenlet error in response
    result = await db.execute(
        select(Aircraft).options(selectinload(Aircraft.seats)).where(Aircraft.id == aircraft_id)
    )
    aircraft = result.scalar_one()

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


async def update_seat_class(
    seat_class_id: int, body: SeatClassUpdate, db: AsyncSession
) -> SeatClass:
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

    in_use = await db.execute(
        select(FlightSeatPricing).where(FlightSeatPricing.seat_class_id == seat_class_id)
    )

    if in_use.scalars().first():
        raise HTTPException(status_code=409, detail="Cannot delete seat class in use by flights.")

    booking_in_use = await db.execute(select(Booking).where(Booking.seat_class_id == seat_class_id))

    if booking_in_use.scalars().first():
        raise HTTPException(status_code=409, detail="Cannot delete seat class used by bookings.")

    await db.delete(seat_class)
    await db.commit()

    logger.info(f"[ADMIN] Deleted seat class {seat_class_id}")


# ─── Aircraft Seat ─────────────────────────────────────────────────────────────


async def create_aircraft_seats(
    aircraft_id: int, seats: list[AircraftSeatCreate], db: AsyncSession
) -> list[AircraftSeat]:
    aircraft_result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = aircraft_result.scalar_one_or_none()  # consume once, store the object
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found.")

    new_seats = []
    for seat_data in seats:
        existing = await db.execute(
            select(AircraftSeat).where(
                AircraftSeat.aircraft_id == aircraft_id,
                AircraftSeat.seat_number == seat_data.seat_number,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Seat {seat_data.seat_number} already exists for this aircraft.",
            )
        seat = AircraftSeat(
            aircraft_id=aircraft_id,
            seat_class_id=seat_data.seat_class_id,
            seat_number=seat_data.seat_number,
        )
        db.add(seat)
        new_seats.append(seat)

    await db.flush()  # get IDs before count query

    count_result = await db.execute(
        select(func.count()).where(AircraftSeat.aircraft_id == aircraft_id)
    )
    aircraft.total_seats = count_result.scalar() or 0
    await db.commit()

    for seat in new_seats:
        await db.refresh(seat)

    logger.info(f"[ADMIN] Created {len(new_seats)} seats for aircraft {aircraft_id}")
    return new_seats


async def get_aircraft_seats(aircraft_id: int, db: AsyncSession) -> list[AircraftSeat]:
    result = await db.execute(
        select(AircraftSeat)
        .where(AircraftSeat.aircraft_id == aircraft_id)
        .order_by(AircraftSeat.seat_number)
    )
    return list(result.scalars().all())


async def delete_aircraft_seat(seat_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(AircraftSeat).where(AircraftSeat.id == seat_id))
    seat = result.scalar_one_or_none()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found.")

    aircraft_id = seat.aircraft_id
    await db.delete(seat)
    await db.commit()

    # Update total_seats
    aircraft_result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = aircraft_result.scalar_one()
    count_result = await db.execute(
        select(func.count()).where(AircraftSeat.aircraft_id == aircraft_id)
    )
    aircraft.total_seats = count_result.scalar() or 0
    await db.commit()

    logger.info(f"[ADMIN] Deleted aircraft seat {seat_id}")
