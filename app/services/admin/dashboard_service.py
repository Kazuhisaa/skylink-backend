import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.bookings import Booking
from app.models.flights import Flight

logger = logging.getLogger(__name__)


# ─── KPI dashboard Services ────────────────────────────────────────────────────────────


async def get_kpi_summary(db: AsyncSession) -> dict:
    from datetime import datetime, timezone

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
        select(func.coalesce(func.sum(Booking.total_price), 0)).where(
            Booking.booked_at >= current_start
        )
    )
    prev_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Booking.total_price), 0)).where(
            Booking.booked_at >= prev_start, Booking.booked_at < prev_end
        )
    )
    cur_revenue = cur_revenue_result.scalar() or 0
    prev_revenue = prev_revenue_result.scalar() or 0

    # Users
    cur_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= current_start)
    )
    prev_users_result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(User.created_at >= prev_start, User.created_at < prev_end)
    )
    cur_users = cur_users_result.scalar() or 0
    prev_users = prev_users_result.scalar() or 0

    # Flights (total, no time filter — just compare scheduled this month vs last)
    cur_flights_result = await db.execute(
        select(func.count()).select_from(Flight).where(Flight.created_at >= current_start)
    )
    prev_flights_result = await db.execute(
        select(func.count())
        .select_from(Flight)
        .where(Flight.created_at >= prev_start, Flight.created_at < prev_end)
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
            Booking.status != "cancelled", Booking.booked_at >= current_start
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


# ─── Revenue by Route ─────────────────────────────────────────────────────────
async def get_revenue_by_route(db: AsyncSession) -> list:
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.flight).selectinload(Flight.origin_airport),
            selectinload(Booking.flight).selectinload(Flight.destination_airport),
        )
        .where(Booking.status != "cancelled")
    )
    bookings = result.scalars().all()
    from collections import defaultdict

    route_map: dict = defaultdict(int)
    for b in bookings:
        if not b.flight or not b.flight.origin_airport or not b.flight.destination_airport:
            continue
        key = f"{b.flight.origin_airport.iata_code} → {b.flight.destination_airport.iata_code}"
        route_map[key] += b.total_price
    routes = sorted(route_map.items(), key=lambda x: x[1], reverse=True)[:5]
    return [{"route": route, "revenue": revenue} for route, revenue in routes]
