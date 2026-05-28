import uuid
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import delete
from app.auth.models import User, LoginAttempt
from app.auth.security import hash_password

# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_auth_users(test_session_factory, seed_users):
    """
    Seed verified passenger, unverified passenger, inactive passenger, admin
    specifically for auth tests.

    Depends on seed_users so that Roles(id=1, id=2) are guaranteed to exist
    before we insert users, and so we never double-insert roles.

    We use distinct emails from conftest's seed_users to avoid collisions.
    """
    verified_passenger = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Verified",
        last_name="Passenger",
        email="verified@test.com",
        password_hash=hash_password("Password1!"),
        is_active=True,
        is_verified=True,
    )
    unverified_passenger = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Unverified",
        last_name="Passenger",
        email="unverified@test.com",
        password_hash=hash_password("Password1!"),
        is_active=True,
        is_verified=False,
    )
    inactive_passenger = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Inactive",
        last_name="Passenger",
        email="inactive@test.com",
        password_hash=hash_password("Password1!"),
        is_active=False,
        is_verified=True,
    )
    auth_admin_user = User(
        id=uuid.uuid4(),
        role_id=1,
        first_name="AuthAdmin",
        last_name="User",
        email="authadmin@test.com",        # ← changed from admin@test.com
        password_hash=hash_password("Password1!"),
        is_active=True,
        is_verified=True,
    )
    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([
                verified_passenger,
                unverified_passenger,
                inactive_passenger,
                auth_admin_user,
            ])

    yield {
        "verified": verified_passenger,
        "unverified": unverified_passenger,
        "inactive": inactive_passenger,
        "admin": auth_admin_user,
    }

    # Teardown: only delete our own users + login attempts.
    # Roles are owned by seed_users (conftest) — do NOT delete them here.
    async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(LoginAttempt))
                await session.execute(
                    delete(User).where(
                        User.email.in_([
                            "verified@test.com",
                            "unverified@test.com",
                            "inactive@test.com",
                            "authadmin@test.com",
                            # users created via API during tests, never individually cleaned up
                            "newpassenger@test.com",
                            "validphone@test.com",
                            "fakeadmin2@test.com",
                        ])
                    )
                )


def mock_email():
    """Patch email service so no real emails are sent during tests."""
    return patch(
        "app.auth.register.send_verification_email",
        new_callable=AsyncMock,
    )


def mock_reset_email():
    return patch(
        "app.auth.router.send_password_reset_email",
        new_callable=AsyncMock,
    )


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/register
# ══════════════════════════════════════════════════════════════════════════════

class TestRegister:
    async def test_passenger_can_register(
        self, unauthenticated_client: AsyncClient, seed_users
    ):
        with mock_email():
            resp = await unauthenticated_client.post("/api/v1/auth/register", json={
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "email": "newpassenger@test.com",
                "password": "Password1!",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newpassenger@test.com"
        assert data["role_id"] == 2
        assert "id" in data

    async def test_register_duplicate_email_returns_409(
        self, unauthenticated_client: AsyncClient, seed_auth_users
    ):
        with mock_email():
            resp = await unauthenticated_client.post("/api/v1/auth/register", json={
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "email": "verified@test.com",  # already exists
                "password": "Password1!",
            })
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Email already registered."

    async def test_register_missing_required_fields_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422

    async def test_register_invalid_email_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        with mock_email():
            resp = await unauthenticated_client.post("/api/v1/auth/register", json={
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "email": "not-an-email",
                "password": "Password1!",
            })
        assert resp.status_code == 422

    async def test_register_password_too_short_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        with mock_email():
            resp = await unauthenticated_client.post("/api/v1/auth/register", json={
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "email": "shortpass@test.com",
                "password": "short",
            })
        assert resp.status_code == 422

    async def test_register_invalid_phone_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        with mock_email():
            resp = await unauthenticated_client.post("/api/v1/auth/register", json={
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "email": "phone@test.com",
                "password": "Password1!",
                "phone_number": "12345",  # invalid PH format
            })
        assert resp.status_code == 422

    async def test_register_valid_ph_phone_accepted(
        self, unauthenticated_client: AsyncClient
    ):
        with mock_email():
            resp = await unauthenticated_client.post("/api/v1/auth/register", json={
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "email": "validphone@test.com",
                "password": "Password1!",
                "phone_number": "09171234567",
            })
        assert resp.status_code == 201


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/login
# ══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    async def test_verified_user_can_login(
        self, unauthenticated_client: AsyncClient, seed_auth_users
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "verified@test.com",
            "password": "Password1!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_wrong_password_returns_401(
        self, unauthenticated_client: AsyncClient, seed_auth_users
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "verified@test.com",
            "password": "WrongPassword1!",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password."

    async def test_nonexistent_email_returns_401(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "ghost@test.com",
            "password": "Password1!",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password."

    async def test_unverified_user_cannot_login(
        self, unauthenticated_client: AsyncClient, seed_auth_users
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "unverified@test.com",
            "password": "Password1!",
        })
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Please verify your email address."

    async def test_inactive_user_cannot_login(
        self, unauthenticated_client: AsyncClient, seed_auth_users
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "inactive@test.com",
            "password": "Password1!",
        })
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account is deactivated."

    async def test_login_missing_fields_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    async def test_login_invalid_email_format_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "notanemail",
            "password": "Password1!",
        })
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /auth/me
# ══════════════════════════════════════════════════════════════════════════════

class TestMe:
    async def test_authenticated_user_can_get_me(
        self, unauthenticated_client: AsyncClient, seed_auth_users
    ):
        login_resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "verified@test.com",
            "password": "Password1!",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        resp = await unauthenticated_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "verified@test.com"
        assert data["role_id"] == 2

    async def test_unauthenticated_cannot_get_me(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/auth/me")
        assert resp.status_code == 401  # HTTPBearer raises 401 when no token provided

    async def test_invalid_token_returns_401(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# GET /auth/verify-email
# ══════════════════════════════════════════════════════════════════════════════

class TestVerifyEmail:
    async def test_valid_token_verifies_email(
        self, unauthenticated_client: AsyncClient, test_session_factory
    ):
        import secrets
        from datetime import datetime, timedelta, timezone
        token = secrets.token_urlsafe(32)
        user_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(User(
                    id=user_id,
                    role_id=2,
                    first_name="Token",
                    last_name="User",
                    email="tokenuser@test.com",
                    password_hash=hash_password("Password1!"),
                    is_active=True,
                    is_verified=False,
                    verification_token=token,
                    verification_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                ))
        resp = await unauthenticated_client.get(f"/api/v1/auth/verify-email?token={token}")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email verified successfully."
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(User).where(User.id == user_id))

    async def test_invalid_token_returns_400(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get(
            "/api/v1/auth/verify-email?token=totallyinvalidtoken"
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid verification token."

    async def test_expired_token_returns_400(
        self, unauthenticated_client: AsyncClient, test_session_factory
    ):
        import secrets
        from datetime import datetime, timedelta, timezone
        token = secrets.token_urlsafe(32)
        user_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(User(
                    id=user_id,
                    role_id=2,
                    first_name="Expired",
                    last_name="Token",
                    email="expiredtoken@test.com",
                    password_hash=hash_password("Password1!"),
                    is_active=True,
                    is_verified=False,
                    verification_token=token,
                    verification_token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                ))
        resp = await unauthenticated_client.get(f"/api/v1/auth/verify-email?token={token}")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Verification token has expired."
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(User).where(User.id == user_id))

    async def test_already_verified_returns_message(
        self, unauthenticated_client: AsyncClient, seed_auth_users, test_session_factory
    ):
        import secrets
        from datetime import datetime, timedelta, timezone
        token = secrets.token_urlsafe(32)
        user_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(User(
                    id=user_id,
                    role_id=2,
                    first_name="Already",
                    last_name="Verified",
                    email="alreadyverified@test.com",
                    password_hash=hash_password("Password1!"),
                    is_active=True,
                    is_verified=True,
                    verification_token=token,
                    verification_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                ))
        resp = await unauthenticated_client.get(f"/api/v1/auth/verify-email?token={token}")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email already verified."
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(User).where(User.id == user_id))


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/forgot-password
# ══════════════════════════════════════════════════════════════════════════════

class TestForgotPassword:
    async def test_registered_email_returns_generic_message(
        self, unauthenticated_client: AsyncClient, seed_auth_users
    ):
        with mock_reset_email():
            resp = await unauthenticated_client.post("/api/v1/auth/forgot-password", json={
                "email": "verified@test.com",
            })
        assert resp.status_code == 200
        assert "password reset link" in resp.json()["message"].lower()

    async def test_unregistered_email_returns_same_generic_message(
        self, unauthenticated_client: AsyncClient
    ):
        with mock_reset_email():
            resp = await unauthenticated_client.post("/api/v1/auth/forgot-password", json={
                "email": "ghost@test.com",
            })
        assert resp.status_code == 200
        assert "password reset link" in resp.json()["message"].lower()

    async def test_invalid_email_format_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/forgot-password", json={
            "email": "notanemail",
        })
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/reset-password
# ══════════════════════════════════════════════════════════════════════════════

class TestResetPassword:
    async def test_valid_token_resets_password(
        self, unauthenticated_client: AsyncClient, test_session_factory
    ):
        import secrets
        from datetime import datetime, timedelta, timezone
        token = secrets.token_urlsafe(32)
        user_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(User(
                    id=user_id,
                    role_id=2,
                    first_name="Reset",
                    last_name="User",
                    email="resetuser@test.com",
                    password_hash=hash_password("OldPassword1!"),
                    is_active=True,
                    is_verified=True,
                    reset_password_token=token,
                    reset_password_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                ))
        resp = await unauthenticated_client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "NewPassword1!",
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password reset successfully."
        login_resp = await unauthenticated_client.post("/api/v1/auth/login", json={
            "email": "resetuser@test.com",
            "password": "NewPassword1!",
        })
        assert login_resp.status_code == 200
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(User).where(User.id == user_id))

    async def test_invalid_token_returns_400(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/reset-password", json={
            "token": "invalidtoken",
            "new_password": "NewPassword1!",
        })
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired reset token."

    async def test_expired_token_returns_400(
        self, unauthenticated_client: AsyncClient, test_session_factory
    ):
        import secrets
        from datetime import datetime, timedelta, timezone
        token = secrets.token_urlsafe(32)
        user_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(User(
                    id=user_id,
                    role_id=2,
                    first_name="Expired",
                    last_name="Reset",
                    email="expiredreset@test.com",
                    password_hash=hash_password("Password1!"),
                    is_active=True,
                    is_verified=True,
                    reset_password_token=token,
                    reset_password_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                ))
        resp = await unauthenticated_client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "NewPassword1!",
        })
        assert resp.status_code == 400
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(User).where(User.id == user_id))

    async def test_password_too_short_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/reset-password", json={
            "token": "sometoken",
            "new_password": "short",
        })
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/admin/register
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminRegister:
    async def test_admin_can_register_another_admin(
        self, admin_client: AsyncClient, test_session_factory
    ):
        resp = await admin_client.post("/api/v1/auth/admin/register", json={
            "first_name": "New",
            "last_name": "Admin",
            "email": "newadmin@test.com",
            "password": "Password1!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newadmin@test.com"
        assert data["role_id"] == 1
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(User).where(User.email == "newadmin@test.com"))

    async def test_passenger_cannot_register_admin(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.post("/api/v1/auth/admin/register", json={
            "first_name": "Fake",
            "last_name": "Admin",
            "email": "fakeadmin@test.com",
            "password": "Password1!",
        })
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_register_admin(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/auth/admin/register", json={
            "first_name": "Fake",
            "last_name": "Admin",
            "email": "fakeadmin2@test.com",
            "password": "Password1!",
        })
        assert resp.status_code in (401, 403)

    async def test_duplicate_admin_email_returns_409(
        self, admin_client: AsyncClient, seed_auth_users
    ):
        resp = await admin_client.post("/api/v1/auth/admin/register", json={
            "first_name": "Dupe",
            "last_name": "Admin",
            "email": "authadmin@test.com",  # matches seed_auth_users admin email
            "password": "Password1!",
        })
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Email already registered."