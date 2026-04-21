import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.bookings import Booking
from app.schemas.admin import BookingReportRead

logger = logging.getLogger(__name__)


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


