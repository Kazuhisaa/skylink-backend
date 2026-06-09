import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, CHAR
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(CHAR(3), nullable=False, default="PHP")
    method = Column(String(30), nullable=False)  # e.g., 'paymongo'
    payment_method_type = Column(String(30))      # e.g., 'card', 'gcash', 'paymaya'
    status = Column(String(20), nullable=False, default="pending")
    gateway_ref = Column(String(100))             # payment_intent_id
    checkout_url = Column(String(500))            # For redirect-based payments
    external_metadata = Column(JSONB)             # Store raw response from PayMongo
    paid_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    booking = relationship("Booking", back_populates="payment")