from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import uuid


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None


class UserStatusUpdate(BaseModel):
    is_active: bool