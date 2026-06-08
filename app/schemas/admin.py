from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# --- Bookings Report ---
class BookingReportFilter(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class MonthlyRevenuePoint(BaseModel):
    month: str        # e.g. "Jan", "Feb"
    year: int
    revenue: int
    bookings: int

class BookingReportRead(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    total_revenue: int
    confirmed_revenue: int
    monthly_revenue: list[MonthlyRevenuePoint] = []
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# --- Airport ---
class AirportCreate(BaseModel):
    iata_code: str
    name: str
    city: str
    country: str
    timezone: str
    about: Optional[str] = None     
    highlights: Optional[list[str]] = None  
    best_time: Optional[str] = None   
    image_url: Optional[str] = None      

class AirportUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    about: Optional[str] = None       
    highlights: Optional[list[str]] = None  
    best_time: Optional[str] = None     
    image_url: Optional[str] = None   


# --- Aircraft ---
class AircraftSeatConfig(BaseModel):
    seat_class_id: int
    quantity: int

class AircraftCreate(BaseModel):
    model: str
    registration: str
    seat_configurations: list[AircraftSeatConfig]


class AircraftUpdate(BaseModel):
    model: Optional[str] = None
    total_seats: Optional[int] = None
    registration: Optional[str] = None


# --- Seat Class ---
class SeatClassCreate(BaseModel):
    name: str

class SeatClassUpdate(BaseModel):
    name: Optional[str] = None


# --- Aircraft Seat ---
class AircraftSeatCreate(BaseModel):
    seat_class_id: int
    seat_number: str

class AircraftSeatRead(BaseModel):
    id: int
    aircraft_id: int
    seat_class_id: int
    seat_number: str

    model_config = {"from_attributes": True}


# --- Route Booking Point ---
class RouteBookingPoint(BaseModel):
    route: str       
    bookings: int
    revenue: int

class RouteReportRead(BaseModel):
    routes: list[RouteBookingPoint] = []
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