import uuid
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from app.auth.models import User
from app.auth.security import hash_password


# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_users_data(test_session_factory, seed_users):
    """
    Seed extra users specifically for users-endpoint tests.
    Depends on seed_users so Roles(id=1, id=2) are guaranteed to exist.
    Uses distinct emails to avoid collisions with conftest and test_auth users.
    """
    target_passenger = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Target",
        last_name="Passenger",
        email="target.passenger@test.com",
        password_hash=hash_password("Password1!"),
        is_active=True,
        is_verified=True,
    )
    another_passenger = User(
        id=uuid.uuid4(),
        role_id=2,
        first_name="Another",
        last_name="Passenger",
        email="another.passenger@test.com",
        password_hash=hash_password("Password1!"),
        is_active=True,
        is_verified=True,
    )

    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([target_passenger, another_passenger])

    yield {
        "target": target_passenger,
        "another": another_passenger,
    }

    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(User).where(
                    User.email.in_([
                        "target.passenger@test.com",
                        "another.passenger@test.com",
                    ])
                )
            )


# ══════════════════════════════════════════════════════════════════════════════
# GET /users/me
# ══════════════════════════════════════════════════════════════════════════════

class TestGetMe:
    async def test_passenger_can_get_own_profile(
        self, passenger_client: AsyncClient, seed_users
    ):
        resp = await passenger_client.get("/api/v1/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "passenger@test.com"
        assert data["role_id"] == 2
        assert "id" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "is_active" in data
        assert "created_at" in data

    async def test_admin_can_get_own_profile(
        self, admin_client: AsyncClient, seed_users
    ):
        resp = await admin_client.get("/api/v1/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@test.com"
        assert data["role_id"] == 1

    async def test_unauthenticated_cannot_get_me(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/users/me")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# PUT /users/me
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateMe:
    async def test_passenger_can_update_own_profile(
        self, passenger_client: AsyncClient, seed_users
    ):
        resp = await passenger_client.put("/api/v1/users/me", json={
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "UpdatedFirst"
        assert data["last_name"] == "UpdatedLast"

    async def test_can_update_phone_number(
        self, passenger_client: AsyncClient, seed_users
    ):
        resp = await passenger_client.put("/api/v1/users/me", json={
            "phone_number": "09171234567",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone_number"] == "09171234567"

    async def test_partial_update_only_changes_provided_fields(
        self, passenger_client: AsyncClient, seed_users
    ):
        # First, set a known state
        await passenger_client.put("/api/v1/users/me", json={
            "first_name": "BeforeUpdate",
            "last_name": "Stable",
        })
        # Update only first_name
        resp = await passenger_client.put("/api/v1/users/me", json={
            "first_name": "AfterUpdate",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "AfterUpdate"
        assert data["last_name"] == "Stable"

    async def test_empty_body_returns_200_unchanged(
        self, passenger_client: AsyncClient, seed_users
    ):
        # Empty body with all-optional fields should be accepted
        resp = await passenger_client.put("/api/v1/users/me", json={})
        assert resp.status_code == 200

    async def test_unauthenticated_cannot_update_me(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.put("/api/v1/users/me", json={
            "first_name": "Hacker",
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# GET /users  (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestGetAllUsers:
    async def test_admin_can_list_users(
        self, admin_client: AsyncClient, seed_users
    ):
        resp = await admin_client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 2  # at least admin + passenger from seed_users

    async def test_pagination_defaults(
        self, admin_client: AsyncClient, seed_users
    ):
        resp = await admin_client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 10

    async def test_pagination_custom_page_and_size(
        self, admin_client: AsyncClient, seed_users
    ):
        resp = await admin_client.get("/api/v1/users?page=1&size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) <= 2

    async def test_pagination_invalid_page_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.get("/api/v1/users?page=0")
        assert resp.status_code == 422

    async def test_pagination_size_exceeds_max_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.get("/api/v1/users?size=101")
        assert resp.status_code == 422

    async def test_passenger_cannot_list_users(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.get("/api/v1/users")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_list_users(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/users")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# GET /users/{user_id}  (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestGetUser:
    async def test_admin_can_get_user_by_id(
        self, admin_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await admin_client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "target.passenger@test.com"
        assert str(data["id"]) == str(user_id)

    async def test_admin_get_nonexistent_user_returns_404(
        self, admin_client: AsyncClient
    ):
        fake_id = uuid.uuid4()
        resp = await admin_client.get(f"/api/v1/users/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found."

    async def test_admin_get_user_invalid_uuid_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.get("/api/v1/users/not-a-uuid")
        assert resp.status_code == 422

    async def test_passenger_cannot_get_user_by_id(
        self, passenger_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await passenger_client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_get_user_by_id(
        self, unauthenticated_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await unauthenticated_client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# PUT /users/{user_id}/status  (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateUserStatus:
    async def test_admin_can_deactivate_user(
        self, admin_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["another"].id
        resp = await admin_client.put(f"/api/v1/users/{user_id}/status", json={
            "is_active": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False

    async def test_admin_can_reactivate_user(
        self, admin_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["another"].id
        resp = await admin_client.put(f"/api/v1/users/{user_id}/status", json={
            "is_active": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is True

    async def test_admin_update_status_nonexistent_user_returns_404(
        self, admin_client: AsyncClient
    ):
        fake_id = uuid.uuid4()
        resp = await admin_client.put(f"/api/v1/users/{fake_id}/status", json={
            "is_active": False,
        })
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found."

    async def test_update_status_missing_body_returns_422(
        self, admin_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await admin_client.put(f"/api/v1/users/{user_id}/status", json={})
        assert resp.status_code == 422

    async def test_passenger_cannot_update_user_status(
        self, passenger_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await passenger_client.put(f"/api/v1/users/{user_id}/status", json={
            "is_active": False,
        })
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_update_user_status(
        self, unauthenticated_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await unauthenticated_client.put(f"/api/v1/users/{user_id}/status", json={
            "is_active": False,
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /users/{user_id}  (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestDeleteUser:
    async def test_passenger_cannot_delete_user(
        self, passenger_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await passenger_client.delete(f"/api/v1/users/{user_id}")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_delete_user(
        self, unauthenticated_client: AsyncClient, seed_users_data
    ):
        user_id = seed_users_data["target"].id
        resp = await unauthenticated_client.delete(f"/api/v1/users/{user_id}")
        assert resp.status_code == 401

    async def test_admin_delete_nonexistent_user_returns_404(
        self, admin_client: AsyncClient
    ):
        fake_id = uuid.uuid4()
        resp = await admin_client.delete(f"/api/v1/users/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found."

    async def test_admin_delete_invalid_uuid_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.delete("/api/v1/users/not-a-uuid")
        assert resp.status_code == 422

    async def test_admin_can_delete_user(
        self, admin_client: AsyncClient, test_session_factory, seed_users
    ):
        # Create a throwaway user just for deletion
        throwaway = User(
            id=uuid.uuid4(),
            role_id=2,
            first_name="Delete",
            last_name="Me",
            email="deleteme@test.com",
            password_hash=hash_password("Password1!"),
            is_active=True,
            is_verified=True,
        )
        async with test_session_factory() as session:
            async with session.begin():
                session.add(throwaway)

        resp = await admin_client.delete(f"/api/v1/users/{throwaway.id}")
        assert resp.status_code == 204

        # Confirm it's gone
        confirm = await admin_client.get(f"/api/v1/users/{throwaway.id}")
        assert confirm.status_code == 404