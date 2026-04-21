from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BookingReportFilter(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class BookingReportRead(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    total_revenue: int
    confirmed_revenue: int
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None