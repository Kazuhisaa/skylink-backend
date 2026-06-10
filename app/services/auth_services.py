import logging
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.auth import User, Role, LoginAttempt
from app.core.security import hash_password, verify_password
from app.schemas.auth import RegisterRequest
from app.services.email_service import send_verification_email

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
WINDOW_MINUTES = 15


# ─── Login ─────────────────────────────────────────────────────────────────────
async def purge_old_attempts(db: AsyncSession):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
    await db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < cutoff))
    await db.commit()


async def record_attempt(email: str, ip: str | None, db: AsyncSession):
    attempt = LoginAttempt(email=email, ip_address=ip)
    db.add(attempt)
    await db.commit()


async def verify_user(email: str, password: str, ip: str | None, db: AsyncSession) -> dict:
    await purge_old_attempts(db)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"[AUTH] Login failed — email not found: {email} ip={ip}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(password, user.password_hash):  # type: ignore
        logger.warning(f"[AUTH] Login failed — wrong password: email={email} ip={ip}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:  # type: ignore
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    if not user.is_verified:  # type: ignore
        raise HTTPException(status_code=403, detail="Please verify your email address.")

    await record_attempt(email, ip, db)

    role = "admin" if user.role_id == 1 else "passenger"
    logger.info(f"[AUTH], [role = {role}] Login success — user_id={user.id} email={email} ip={ip}")
    return {"id": str(user.id), "email": user.email, "role_id": user.role_id}


# ─── Register ──────────────────────────────────────────────────────────────────
async def _insert_user(data: dict, db: AsyncSession) -> User:
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

    logger.info(f"[REGISTER] Creating passenger — email={body.email}")
    return await _insert_user(
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


# ─── Admin Register ────────────────────────────────────────────────────────────
async def create_admin(body: RegisterRequest, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered.")

    result = await db.execute(select(Role).where(Role.name == "admin"))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=500, detail="Admin role not found.")

    user = User(
        id=uuid.uuid4(),
        role_id=role.id,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        password_hash=hash_password(body.password),
        phone_number=body.phone_number,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"[REGISTER] Admin account created — email={body.email}")
    return user