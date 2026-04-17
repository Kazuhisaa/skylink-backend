from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import Optional
import uuid

from app.schemas.flights import FlightListRead, SeatClassRead


# --- Passenger ---
class PassengerCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    passport_number: str
    nationality: str


class PassengerRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    date_of_birth: date
    passport_number: str
    nationality: str

    model_config = {"from_attributes": True}


# --- Booking ---
class BookingCreate(BaseModel):
    flight_id: uuid.UUID
    seat_class_id: int
    seat_number: Optional[str] = None
    passengers: list[PassengerCreate]

    @field_validator("passengers")
    @classmethod
    def at_least_one_passenger(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one passenger is required.")
        return v


class BookingRead(BaseModel):
    id: uuid.UUID
    flight: FlightListRead
    seat_class: SeatClassRead
    seat_number: Optional[str] = None
    status: str
    total_price: int
    booked_at: datetime
    updated_at: datetime
    passengers: list[PassengerRead] = []

    model_config = {"from_attributes": True}


class BookingListRead(BaseModel):
    id: uuid.UUID
    flight: FlightListRead
    seat_class: SeatClassRead
    seat_number: Optional[str] = None
    status: str
    total_price: int
    booked_at: datetime

    model_config = {"from_attributes": True}


# --- Reschedule ---
class RescheduleRequest(BaseModel):
    new_flight_id: uuid.UUID
    reason: Optional[str] = None


# --- Cancel ---
class CancelRequest(BaseModel):
    reason: Optional[str] = None