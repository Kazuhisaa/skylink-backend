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


# --- Airport ---
class AirportCreate(BaseModel):
    iata_code: str
    name: str
    city: str
    country: str
    timezone: str

class AirportUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None



# --- Aircraft ---
class AircraftCreate(BaseModel):
    model: str
    total_seats: int
    registration: str


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