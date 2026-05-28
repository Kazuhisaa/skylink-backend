import os
os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver,test"

from app.core.limiter import limiter
limiter.enabled = False

import uuid
import pytest_asyncio
from dotenv import load_dotenv
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import delete

from app.main import app
from app.database import Base, get_db          # get_db lives here
from app.auth.dependencies import (
    get_current_user,
    require_admin,
    require_passenger,
)
from app.auth.models import User, Role

# ── Load test DB URL ──────────────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
assert TEST_DATABASE_URL, "TEST_DATABASE_URL is not set in .env"


# ── Engine ────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,      #type: ignore
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Session factory ───────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# ── Per-test DB session with rollback ─────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="session")
async def db_session(test_session_factory):
    async with test_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ── Seed roles + users once per session ──────────────────────────────────────
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_users(test_session_factory):
    admin_user = User(
        id=uuid.uuid4(),
        role_id=1,
        first_name="Admin",
        last_name="User",
        email="admin@test.com",
        password_hash="hashed",
        is_active=True,
        is_verified=True,
    )
    passenger_user = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Passenger",
        last_name="User",
        email="passenger@test.com",
        password_hash="hashed",
        is_active=True,
        is_verified=True,
    )

    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([Role(id=1, name="admin"), Role(id=2, name="passenger")])
            await session.flush()
            session.add_all([admin_user, passenger_user])

    yield {
        "admin": admin_user,
        "passenger": passenger_user,
    }

    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(delete(User).where(User.email.in_(["admin@test.com", "passenger@test.com"])))
            await session.execute(delete(Role).where(Role.id.in_([1, 2])))


# ── Auth override helpers ─────────────────────────────────────────────────────
# get_current_user is async — override must be async
def make_current_user_override(user: User):
    async def override():
        return user
    return override

# require_admin/require_passenger are sync — override must be sync
def make_admin_override(user: User):
    def override():
        return user
    return override

def make_passenger_override(user: User):
    def override():
        return user
    return override


# ── get_db override — must be async generator like the original ───────────────
def make_get_db_override(session_factory):
    async def override():
        async with session_factory() as session:
            yield session
    return override


# ── Admin client ──────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="session")
async def admin_client(seed_users, test_session_factory):
    admin = seed_users["admin"]
    app.dependency_overrides[get_current_user] = make_current_user_override(admin)
    app.dependency_overrides[require_admin] = make_admin_override(admin)
    app.dependency_overrides[get_db] = make_get_db_override(test_session_factory)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ── Passenger client ──────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="session")
async def passenger_client(seed_users, test_session_factory):
    passenger = seed_users["passenger"]
    app.dependency_overrides[get_current_user] = make_current_user_override(passenger)
    app.dependency_overrides[require_passenger] = make_passenger_override(passenger)
    app.dependency_overrides[get_db] = make_get_db_override(test_session_factory)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ── Unauthenticated client ────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="session")
async def unauthenticated_client(test_session_factory):
    app.dependency_overrides[get_db] = make_get_db_override(test_session_factory)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        yield client
    app.dependency_overrides.clear()