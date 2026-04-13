import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.security import decode_access_token
from app.auth.models import User
from app.database import get_db
from dotenv import load_dotenv

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.is_active:  # type: ignore
        raise HTTPException(status_code=403, detail="Account is deactivated.")
    return user


def get_user_id_and_role(current_user: User = Depends(get_current_user)):
    return {"user_id": str(current_user.id), "role_id": current_user.role_id}


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role_id != 1:  # type: ignore
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def require_passenger(current_user: User = Depends(get_current_user)):
    if current_user.role_id != 2:  # type: ignore
        raise HTTPException(status_code=403, detail="Passenger access required.")
    return current_user