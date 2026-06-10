import uuid
import logging
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from app.models.auth import User, Role
from app.core.security import create_access_token

from app.core.settings import settings
logger = logging.getLogger(__name__)
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID

async def google_login_or_register(token: str, db: AsyncSession, mode: str = "login") -> dict:
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
        # Existing user — link google_id if not yet linked
        if not user.google_id:          # type: ignore
            user.google_id = google_id  # type: ignore
            await db.commit()
            await db.refresh(user)
        if not user.is_active:          # type: ignore
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        # If on register page but account already exists, just log them in
        logger.info(f"[GOOGLE AUTH] Login — user_id={user.id} email={email}")

    else:
        if mode == "login":
            # Login page: no account → tell frontend to redirect to register
            logger.info(f"[GOOGLE AUTH] No account found for email={email}")
            raise HTTPException(status_code=404, detail="no_account")

        # Register page: create the account
        logger.info(f"[GOOGLE AUTH] Registering new user via Google — email={email}")

        default_role = await db.execute(select(Role).where(Role.id == 2))
        role = default_role.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=500, detail="Default role not found.")
        
        user = User(
            id=uuid.uuid4(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            google_id=google_id,
            role_id=role.id,
            is_active=True,
            is_verified=True,
            # set a default role_id as needed, e.g. role_id=<your default role>
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 4. Issue JWT
    return {
        "access_token": create_access_token({"sub": str(user.id), "role_id": user.role_id}),
        "token_type": "bearer"
    }