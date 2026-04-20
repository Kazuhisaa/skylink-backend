from pydantic import BaseModel, StringConstraints
from typing import Annotated, Optional
from datetime import datetime
import uuid

NameStr = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r'^[A-Za-z\s\-]+$')]
PhoneStr = Annotated[str, StringConstraints(
    pattern=r'^(09\d{9}|639\d{9})$'
)]


# --- Role ---
class RoleRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# --- User Profile ---
class UserProfileUpdate(BaseModel):
    first_name: Optional[NameStr] = None
    last_name: Optional[NameStr] = None
    phone_number: Optional[PhoneStr] = None

    model_config = {
        "extra": "forbid"
    }

class UserProfileRead(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: RoleRead
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    role_name: Optional[str] = None  # populated by admin endpoints

    model_config = {"from_attributes": True}