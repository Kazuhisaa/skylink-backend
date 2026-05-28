from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from decimal import Decimal
import uuid


class PromotionBase(BaseModel):
    title: str
    sale_price: Decimal
    original_price: Decimal
    discount_text: Optional[str] = None
    badge_text: Optional[str] = None
    badge_type: Optional[str] = None
    valid_until: date
    image_url: str
    destination_city: Optional[str] = None
    destination_code: Optional[str] = None


class PromotionCreate(PromotionBase):
    pass


class PromotionUpdate(BaseModel):
    title: Optional[str] = None
    sale_price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount_text: Optional[str] = None
    badge_text: Optional[str] = None
    badge_type: Optional[str] = None
    valid_until: Optional[date] = None
    image_url: Optional[str] = None
    destination_city: Optional[str] = None
    destination_code: Optional[str] = None


class PromotionRead(PromotionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}