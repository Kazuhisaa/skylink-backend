import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    seat_class_id = Column(Integer, ForeignKey("seat_classes.id"), nullable=False)
    seat_number = Column(String(5))
    status = Column(String(20), nullable=False, default="pending")
    total_price = Column(Integer, nullable=False)
    booked_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="bookings", foreign_keys=[user_id])
    flight = relationship("Flight", back_populates="bookings")
    seat_class = relationship("SeatClass", back_populates="bookings")
    passengers = relationship("Passenger", back_populates="booking")
    payment = relationship("Payment", back_populates="booking", uselist=False)
    reschedule_history = relationship("RescheduleHistory", back_populates="booking", foreign_keys="RescheduleHistory.booking_id")
    cancellation = relationship("Cancellation", back_populates="booking", uselist=False)


class Passenger(Base):
    __tablename__ = "passengers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    passport_number = Column(String(50))
    nationality = Column(String(80))

    booking = relationship("Booking", back_populates="passengers")