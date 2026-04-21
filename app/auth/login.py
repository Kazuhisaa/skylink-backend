import logging
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.auth.models import User, LoginAttempt
from app.auth.security import verify_password
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
WINDOW_MINUTES = 15


async def purge_old_attempts(db: AsyncSession):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
    await db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < cutoff))
    await db.commit()


async def count_recent_attempts(email: str, ip: str | None, db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
    query = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.attempted_at >= cutoff)
    )
    if ip:
        query = query.where(
            (LoginAttempt.email == email) | (LoginAttempt.ip_address == ip)
        )
    else:
        query = query.where(LoginAttempt.email == email)
    result = await db.execute(query)
    return result.scalar() or 0


async def record_failed_attempt(email: str, ip: str | None, db: AsyncSession):
    attempt = LoginAttempt(email=email, ip_address=ip)
    db.add(attempt)
    await db.commit()


async def clear_attempts(email: str, ip: str | None, db: AsyncSession):
    if ip:
        query = delete(LoginAttempt).where(
            (LoginAttempt.email == email) | (LoginAttempt.ip_address == ip)
        )
    else:
        query = delete(LoginAttempt).where(LoginAttempt.email == email)
    await db.execute(query)
    await db.commit()


async def verify_user(email: str, password: str, ip: str | None, db: AsyncSession) -> dict:
    await purge_old_attempts(db)


#    recent = await count_recent_attempts(email, ip, db)
#    if recent >= MAX_ATTEMPTS:
#        logger.warning(f"[AUTH] Brute force blocked — email={email} ip={ip}")
#        raise HTTPException(
#            status_code=429,
#            detail=f"Too many failed login attempts. Please wait {LOCKOUT_MINUTES} minutes.",
#        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"[AUTH] Login failed — email not found: {email} ip={ip}")
        # await record_failed_attempt(email, ip, db)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(password, user.password_hash):       # type: ignore
        logger.warning(f"[AUTH] Login failed — wrong password: email={email} ip={ip}")
        # await record_failed_attempt(email, ip, db)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:          # type: ignore
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    if not user.is_verified:        # type: ignore
        raise HTTPException(status_code=403, detail="Please verify your email address.")

    # await clear_attempts(email, ip, db)
    logger.info(f"[AUTH] Login success — user_id={user.id} email={email} ip={ip}")
    return {"id": str(user.id), "email": user.email, "role_id": user.role_id}