import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.models import User, Role
from app.auth.security import hash_password
from app.auth.schemas import RegisterRequest

logger = logging.getLogger(__name__)


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
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"[REGISTER] Admin account created — email={body.email}")
    return user