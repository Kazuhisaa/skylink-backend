import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.bookings import Booking

from app.schemas.admin.reports import RouteReportRead, RouteBookingPoint, CancellationReportRead, MonthlyCancellationPoint, UserGrowthReportRead, MonthlyUserGrowthPoint, ActivityLogListRead, ActivityLogRead

from app.models.flights import Flight
from app.models.auth import User, LoginAttempt


logger = logging.getLogger(__name__)



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
        if b.status != "cancelled":
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

