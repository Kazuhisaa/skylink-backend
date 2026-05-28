import uuid
from sqlalchemy import Column, String, Numeric, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=False)
    discount_text = Column(String(50), nullable=True)
    badge_text = Column(String(50), nullable=True)
    badge_type = Column(String(20), nullable=True)
    valid_until = Column(String(100), nullable=False)
    image_url = Column(String(255), nullable=False)
    destination_city = Column(String(100), nullable=True)
    destination_code = Column(String(10), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
