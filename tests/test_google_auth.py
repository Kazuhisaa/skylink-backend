import uuid
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
from sqlalchemy import delete, select
from app.auth.models import User

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def mock_google_userinfo(
    google_id: str = "google-id-123",
    email: str = "googleuser@test.com",
    first_name: str = "Google",
    last_name: str = "User",
    email_verified: bool = True,
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sub": google_id,
        "email": email,
        "given_name": first_name,
        "family_name": last_name,
        "email_verified": email_verified,
    }

    async def mock_get(*args, **kwargs):
        return mock_response

    mock_client = MagicMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return patch("app.auth.google_service.httpx.AsyncClient", return_value=mock_client)


def mock_google_userinfo_failure():
    mock_response = MagicMock()
    mock_response.status_code = 401

    async def mock_get(*args, **kwargs):
        return mock_response

    mock_client = MagicMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return patch("app.auth.google_service.httpx.AsyncClient", return_value=mock_client)


# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_google_users(test_session_factory, seed_users):
    """
    Seed a user that already has a google_id (existing Google user)
    and a user registered via email only (for linking test).
    Depends on seed_users so Roles exist.
    """
    existing_google_user = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Existing",
        last_name="Google",
        email="existing.google@test.com",
        password_hash=None,
        google_id="existing-google-id-999",
        is_active=True,
        is_verified=True,
    )
    email_only_user = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Email",
        last_name="Only",
        email="emailonly.google@test.com",
        password_hash="hashed",
        google_id=None,
        is_active=True,
        is_verified=True,
    )
    inactive_google_user = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Inactive",
        last_name="Google",
        email="inactive.google@test.com",
        password_hash=None,
        google_id="inactive-google-id-000",
        is_active=False,
        is_verified=True,
    )
    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([
                existing_google_user,
                email_only_user,
                inactive_google_user,
            ])
    yield {
        "existing": existing_google_user,
        "email_only": email_only_user,
        "inactive": inactive_google_user,
    }
    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(User).where(
                    User.email.in_([
                        "existing.google@test.com",
                        "emailonly.google@test.com",
                        "inactive.google@test.com",
                        "newgoogle@test.com",
                        "newregister@test.com", 
                    ])
                )
            )


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/google
# ══════════════════════════════════════════════════════════════════════════════

class TestGoogleAuth:

    async def test_new_user_gets_404_no_account(
        self, unauthenticated_client: AsyncClient, seed_google_users
    ):
        """New Google user with no existing account gets 404 with no_account detail."""
        with mock_google_userinfo(
            google_id="brand-new-google-id",
            email="newgoogle@test.com",
        ):
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "fake-token", "mode": "login"} 
            )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "no_account"

    async def test_new_user_register_mode_creates_account(
        self, unauthenticated_client: AsyncClient, seed_google_users, test_session_factory
    ):
        """New Google user on register page gets account created and JWT returned."""
        with mock_google_userinfo(
            google_id="brand-new-register-id",
            email="newregister@test.com",
        ):
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "fake-token", "mode": "register"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        async with test_session_factory() as session:
            result = await session.execute(
                select(User).where(User.email == "newregister@test.com")
            )
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.google_id == "brand-new-register-id"
            assert user.is_verified is True
            assert user.role_id == 2

    async def test_existing_user_register_mode_still_logs_in(
        self, unauthenticated_client: AsyncClient, seed_google_users
    ):
        """Existing user clicking Google on register page just logs them in."""
        with mock_google_userinfo(
            google_id="existing-google-id-999",
            email="existing.google@test.com",
        ):
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "fake-token", "mode": "register"}
            )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_existing_google_user_can_login(
        self, unauthenticated_client: AsyncClient, seed_google_users
    ):
        """User with existing google_id gets JWT back."""
        with mock_google_userinfo(
            google_id="existing-google-id-999",
            email="existing.google@test.com",
        ):
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "fake-token", "mode": "login"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_email_only_user_gets_google_id_linked(
        self, unauthenticated_client: AsyncClient, seed_google_users, test_session_factory
    ):
        """User registered via email gets google_id linked and can login."""
        with mock_google_userinfo(
            google_id="new-linked-google-id",
            email="emailonly.google@test.com",
        ):
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "fake-token", "mode": "login"}
            )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

        async with test_session_factory() as session:
            result = await session.execute(
                select(User).where(User.email == "emailonly.google@test.com")
            )
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.google_id == "new-linked-google-id"

    async def test_inactive_google_user_gets_403(
        self, unauthenticated_client: AsyncClient, seed_google_users
    ):
        """Inactive Google user cannot login."""
        with mock_google_userinfo(
            google_id="inactive-google-id-000",
            email="inactive.google@test.com",
        ):
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "fake-token", "mode": "login"}
            )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account is deactivated."

    async def test_invalid_google_token_returns_401(
        self, unauthenticated_client: AsyncClient, seed_google_users
    ):
        """Invalid/expired Google token returns 401."""
        with mock_google_userinfo_failure():
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "invalid-token"}
            )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid Google token."

    async def test_missing_token_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        """Missing token field returns 422."""
        resp = await unauthenticated_client.post(
            "/api/v1/auth/google", json={}
        )
        assert resp.status_code == 422

    async def test_unverified_google_email_returns_400(
        self, unauthenticated_client: AsyncClient, seed_google_users
    ):
        """Google account with unverified email is rejected."""
        with mock_google_userinfo(
            google_id="unverified-google-id",
            email="unverified.google@test.com",
            email_verified=False,
        ):
            resp = await unauthenticated_client.post(
                "/api/v1/auth/google", json={"token": "fake-token"}
            )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Google email is not verified."