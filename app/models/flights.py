import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, CHAR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Airport(Base):
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    iata_code = Column(CHAR(3), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    timezone = Column(String(60), nullable=False)

    origin_flights = relationship("Flight", back_populates="origin_airport", foreign_keys="Flight.origin_airport_id")
    destination_flights = relationship("Flight", back_populates="destination_airport", foreign_keys="Flight.destination_airport_id")


class Aircraft(Base):
    __tablename__ = "aircraft"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model = Column(String(100), nullable=False)
    total_seats = Column(Integer, nullable=False)
    registration = Column(String(20), unique=True, nullable=False)

    flights = relationship("Flight", back_populates="aircraft")
    seats = relationship("AircraftSeat", back_populates="aircraft", cascade="all, delete-orphan")


class AircraftSeat(Base):
    __tablename__ = "aircraft_seats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aircraft_id = Column(Integer, ForeignKey("aircraft.id"), nullable=False)
    seat_class_id = Column(Integer, ForeignKey("seat_classes.id"), nullable=False)
    seat_number = Column(String(10), nullable=False)

    aircraft = relationship("Aircraft", back_populates="seats")
    seat_class = relationship("SeatClass")


class SeatClass(Base):
    __tablename__ = "seat_classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    flight_pricing = relationship("FlightSeatPricing", back_populates="seat_class")
    bookings = relationship("Booking", back_populates="seat_class")
    aircraft_seats = relationship("AircraftSeat", back_populates="seat_class")


class Flight(Base):
    __tablename__ = "flights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_number = Column(String(10), unique=True, nullable=False)
    aircraft_id = Column(Integer, ForeignKey("aircraft.id"), nullable=False)
    origin_airport_id = Column(Integer, ForeignKey("airports.id"), nullable=False)
    destination_airport_id = Column(Integer, ForeignKey("airports.id"), nullable=False)
    departure_time = Column(TIMESTAMP(timezone=True), nullable=False)
    arrival_time = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="scheduled")
    image_url = Column(String(255), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    aircraft = relationship("Aircraft", back_populates="flights")
    origin_airport = relationship("Airport", back_populates="origin_flights", foreign_keys=[origin_airport_id])
    destination_airport = relationship("Airport", back_populates="destination_flights", foreign_keys=[destination_airport_id])
    created_by_user = relationship("User", back_populates="created_flights")
    seat_pricing = relationship("FlightSeatPricing", back_populates="flight")
    bookings = relationship("Booking", back_populates="flight")


class FlightSeatPricing(Base):
    __tablename__ = "flight_seat_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    seat_class_id = Column(Integer, ForeignKey("seat_classes.id"), nullable=False)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)  # store as centavos if PHP, or use Numeric

    flight = relationship("Flight", back_populates="seat_pricing")
    seat_class = relationship("SeatClass", back_populates="flight_pricing")
