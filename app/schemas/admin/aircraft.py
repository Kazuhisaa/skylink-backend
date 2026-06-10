from typing import Optional

from pydantic import BaseModel


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


# --- Aircraft ---
class AircraftRead(BaseModel):
    id: int
    model: str
    total_seats: int
    registration: str
    seats: Optional[list[AircraftSeatRead]] = None
    model_config = {"from_attributes": True}


# --- Seat Class ---
class SeatClassRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
