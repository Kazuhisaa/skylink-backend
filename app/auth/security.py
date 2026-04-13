import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"{key} is not set in environment")
    return val


JWT_SECRET_KEY: str = _require("JWT_SECRET_KEY")
JWT_ALGORITHM: str = _require("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_require("ACCESS_TOKEN_EXPIRE_MINUTES"))
BCRYPT_ROUNDS: int = int(_require("BCRYPT_ROUNDS"))

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=BCRYPT_ROUNDS, deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return {}