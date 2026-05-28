import logging
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.models import User, Role
from app.auth.security import hash_password
from app.auth.schemas import RegisterRequest
from app.services.email_service import send_verification_email

logger = logging.getLogger(__name__)


async def insert_user(data: dict, db: AsyncSession) -> User:
    verification_token = secrets.token_urlsafe(32)
    verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    user = User(
        id=uuid.uuid4(),
        role_id=data["role_id"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        password_hash=hash_password(data["password"]),
        phone_number=data.get("phone_number"),
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=verification_token_expires_at,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Send verification email in the background or just await it for now
    await send_verification_email(str(user.email), verification_token)
    
    return user


async def create_passenger(body: RegisterRequest, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered.")

    result = await db.execute(select(Role).where(Role.name == "passenger"))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=500, detail="Default role 'passenger' not found.")

    logger.info(f"[REGISTER] Creating user — email={body.email}")
    return await insert_user(
        {
            "role_id": role.id,
            "first_name": body.first_name,
            "last_name": body.last_name,
            "email": body.email,
            "password": body.password,
            "phone_number": body.phone_number,
        },
        db,
    )