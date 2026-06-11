import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.auth import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    GoogleAuthResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserRead,
    VerifyOTPRequest,
)
from app.services.auth_services import create_admin, create_passenger, verify_user
from app.services.email_service import send_password_reset_email
from app.services.google_service import google_login_or_register

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=UserRead)
@limiter.limit("60/minute")
async def me(request: Request, current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    user = await verify_user(body.email, body.password, ip, db)
    token = create_access_token({"sub": user["id"], "role_id": user["role_id"]})
    return TokenResponse(access_token=token)


@router.post("/register", response_model=UserRead, status_code=201)
@limiter.limit("5/minute")
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await create_passenger(body, db)
    return user


@router.get("/verify-email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request, token: str = Query(...), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token.")
    if user.is_verified:  # type: ignore[truthy-bool]
        return {"message": "Email already verified."}
    if user.verification_token_expires_at < datetime.now(timezone.utc):  # type: ignore[operator]
        raise HTTPException(status_code=400, detail="Verification token has expired.")
    user.is_verified = True  # type: ignore[assignment]
    user.verification_token = None  # type: ignore[assignment]
    user.verification_token_expires_at = None  # type: ignore[assignment]
    await db.commit()
    return {"message": "Email verified successfully."}


@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(
    body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user:
        otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        user.reset_password_otp = otp  # type: ignore[assignment]
        user.reset_password_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)  # type: ignore[assignment]
        await db.commit()
        await send_password_reset_email(user.email, otp)  # type: ignore[arg-type]
    return {
        "message": "If your email is registered, you will receive a 6-digit verification code shortly."
    }


@router.post("/verify-otp")
@limiter.limit("10/hour")
async def verify_otp(body: VerifyOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or user.reset_password_otp != body.otp:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    if user.reset_password_expires_at < datetime.now(timezone.utc):  # type: ignore[operator]
        raise HTTPException(status_code=400, detail="Verification code has expired.")

    # Generate a temporary token to allow password reset
    reset_token = secrets.token_urlsafe(32)
    user.reset_password_token = reset_token  # type: ignore[assignment]
    await db.commit()

    return {"message": "OTP verified successfully.", "reset_token": reset_token}


@router.post("/reset-password")
@limiter.limit("5/hour")
async def reset_password(
    body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="User not found.")

    user.password_hash = hash_password(body.new_password)  # type: ignore[assignment]
    user.reset_password_otp = None  # type: ignore[assignment]
    user.reset_password_token = None  # type: ignore[assignment]
    user.reset_password_expires_at = None  # type: ignore[assignment]
    await db.commit()
    return {"message": "Password reset successfully."}


@router.post("/admin/register", response_model=UserRead, status_code=201)
@limiter.limit("5/minute")
async def register_admin(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    user = await create_admin(body, db)
    return user


@router.post("/google", response_model=GoogleAuthResponse)
@limiter.limit("20/minute")
async def google_auth(
    body: GoogleAuthRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await google_login_or_register(body.token, db, mode=body.mode)
    return GoogleAuthResponse(**result)
