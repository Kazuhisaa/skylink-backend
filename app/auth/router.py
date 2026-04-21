from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.login import verify_user
from app.auth.register import create_passenger
from app.auth.security import create_access_token
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.database import get_db
from app.auth.dependencies import require_admin
from app.auth.admin_register import create_admin
from app.auth.models import User
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    user = await verify_user(body.email, body.password, ip, db)
    token = create_access_token({"sub": user["id"], "role_id": user["role_id"]})
    return TokenResponse(access_token=token)

@router.post("/register", response_model=UserRead, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await create_passenger(body, db)
    return user

@router.get("/verify-email")
async def verify_email(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token.")
    
    if user.is_verified:
        return {"message": "Email already verified."}
    
    if user.verification_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification token has expired.")
    
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    
    await db.commit()
    return {"message": "Email verified successfully."}

@router.post("/admin/register", response_model=UserRead, status_code=201)
async def register_admin(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    user = await create_admin(body, db)
    return user