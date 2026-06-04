import uuid
import logging
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from app.auth.models import User, Role
from app.auth.security import create_access_token
import os

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


async def google_login_or_register(token: str, db: AsyncSession) -> dict:
    # 1. Verify the token with Google
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            logger.warning(f"[GOOGLE AUTH] Failed to fetch user info: {response.status_code}")
            raise HTTPException(status_code=401, detail="Invalid Google token.")
        id_info = response.json()

    google_id = id_info.get("sub")
    email = id_info.get("email")
    first_name = id_info.get("given_name", "")
    last_name = id_info.get("family_name", "")
    email_verified = id_info.get("email_verified", False)

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Google token missing required fields.")

    if not email_verified or email_verified == "false":
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
        # No account found — tell frontend to redirect to register
        logger.info(f"[GOOGLE AUTH] No account found for email={email}")
        raise HTTPException(
            status_code=404,
            detail="no_account"
        )

    # 4. Issue JWT — same structure as regular login
    return {
        "access_token": create_access_token({"sub": str(user.id), "role_id": user.role_id}),
        "token_type": "bearer"
    }