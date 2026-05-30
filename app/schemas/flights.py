from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import uuid


# --- Airport ---
class AirportRead(BaseModel):
    id: int
    iata_code: str
    name: str
    city: str
    country: str
    timezone: str

    model_config = {"from_attributes": True}


# --- Aircraft ---
class AircraftRead(BaseModel):
    id: int
    model: str
    total_seats: int
    registration: str
    seats: Optional[list["AircraftSeatRead"]] = None

    model_config = {"from_attributes": True}


from app.schemas.admin import AircraftSeatRead
AircraftRead.model_rebuild()


# --- Seat Class ---
class SeatClassRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# --- Flight Seat Pricing ---
class FlightSeatPricingRead(BaseModel):
    id: int
    seat_class: SeatClassRead
    total_seats: int
    available_seats: int
    price: int

    model_config = {"from_attributes": True}


# --- Flight ---
class FlightCreate(BaseModel):
    flight_number: str
    aircraft_id: int
    origin_airport_id: int
    destination_airport_id: int
    departure_time: datetime
    arrival_time: datetime
    status: str = "scheduled"
    image_url: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"scheduled", "completed", "cancelled"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @field_validator("arrival_time")
    @classmethod
    def arrival_after_departure(cls, v: datetime, info) -> datetime:
        departure = info.data.get("departure_time")
        if departure and v <= departure:
            raise ValueError("Arrival time must be after departure time")
        return v


class FlightUpdate(BaseModel):
    flight_number: Optional[str] = None
    aircraft_id: Optional[int] = None
    origin_airport_id: Optional[int] = None
    destination_airport_id: Optional[int] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    status: Optional[str] = None
    image_url: Optional[str] = None


class FlightRead(BaseModel):
    id: uuid.UUID
    flight_number: str
    aircraft: AircraftRead
    origin_airport: AirportRead
    destination_airport: AirportRead
    departure_time: datetime
    arrival_time: datetime
    status: str
    image_url: Optional[str] = None
    created_at: datetime
    seat_pricing: list[FlightSeatPricingRead] = []

    model_config = {"from_attributes": True}


class FlightListRead(BaseModel):
    id: uuid.UUID
    flight_number: str
    origin_airport: AirportRead
    destination_airport: AirportRead
    departure_time: datetime
    arrival_time: datetime
    status: str
    image_url: Optional[str] = None
    seat_pricing: list[FlightSeatPricingRead] = []

    model_config = {"from_attributes": True}


# --- Flight Seat Pricing Create (used when creating a flight) ---
class FlightSeatPricingCreate(BaseModel):
    seat_class_id: int
    price: int


class FlightCreateWithPricing(FlightCreate):
    seat_pricing: Optional[list[FlightSeatPricingCreate]] = None
