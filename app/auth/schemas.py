from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Annotated, Optional
from datetime import datetime
import uuid

PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=72)]
NameStr = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r'^[A-Za-z\s\-]+$')]
PhoneStr = Annotated[str, StringConstraints(pattern=r'^\+?\d{7,15}$')]


class LoginRequest(BaseModel):
    email: EmailStr
    password: PasswordStr


class RegisterRequest(BaseModel):
    first_name: NameStr
    last_name: NameStr
    email: EmailStr
    password: PasswordStr
    phone_number: Optional[PhoneStr] = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"