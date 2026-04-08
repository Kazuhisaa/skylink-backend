from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class RescheduleHistory(Base):
    __tablename__ = "reschedule_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    old_flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    new_flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    rescheduled_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(Text)
    rescheduled_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="reschedule_history", foreign_keys=[booking_id])
    rescheduled_by_user = relationship("User", back_populates="reschedules", foreign_keys=[rescheduled_by])


class Cancellation(Base):
    __tablename__ = "cancellations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, nullable=False)
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(Text)
    refund_amount = Column(Integer)
    cancelled_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="cancellation", foreign_keys=[booking_id])
    cancelled_by_user = relationship("User", back_populates="cancellations", foreign_keys=[cancelled_by])