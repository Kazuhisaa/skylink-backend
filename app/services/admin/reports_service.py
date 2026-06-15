import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import LoginAttempt, User
from app.models.bookings import Booking
from app.models.flights import Flight
from app.schemas.admin.reports import (
    ActivityLogListRead,
    ActivityLogRead,
    BookingReportRead,
    CancellationReportRead,
    MonthlyCancellationPoint,
    MonthlyRevenuePoint,
    MonthlyUserGrowthPoint,
    RawRouteEntry,
    RouteBookingPoint,
    RouteReportRead,
    UserGrowthReportRead,
)

logger = logging.getLogger(__name__)


async def get_route_report(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> "RouteReportRead":
    query = select(Booking).options(
        selectinload(Booking.flight).selectinload(Flight.origin_airport),
        selectinload(Booking.flight).selectinload(Flight.destination_airport),
    )
    result = await db.execute(query)
    bookings = result.scalars().all()
    from collections import defaultdict
    route_map: dict = defaultdict(lambda: {"bookings": 0, "revenue": 0, "booked_at": []})
    for b in bookings:
        origin = b.flight.origin_airport.iata_code
        dest = b.flight.destination_airport.iata_code
        key = f"{origin} → {dest}"
        route_map[key]["bookings"] += 1
        route_map[key]["booked_at"].append(b.booked_at)
        if b.status != "cancelled":
            route_map[key]["revenue"] += b.total_price
    routes = [
        RouteBookingPoint(route=k, bookings=v["bookings"], revenue=v["revenue"])
        for k, v in sorted(route_map.items(), key=lambda x: x[1]["bookings"], reverse=True)
    ]
    raw = [
        RawRouteEntry(
            route=f"{b.flight.origin_airport.iata_code} → {b.flight.destination_airport.iata_code}",
            revenue=float(b.total_price) if b.status != "cancelled" else 0,
            booked_at=b.booked_at,
            status=b.status,
        )
        for b in bookings
    ]
    return RouteReportRead(routes=routes, raw=raw, date_from=None, date_to=None)


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
            cancellation_rate=round((v["cancelled"] / v["total"]) * 100, 1)
            if v["total"] > 0
            else 0.0,
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

    query = (
        select(LoginAttempt)
        .where(LoginAttempt.is_admin == True)
        .order_by(LoginAttempt.attempted_at.desc())
    )
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
                success=log.success,
                is_admin=log.is_admin,
                attempted_at=log.attempted_at,
            )
            for log in logs
        ],
        total=total,
    )


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
    confirmed = [b for b in bookings if b.status != "cancelled"]
    cancelled = [b for b in bookings if b.status == "cancelled"]
    total_revenue = sum(b.total_price for b in bookings)
    confirmed_revenue = sum(b.total_price for b in confirmed)
    # Build monthly breakdown
    from collections import defaultdict

    monthly: dict = defaultdict(lambda: {"revenue": 0, "bookings": 0})
    for b in confirmed:
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
