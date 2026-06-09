from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
import uuid
from datetime import datetime

class PaymentCreate(BaseModel):
    booking_id: uuid.UUID
    amount: int  # in centavos for PHP
    method: str = "card"

class PaymentResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: int
    currency: str
    status: str
    gateway_ref: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# PayMongo Specific Schemas
class PayMongoPaymentIntentCreate(BaseModel):
    amount: int
    payment_method_allowed: List[str] = ["card", "paymaya", "gcash", "grab_pay", "paymongo_qr"]
    payment_method_options: Dict[str, Any] = {"card": {"installments": None}}
    currency: str = "PHP"
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}

class PayMongoWebhookPayload(BaseModel):
    data: Dict[str, Any]
