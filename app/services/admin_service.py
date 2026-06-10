import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.bookings import Booking

from app.schemas.admin import BookingReportRead, MonthlyRevenuePoint, RouteReportRead, RouteBookingPoint, AirportCreate, AircraftCreate, SeatClassCreate, AirportUpdate, AircraftUpdate, SeatClassUpdate, AircraftSeatCreate, CancellationReportRead, MonthlyCancellationPoint, UserGrowthReportRead, MonthlyUserGrowthPoint, ActivityLogListRead, ActivityLogRead

from app.models.flights import Flight, Airport, Aircraft, SeatClass, FlightSeatPricing, AircraftSeat
from app.auth.models import User, LoginAttempt

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

# ─── Aircraft ──────────────────────────────────────────────────────────────────

async def create_aircraft(body: AircraftCreate, db: AsyncSession) -> Aircraft:
    existing = await db.execute(select(Aircraft).where(Aircraft.registration == body.registration))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Aircraft with this registration already exists.")
    
    total_calculated_seats = sum(config.quantity for config in body.seat_configurations)
    
    aircraft = Aircraft(
        model=body.model,
        total_seats=total_calculated_seats,
        registration=body.registration,
    )
    db.add(aircraft)
    await db.flush() # get aircraft.id

    # Automatic Seat Generation (Row + Letter Pattern: A, B, C, D, E, F)
    letters = ["A", "B", "C", "D", "E", "F"]
    current_row = 1
    letter_idx = 0

    for config in body.seat_configurations:
        for _ in range(config.quantity):
            seat_number = f"{current_row}{letters[letter_idx]}"
            db.add(AircraftSeat(
                aircraft_id=aircraft.id,
                seat_class_id=config.seat_class_id,
                seat_number=seat_number
            ))
            
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
        select(Aircraft)
        .options(selectinload(Aircraft.seats))
        .where(Aircraft.id == aircraft.id)
    )
    aircraft = result.scalar_one()
    
    logger.info(f"[ADMIN] Created aircraft {aircraft.registration} with {total_calculated_seats} auto-generated seats")
    return aircraft

from sqlalchemy.orm import selectinload

async def get_aircraft(db: AsyncSession) -> list[Aircraft]:
    result = await db.execute(
        select(Aircraft)
        .options(selectinload(Aircraft.seats))
        .order_by(Aircraft.model)
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
                Aircraft.registration == body.registration,
                Aircraft.id != aircraft_id
            )
        )

        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Aircraft already exists.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(aircraft, field, value)
    await db.commit()
    
    # Re-fetch with seats loaded to avoid MissingGreenlet error in response
    result = await db.execute(
        select(Aircraft)
        .options(selectinload(Aircraft.seats))
        .where(Aircraft.id == aircraft_id)
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

    # Build monthly breakdown
    from collections import defaultdict
    monthly: dict = defaultdict(lambda: {"revenue": 0, "bookings": 0})
    for b in bookings:
        key = b.booked_at.strftime("%Y-%m")
        monthly[key]["revenue"] += b.total_price
        monthly[key]["bookings"] += 1

    monthly_revenue = [
        MonthlyRevenuePoint(
            month=datetime.strptime(k, "%Y-%m").strftime("%b"),
            year=int(k.split("-")[0]),
            revenue=v["revenue"],
            bookings=v["bookings"],
        )
        for k, v in sorted(monthly.items())
    ]

    logger.info(f"[ADMIN] Report generated — total={total_bookings} revenue={total_revenue}")
    return BookingReportRead(
        total_bookings=total_bookings,
        confirmed_bookings=len(confirmed),
        cancelled_bookings=len(cancelled),
        total_revenue=total_revenue,
        confirmed_revenue=confirmed_revenue,
        monthly_revenue=monthly_revenue,
        date_from=date_from,
        date_to=date_to,
    )


# ─── Aircraft Seat ─────────────────────────────────────────────────────────────

async def create_aircraft_seats(aircraft_id: int, seats: list[AircraftSeatCreate], db: AsyncSession) -> list[AircraftSeat]:
    aircraft_result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = aircraft_result.scalar_one_or_none()  # consume once, store the object
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found.")

    new_seats = []
    for seat_data in seats:
        existing = await db.execute(
            select(AircraftSeat).where(
                AircraftSeat.aircraft_id == aircraft_id,
                AircraftSeat.seat_number == seat_data.seat_number
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Seat {seat_data.seat_number} already exists for this aircraft."
            )
        seat = AircraftSeat(
            aircraft_id=aircraft_id,
            seat_class_id=seat_data.seat_class_id,
            seat_number=seat_data.seat_number
        )
        db.add(seat)
        new_seats.append(seat)

    await db.flush()  # get IDs before count query

    count_result = await db.execute(select(func.count()).where(AircraftSeat.aircraft_id == aircraft_id))
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
    count_result = await db.execute(select(func.count()).where(AircraftSeat.aircraft_id == aircraft_id))
    aircraft.total_seats = count_result.scalar() or 0
    await db.commit()

    logger.info(f"[ADMIN] Deleted aircraft seat {seat_id}")


async def get_route_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> "RouteReportRead":

    query = (
        select(Booking)
        .options(
            selectinload(Booking.flight).selectinload(Flight.origin_airport),
            selectinload(Booking.flight).selectinload(Flight.destination_airport),
        )
    )
    if date_from:
        query = query.where(Booking.booked_at >= date_from)
    if date_to:
        query = query.where(Booking.booked_at <= date_to)

    result = await db.execute(query)
    bookings = result.scalars().all()

    from collections import defaultdict
    route_map: dict = defaultdict(lambda: {"bookings": 0, "revenue": 0})
    for b in bookings:
        origin = b.flight.origin_airport.iata_code
        dest = b.flight.destination_airport.iata_code
        key = f"{origin} → {dest}"
        route_map[key]["bookings"] += 1
        route_map[key]["revenue"] += b.total_price

    routes = [
        RouteBookingPoint(route=k, bookings=v["bookings"], revenue=v["revenue"])
        for k, v in sorted(route_map.items(), key=lambda x: x[1]["bookings"], reverse=True)
    ]

    return RouteReportRead(routes=routes, date_from=date_from, date_to=date_to)


# ─── Cancellation Report ─────────────────────────────────────────────────────────────

async def get_cancellation_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> "CancellationReportRead":


    query = select(Booking)
    if date_from:
        query = query.where(Booking.booked_at >= date_from)
    if date_to:
        query = query.where(Booking.booked_at <= date_to)

    result = await db.execute(query)
    bookings = result.scalars().all()

    from collections import defaultdict
    monthly: dict = defaultdict(lambda: {"total": 0, "cancelled": 0})
    for b in bookings:
        key = b.booked_at.strftime("%Y-%m")
        monthly[key]["total"] += 1
        if b.status == "cancelled":
            monthly[key]["cancelled"] += 1

    monthly_cancellations = [
        MonthlyCancellationPoint(
            month=datetime.strptime(k, "%Y-%m").strftime("%b"),
            year=int(k.split("-")[0]),
            total_bookings=v["total"],
            cancelled_bookings=v["cancelled"],
            cancellation_rate=round((v["cancelled"] / v["total"]) * 100, 1) if v["total"] > 0 else 0.0,
        )
        for k, v in sorted(monthly.items())
    ]

    logger.info(f"[ADMIN] Cancellation report generated — months={len(monthly_cancellations)}")
    return CancellationReportRead(
        monthly_cancellations=monthly_cancellations,
        date_from=date_from,
        date_to=date_to,
    )


# ─── User Growth Report ─────────────────────────────────────────────────────────────

async def get_user_growth_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> "UserGrowthReportRead":

    query = select(User)
    if date_from:
        query = query.where(User.created_at >= date_from)
    if date_to:
        query = query.where(User.created_at <= date_to)

    result = await db.execute(query)
    users = result.scalars().all()

    from collections import defaultdict
    monthly: dict = defaultdict(int)
    for u in users:
        key = u.created_at.strftime("%Y-%m")
        monthly[key] += 1

    monthly_growth = [
        MonthlyUserGrowthPoint(
            month=datetime.strptime(k, "%Y-%m").strftime("%b"),
            year=int(k.split("-")[0]),
            new_users=v,
        )
        for k, v in sorted(monthly.items())
    ]

    logger.info(f"[ADMIN] User growth report generated — months={len(monthly_growth)}")
    return UserGrowthReportRead(
        monthly_growth=monthly_growth,
        date_from=date_from,
        date_to=date_to,
    )


# ─── Activity Log ─────────────────────────────────────────────────────────────

async def get_activity_logs(
    db: AsyncSession,
    page: int = 1,
    size: int = 8,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> "ActivityLogListRead":

    query = select(LoginAttempt).order_by(LoginAttempt.attempted_at.desc())

    if search:
        query = query.where(LoginAttempt.email.ilike(f"%{search}%"))
    if date_from:
        query = query.where(LoginAttempt.attempted_at >= date_from)
    if date_to:
        query = query.where(LoginAttempt.attempted_at <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    logs = result.scalars().all()

    logger.info(f"[ADMIN] Activity logs fetched — page={page} total={total}")
    return ActivityLogListRead(
        logs=[
            ActivityLogRead(
                id=str(log.id),
                email=log.email,
                ip_address=log.ip_address,
                attempted_at=log.attempted_at,
            )
            for log in logs
        ],
        total=total,
    )


# ─── KPI dashboard Services ────────────────────────────────────────────────────────────

async def get_kpi_summary(db: AsyncSession) -> dict:
    from datetime import timezone, datetime
    now = datetime.now(timezone.utc)
    
    # Current month boundaries
    current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Previous month boundaries
    if current_start.month == 1:
        prev_start = current_start.replace(year=current_start.year - 1, month=12)
    else:
        prev_start = current_start.replace(month=current_start.month - 1)
    prev_end = current_start

    def pct_change(current: int, previous: int) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    # Bookings
    cur_bookings_result = await db.execute(
        select(func.count()).where(Booking.booked_at >= current_start)
    )
    prev_bookings_result = await db.execute(
        select(func.count()).where(Booking.booked_at >= prev_start, Booking.booked_at < prev_end)
    )
    cur_bookings = cur_bookings_result.scalar() or 0
    prev_bookings = prev_bookings_result.scalar() or 0

    # Revenue
    cur_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Booking.total_price), 0)).where(Booking.booked_at >= current_start)
    )
    prev_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Booking.total_price), 0)).where(Booking.booked_at >= prev_start, Booking.booked_at < prev_end)
    )
    cur_revenue = cur_revenue_result.scalar() or 0
    prev_revenue = prev_revenue_result.scalar() or 0

    # Users
    cur_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= current_start)
    )
    prev_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= prev_start, User.created_at < prev_end)
    )
    cur_users = cur_users_result.scalar() or 0
    prev_users = prev_users_result.scalar() or 0

    # Flights (total, no time filter — just compare scheduled this month vs last)
    cur_flights_result = await db.execute(
        select(func.count()).select_from(Flight).where(Flight.created_at >= current_start)
    )
    prev_flights_result = await db.execute(
        select(func.count()).select_from(Flight).where(Flight.created_at >= prev_start, Flight.created_at < prev_end)
    )
    cur_flights = cur_flights_result.scalar() or 0
    prev_flights = prev_flights_result.scalar() or 0

    # Totals (all time) for display values
    total_flights_result = await db.execute(select(func.count()).select_from(Flight))
    total_bookings_result = await db.execute(
        select(func.count()).select_from(Booking).where(Booking.status != "cancelled")
    )
    total_users_result = await db.execute(select(func.count()).select_from(User))
    total_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Booking.total_price), 0)).where(
            Booking.status != "cancelled",
            Booking.booked_at >= current_start
        )
    )

    return {
        "total_flights": total_flights_result.scalar() or 0,
        "total_bookings": total_bookings_result.scalar() or 0,
        "total_users": total_users_result.scalar() or 0,
        "total_revenue": total_revenue_result.scalar() or 0,
        "flights_change": pct_change(cur_flights, prev_flights),
        "bookings_change": pct_change(cur_bookings, prev_bookings),
        "users_change": pct_change(cur_users, prev_users),
        "revenue_change": pct_change(cur_revenue, prev_revenue),
    }