from fastapi import APIRouter, Depends, Request, HTTPException, Query
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.login import verify_user
from app.auth.register import create_passenger
from app.auth.security import create_access_token, hash_password
from app.auth.schemas import (
    LoginRequest, 
    RegisterRequest, 
    TokenResponse, 
    UserRead, 
    ForgotPasswordRequest, 
    ResetPasswordRequest
)
from app.database import get_db
from app.auth.dependencies import require_admin, get_current_user
from app.auth.admin_register import create_admin
from app.auth.models import User
from app.services.email_service import send_password_reset_email
from app.core.limiter import limiter

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
async def verify_email(request: Request, token: str = Query(...), db: AsyncSession = Depends(get_db)):
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
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_password_token = token  # type: ignore[assignment]
        user.reset_password_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # type: ignore[assignment]
        await db.commit()
        await send_password_reset_email(user.email, token)      # type: ignore[arg-type]
    return {"message": "If your email is registered, you will receive a password reset link shortly."}

@router.post("/reset-password")
@limiter.limit("5/hour")
async def reset_password(body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.reset_password_token == body.token))
    user = result.scalar_one_or_none()
    if not user or user.reset_password_expires_at < datetime.now(timezone.utc):  # type: ignore[operator]
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    user.password_hash = hash_password(body.new_password)  # type: ignore[assignment]
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