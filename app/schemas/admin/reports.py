from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BookingReportFilter(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class MonthlyRevenuePoint(BaseModel):
    month: str
    year: int
    revenue: float
    bookings: int


class RouteBookingPoint(BaseModel):
    route: str
    bookings: int
    revenue: float


class RouteReportRead(BaseModel):
    routes: list[RouteBookingPoint] = []
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class BookingReportRead(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    total_revenue: float
    confirmed_revenue: float
    monthly_revenue: list[MonthlyRevenuePoint] = []
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# --- Cancellation Report ---
class MonthlyCancellationPoint(BaseModel):
    month: str
    year: int
    total_bookings: int
    cancelled_bookings: int
    cancellation_rate: float


class CancellationReportRead(BaseModel):
    monthly_cancellations: list[MonthlyCancellationPoint] = []
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# --- User Growth Report ---
class MonthlyUserGrowthPoint(BaseModel):
    month: str
    year: int
    new_users: int


class UserGrowthReportRead(BaseModel):
    monthly_growth: list[MonthlyUserGrowthPoint] = []
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# --- Activity Log ---
class ActivityLogRead(BaseModel):
    id: str
    email: str
    ip_address: Optional[str] = None
    attempted_at: datetime

    model_config = {"from_attributes": True}


class ActivityLogListRead(BaseModel):
    logs: list[ActivityLogRead] = []
    total: int
