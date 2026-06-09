import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from sqlalchemy.orm import selectinload

from app.models.bookings import Booking, Passenger
from app.models.flights import Flight, FlightSeatPricing
from app.models.audit import RescheduleHistory, Cancellation
from app.schemas.bookings import BookingCreate, RescheduleRequest, CancelRequest

logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────────

async def _get_booking_with_relations(booking_id: uuid.UUID, db: AsyncSession) -> Booking:
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.flight).selectinload(Flight.origin_airport),
            selectinload(Booking.flight).selectinload(Flight.destination_airport),
            selectinload(Booking.flight).selectinload(Flight.seat_pricing).selectinload(FlightSeatPricing.seat_class),
            selectinload(Booking.seat_class),
            selectinload(Booking.passengers),
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return booking


async def _get_pricing(flight_id: uuid.UUID, seat_class_id: int, db: AsyncSession) -> FlightSeatPricing:
    result = await db.execute(
        select(FlightSeatPricing).where(
            FlightSeatPricing.flight_id == flight_id,
            FlightSeatPricing.seat_class_id == seat_class_id,
        )
    )
    pricing = result.scalar_one_or_none()
    if not pricing:
        raise HTTPException(status_code=404, detail="Seat class not available for this flight.")
    return pricing


# ─── Passenger Services ────────────────────────────────────────────────────────

async def create_booking(body: BookingCreate, user_id: uuid.UUID, db: AsyncSession) -> Booking:
    # Check flight exists and is scheduled
    flight_result = await db.execute(select(Flight).where(Flight.id == body.flight_id))
    flight = flight_result.scalar_one_or_none()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found.")
    if flight.status != "scheduled":  # type: ignore
        raise HTTPException(status_code=400, detail="Flight is not available for booking.")

    # Check seat availability
    pricing = await _get_pricing(body.flight_id, body.seat_class_id, db)
    if pricing.available_seats <= 0:  # type: ignore
        raise HTTPException(status_code=400, detail="No available seats for this class.")

    # Create booking
    booking = Booking(
        id=uuid.uuid4(),
        user_id=user_id,
        flight_id=body.flight_id,
        seat_class_id=body.seat_class_id,
        seat_number=body.seat_number,
        status="confirmed",
        total_price=pricing.price,  # type: ignore
    )
    db.add(booking)
    await db.flush()

    # Add passengers
    for p in body.passengers:
        db.add(Passenger(
            booking_id=booking.id,
            first_name=p.first_name,
            last_name=p.last_name,
            date_of_birth=p.date_of_birth,
            passport_number=p.passport_number,
            nationality=p.nationality,
        ))

    # Decrement available seats
    pricing.available_seats -= 1  # type: ignore

    await db.commit()
    logger.info(f"[BOOKING] Created booking {booking.id} for user {user_id}")
    return await _get_booking_with_relations(booking.id, db)        # type: ignore


async def get_user_bookings(
    user_id: uuid.UUID, 
    db: AsyncSession,
    page: int = 1,
    size: int = 10
) -> tuple[list[Booking], int]:
    # Base query
    query = (
        select(Booking)
        .where(Booking.user_id == user_id)
        .options(
            selectinload(Booking.flight).selectinload(Flight.origin_airport),
            selectinload(Booking.flight).selectinload(Flight.destination_airport),
            selectinload(Booking.flight).selectinload(Flight.seat_pricing).selectinload(FlightSeatPricing.seat_class),
            selectinload(Booking.seat_class),
        )
        .order_by(Booking.booked_at.desc())
    )

    # Count total
    count_query = select(func.count()).select_from(Booking).where(Booking.user_id == user_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return items, total  # type: ignore


async def get_booking(booking_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Booking:
    booking = await _get_booking_with_relations(booking_id, db)
    if booking.user_id != user_id:  # type: ignore
        raise HTTPException(status_code=403, detail="Access denied.")
    return booking


async def reschedule_booking(
    booking_id: uuid.UUID,
    body: RescheduleRequest,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Booking:
    booking = await _get_booking_with_relations(booking_id, db)

    if booking.user_id != user_id:  # type: ignore
        raise HTTPException(status_code=403, detail="Access denied.")
    if booking.status == "cancelled":  # type: ignore
        raise HTTPException(status_code=400, detail="Cannot reschedule a cancelled booking.")

    # Check new flight exists and is scheduled
    new_flight_result = await db.execute(select(Flight).where(Flight.id == body.new_flight_id))
    new_flight = new_flight_result.scalar_one_or_none()
    if not new_flight:
        raise HTTPException(status_code=404, detail="New flight not found.")
    if new_flight.status != "scheduled":  # type: ignore
        raise HTTPException(status_code=400, detail="New flight is not available.")
    if body.new_flight_id == booking.flight_id:  # type: ignore
        raise HTTPException(status_code=400, detail="New flight is the same as current flight.")

    # Check seat availability on new flight
    new_pricing = await _get_pricing(body.new_flight_id, booking.seat_class_id, db)  # type: ignore
    if new_pricing.available_seats <= 0:  # type: ignore
        raise HTTPException(status_code=400, detail="No available seats on new flight.")

    # Record reschedule history
    db.add(RescheduleHistory(
        booking_id=booking.id,
        old_flight_id=booking.flight_id,
        new_flight_id=body.new_flight_id,
        rescheduled_by=user_id,
        reason=body.reason,
    ))

    # Restore seat on old flight
    old_pricing = await _get_pricing(booking.flight_id, booking.seat_class_id, db)  # type: ignore
    old_pricing.available_seats += 1  # type: ignore

    # Decrement seat on new flight
    new_pricing.available_seats -= 1  # type: ignore

    # Update booking
    booking.flight_id = body.new_flight_id  # type: ignore
    booking.total_price = new_pricing.price  # type: ignore

    await db.commit()
    await db.refresh(booking)
    
    logger.info(f"[BOOKING] Rescheduled booking {booking_id} to flight {body.new_flight_id}")
    return await _get_booking_with_relations(booking_id, db)


async def cancel_booking(
    booking_id: uuid.UUID,
    body: CancelRequest,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    booking = await _get_booking_with_relations(booking_id, db)

    if booking.user_id != user_id:  # type: ignore
        raise HTTPException(status_code=403, detail="Access denied.")
    if booking.status == "cancelled":  # type: ignore
        raise HTTPException(status_code=400, detail="Booking is already cancelled.")

    # Record cancellation
    db.add(Cancellation(
        booking_id=booking.id,
        cancelled_by=user_id,
        reason=body.reason,
        refund_amount=booking.total_price,  # type: ignore
    ))

    # Restore seat
    pricing = await _get_pricing(booking.flight_id, booking.seat_class_id, db)  # type: ignore
    pricing.available_seats += 1  # type: ignore

    # Update booking status
    booking.status = "cancelled"  # type: ignore

    await db.commit()
    logger.info(f"[BOOKING] Cancelled booking {booking_id} by user {user_id}")


# ─── Admin Services ────────────────────────────────────────────────────────────

async def get_all_bookings(
    db: AsyncSession,
    page: int = 1,
    size: int = 10
) -> tuple[list[Booking], int]:
    # Base query
    query = (
        select(Booking)
        .options(
            selectinload(Booking.flight).selectinload(Flight.origin_airport),
            selectinload(Booking.flight).selectinload(Flight.destination_airport),
            selectinload(Booking.flight).selectinload(Flight.seat_pricing).selectinload(FlightSeatPricing.seat_class),
            selectinload(Booking.seat_class),
        )
        .order_by(Booking.booked_at.desc())
    )

    # Count total
    count_query = select(func.count()).select_from(Booking)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return items, total  # type: ignore


# ─── Booking by PNR ────────────────────────────────────────────────────────────

async def _find_booking_by_pnr(pnr: str, db: AsyncSession) -> Booking:
    # Reliable search: convert UUID to text, remove hyphens, uppercase, and match prefix
    # id::text converts UUID to string with hyphens
    # replace(..., '-', '') removes hyphens
    # upper(...) makes it uppercase
    # Then we check if it starts with the 8-char PNR
    query = (
        select(Booking)
        .where(func.upper(func.replace(cast(Booking.id, String), "-", "")).like(f"{pnr.upper()}%"))
        .options(
            selectinload(Booking.flight).selectinload(Flight.origin_airport),
            selectinload(Booking.flight).selectinload(Flight.destination_airport),
            selectinload(Booking.flight).selectinload(Flight.seat_pricing).selectinload(FlightSeatPricing.seat_class),
            selectinload(Booking.seat_class),
            selectinload(Booking.passengers),
        )
    )
    
    result = await db.execute(query)
    booking = result.scalar_one_or_none()
    
    if not booking:
        logger.warning(f"PNR search failed for: {pnr}")
        raise HTTPException(status_code=404, detail="Booking not found.")
    return booking


def _build_pnr_response(booking: Booking, pnr: str) -> dict:
    return {
        "pnr": pnr.upper(),
        "booking_id": str(booking.id),
        "booking_status": booking.status,
        "journey_status": booking.flight.status,
        "itinerary": [{
            "id": str(booking.flight.id),
            "flightNumber": booking.flight.flight_number,
            "origin": booking.flight.origin_airport.iata_code,
            "destination": booking.flight.destination_airport.iata_code,
            "departureTime": booking.flight.departure_time.isoformat(),
            "arrivalTime": booking.flight.arrival_time.isoformat(),
            "status": booking.flight.status,
        }],
        "passengers": booking.passengers,
        "updated_at": booking.updated_at,
    }


async def get_booking_by_pnr(pnr: str, db: AsyncSession) -> dict:
    booking = await _find_booking_by_pnr(pnr, db)
    return _build_pnr_response(booking, pnr)


async def get_booking_by_pnr_public(pnr: str, last_name: str, db: AsyncSession) -> dict:
    booking = await _find_booking_by_pnr(pnr, db)
    passenger_last_names = [p.last_name.lower() for p in booking.passengers]
    if last_name.lower() not in passenger_last_names:
        raise HTTPException(status_code=403, detail="Last name does not match booking.")
    return _build_pnr_response(booking, pnr)