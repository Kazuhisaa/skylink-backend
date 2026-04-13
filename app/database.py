import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

env_path = Path(__file__).resolve().parents[1] / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print(f"[config] No .env file found at {env_path} (using system environment)")


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,        # maintains up to 10 persistent connections
    max_overflow=0,      # no extra connections beyond pool_size
    pool_timeout=30,     # wait 30s before giving up on getting a connection
    pool_recycle=300,    # recycle connections every 5 mins (prevents stale)
    pool_pre_ping=True,  # quick SELECT 1 to verify it's still alive
    echo=False,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()