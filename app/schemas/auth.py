import uuid
from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, EmailStr, StringConstraints

PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=72)]
NameStr = Annotated[str, StringConstraints(min_length=1, max_length=100)]
PhoneStr = Annotated[str, StringConstraints(pattern=r"^(\+?63|0)9\d{9}$")]


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
    phone_number: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: PasswordStr


# --  Google auth ----


class GoogleAuthRequest(BaseModel):
    token: str
    mode: str = "login"  # "login" or "register"


class GoogleAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
