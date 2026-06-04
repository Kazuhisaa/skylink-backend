import uuid
import logging
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.auth.models import User, Role
from app.auth.security import create_access_token
import os

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


async def google_login_or_register(token: str, db: AsyncSession) -> dict:
    # 1. Verify the token with Google
    try:
        id_info = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        logger.warning(f"[GOOGLE AUTH] Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google token.")

    google_id = id_info.get("sub")
    email = id_info.get("email")
    first_name = id_info.get("given_name", "")
    last_name = id_info.get("family_name", "")
    email_verified = id_info.get("email_verified", False)

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Google token missing required fields.")

    if not email_verified:
        raise HTTPException(status_code=400, detail="Google email is not verified.")

    # 2. Check by google_id first, then fall back to email
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        # 3a. Existing user — link google_id if not yet linked (email-registered user signing in with Google)
        if not user.google_id:          # type: ignore
            user.google_id = google_id  # type: ignore
            await db.commit()
            await db.refresh(user)

        if not user.is_active:          # type: ignore
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        logger.info(f"[GOOGLE AUTH] Login — user_id={user.id} email={email}")

    else:
        # 3b. New user — auto-register as passenger
        result = await db.execute(select(Role).where(Role.name == "passenger"))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=500, detail="Default role 'passenger' not found.")

        user = User(
            id=uuid.uuid4(),
            role_id=role.id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=None,
            google_id=google_id,
            is_active=True,
            is_verified=True,
            verification_token=None,
            verification_token_expires_at=None,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"[GOOGLE AUTH] Registered — user_id={user.id} email={email}")

    # 4. Issue JWT — same structure as regular login
    return {
        "access_token": create_access_token({"sub": str(user.id), "role_id": user.role_id}),
        "token_type": "bearer"
    }