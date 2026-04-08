import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, CHAR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(CHAR(3), nullable=False, default="PHP")
    method = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    gateway_ref = Column(String(100))
    paid_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="payment")