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
    valid_until: str
    image_url: str
    destination_city: Optional[str] = None
    destination_code: Optional[str] = None

class PromotionCreate(PromotionBase):
    pass

class PromotionRead(PromotionBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
