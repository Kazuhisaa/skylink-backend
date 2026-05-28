import uuid
import pytest_asyncio
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.promotions import Promotion


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def valid_promotion_payload(**overrides) -> dict:
    base = {
        "title": "Cebu for Less",
        "sale_price": "1999.00",
        "original_price": "3999.00",
        "discount_text": "50% OFF",
        "badge_text": "HOT DEAL",
        "badge_type": "hot",
        "valid_until": str(date.today() + timedelta(days=30)),
        "image_url": "https://example.com/promo.jpg",
        "destination_city": "Cebu",
        "destination_code": "CEB",
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_promotions(test_session_factory, seed_users):
    """
    Two active + one expired promotion.
    No FK deps — promotions are standalone.
    """
    today = date.today()

    promo_active_a = Promotion(
        id=uuid.uuid4(),
        title="Manila to Cebu",
        sale_price="1500.00",
        original_price="3000.00",
        discount_text="50% OFF",
        badge_text="SALE",
        badge_type="sale",
        valid_until=today + timedelta(days=10),
        image_url="https://example.com/mnl-ceb.jpg",
        destination_city="Cebu",
        destination_code="CEB",
    )
    promo_active_b = Promotion(
        id=uuid.uuid4(),
        title="Manila to Davao",
        sale_price="2000.00",
        original_price="4000.00",
        discount_text="40% OFF",
        badge_text="NEW",
        badge_type="new",
        valid_until=today + timedelta(days=20),
        image_url="https://example.com/mnl-dvo.jpg",
        destination_city="Davao",
        destination_code="DVO",
    )
    promo_expired = Promotion(
        id=uuid.uuid4(),
        title="Expired Deal",
        sale_price="500.00",
        original_price="1000.00",
        valid_until=today - timedelta(days=1),   # yesterday — expired
        image_url="https://example.com/expired.jpg",
    )

    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([promo_active_a, promo_active_b, promo_expired])

    yield {
        "active_a": promo_active_a,
        "active_b": promo_active_b,
        "expired": promo_expired,
    }

    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(Promotion).where(
                    Promotion.id.in_([
                        promo_active_a.id,
                        promo_active_b.id,
                        promo_expired.id,
                    ])
                )
            )


# ══════════════════════════════════════════════════════════════════════════════
# GET /promotions
# ══════════════════════════════════════════════════════════════════════════════

class TestGetAllPromotions:
    async def test_anyone_can_list_promotions(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        resp = await unauthenticated_client.get("/api/v1/promotions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_contains_active_promotions(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        resp = await unauthenticated_client.get("/api/v1/promotions")
        ids = [item["id"] for item in resp.json()]
        assert str(seed_promotions["active_a"].id) in ids
        assert str(seed_promotions["active_b"].id) in ids

    async def test_list_excludes_expired_promotions(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        resp = await unauthenticated_client.get("/api/v1/promotions")
        ids = [item["id"] for item in resp.json()]
        assert str(seed_promotions["expired"].id) not in ids

    async def test_list_items_have_correct_fields(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        resp = await unauthenticated_client.get("/api/v1/promotions")
        item = resp.json()[0]
        for field in ("id", "title", "sale_price", "original_price", "valid_until", "image_url", "created_at"):
            assert field in item

    async def test_passenger_can_list_promotions(
        self, passenger_client: AsyncClient, seed_promotions
    ):
        resp = await passenger_client.get("/api/v1/promotions")
        assert resp.status_code == 200

    async def test_admin_can_list_promotions(
        self, admin_client: AsyncClient, seed_promotions
    ):
        resp = await admin_client.get("/api/v1/promotions")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# GET /promotions/{promotion_id}
# ══════════════════════════════════════════════════════════════════════════════

class TestGetPromotion:
    async def test_anyone_can_get_active_promotion_by_id(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        promo_id = seed_promotions["active_a"].id
        resp = await unauthenticated_client.get(f"/api/v1/promotions/{promo_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(promo_id)
        assert data["title"] == "Manila to Cebu"
        assert data["destination_code"] == "CEB"

    async def test_expired_promotion_still_retrievable_by_id(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        # GET by ID does not enforce expiry — only the list does
        promo_id = seed_promotions["expired"].id
        resp = await unauthenticated_client.get(f"/api/v1/promotions/{promo_id}")
        assert resp.status_code == 200

    async def test_get_promotion_returns_all_fields(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        promo_id = seed_promotions["active_b"].id
        resp = await unauthenticated_client.get(f"/api/v1/promotions/{promo_id}")
        data = resp.json()
        for field in (
            "id", "title", "sale_price", "original_price",
            "discount_text", "badge_text", "badge_type",
            "valid_until", "image_url", "destination_city",
            "destination_code", "created_at",
        ):
            assert field in data

    async def test_nonexistent_promotion_returns_404(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get(f"/api/v1/promotions/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Promotion not found."

    async def test_invalid_uuid_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/promotions/not-a-uuid")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# POST /promotions  (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestCreatePromotion:
    async def test_admin_can_create_promotion(
        self, admin_client: AsyncClient, test_session_factory
    ):
        payload = valid_promotion_payload(title="Admin Promo")
        resp = await admin_client.post("/api/v1/promotions", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Admin Promo"
        assert data["sale_price"] == "1999.00"
        assert data["original_price"] == "3999.00"
        assert data["destination_code"] == "CEB"
        assert "id" in data
        assert "created_at" in data

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(Promotion).where(Promotion.id == uuid.UUID(data["id"]))
                )

    async def test_create_promotion_optional_fields_can_be_omitted(
        self, admin_client: AsyncClient, test_session_factory
    ):
        payload = {
            "title": "Minimal Promo",
            "sale_price": "999.00",
            "original_price": "1999.00",
            "valid_until": str(date.today() + timedelta(days=5)),
            "image_url": "https://example.com/minimal.jpg",
        }
        resp = await admin_client.post("/api/v1/promotions", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["discount_text"] is None
        assert data["badge_text"] is None
        assert data["destination_city"] is None

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(Promotion).where(Promotion.id == uuid.UUID(data["id"]))
                )

    async def test_passenger_cannot_create_promotion(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.post("/api/v1/promotions", json=valid_promotion_payload())
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_create_promotion(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.post("/api/v1/promotions", json=valid_promotion_payload())
        assert resp.status_code == 401

    async def test_missing_required_fields_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.post("/api/v1/promotions", json={})
        assert resp.status_code == 422

    async def test_missing_title_returns_422(self, admin_client: AsyncClient):
        payload = valid_promotion_payload()
        payload.pop("title")
        resp = await admin_client.post("/api/v1/promotions", json=payload)
        assert resp.status_code == 422

    async def test_missing_image_url_returns_422(self, admin_client: AsyncClient):
        payload = valid_promotion_payload()
        payload.pop("image_url")
        resp = await admin_client.post("/api/v1/promotions", json=payload)
        assert resp.status_code == 422

    async def test_invalid_sale_price_returns_422(self, admin_client: AsyncClient):
        payload = valid_promotion_payload(sale_price="not-a-number")
        resp = await admin_client.post("/api/v1/promotions", json=payload)
        assert resp.status_code == 422

    async def test_invalid_date_format_returns_422(self, admin_client: AsyncClient):
        payload = valid_promotion_payload(valid_until="not-a-date")
        resp = await admin_client.post("/api/v1/promotions", json=payload)
        assert resp.status_code == 422

    async def test_created_promotion_appears_in_list(
        self, admin_client: AsyncClient, unauthenticated_client: AsyncClient, test_session_factory
    ):
        payload = valid_promotion_payload(title="Retrievable Promo")
        create_resp = await admin_client.post("/api/v1/promotions", json=payload)
        assert create_resp.status_code == 201
        promo_id = create_resp.json()["id"]

        get_resp = await unauthenticated_client.get(f"/api/v1/promotions/{promo_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Retrievable Promo"

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(Promotion).where(Promotion.id == uuid.UUID(promo_id))
                )


# ══════════════════════════════════════════════════════════════════════════════
# PUT /promotions/{promotion_id}  (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdatePromotion:
    async def test_admin_can_update_title(
        self, admin_client: AsyncClient, test_session_factory
    ):
        create_resp = await admin_client.post(
            "/api/v1/promotions", json=valid_promotion_payload(title="Before Update")
        )
        assert create_resp.status_code == 201
        promo_id = create_resp.json()["id"]

        resp = await admin_client.put(
            f"/api/v1/promotions/{promo_id}",
            json={"title": "After Update"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "After Update"

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(Promotion).where(Promotion.id == uuid.UUID(promo_id))
                )

    async def test_admin_can_update_valid_until(
        self, admin_client: AsyncClient, test_session_factory
    ):
        create_resp = await admin_client.post(
            "/api/v1/promotions", json=valid_promotion_payload()
        )
        promo_id = create_resp.json()["id"]
        new_date = str(date.today() + timedelta(days=60))

        resp = await admin_client.put(
            f"/api/v1/promotions/{promo_id}",
            json={"valid_until": new_date},
        )
        assert resp.status_code == 200
        assert resp.json()["valid_until"] == new_date

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(Promotion).where(Promotion.id == uuid.UUID(promo_id))
                )

    async def test_partial_update_only_changes_provided_fields(
        self, admin_client: AsyncClient, test_session_factory
    ):
        create_resp = await admin_client.post(
            "/api/v1/promotions",
            json=valid_promotion_payload(title="Stable Title", destination_code="MNL"),
        )
        promo_id = create_resp.json()["id"]

        resp = await admin_client.put(
            f"/api/v1/promotions/{promo_id}",
            json={"badge_text": "UPDATED"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Stable Title"
        assert data["destination_code"] == "MNL"
        assert data["badge_text"] == "UPDATED"

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(Promotion).where(Promotion.id == uuid.UUID(promo_id))
                )

    async def test_update_nonexistent_promotion_returns_404(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.put(
            f"/api/v1/promotions/{uuid.uuid4()}",
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Promotion not found."

    async def test_update_invalid_uuid_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.put(
            "/api/v1/promotions/not-a-uuid",
            json={"title": "Bad"},
        )
        assert resp.status_code == 422

    async def test_passenger_cannot_update_promotion(
        self, passenger_client: AsyncClient, seed_promotions
    ):
        promo_id = seed_promotions["active_a"].id
        resp = await passenger_client.put(
            f"/api/v1/promotions/{promo_id}",
            json={"title": "Hacked"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_update_promotion(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        promo_id = seed_promotions["active_a"].id
        resp = await unauthenticated_client.put(
            f"/api/v1/promotions/{promo_id}",
            json={"title": "Hacked"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /promotions/{promotion_id}  (admin only)
# ══════════════════════════════════════════════════════════════════════════════

class TestDeletePromotion:
    async def test_admin_can_delete_promotion(
        self, admin_client: AsyncClient, unauthenticated_client: AsyncClient, test_session_factory
    ):
        create_resp = await admin_client.post(
            "/api/v1/promotions", json=valid_promotion_payload(title="Delete Me")
        )
        assert create_resp.status_code == 201
        promo_id = create_resp.json()["id"]

        del_resp = await admin_client.delete(f"/api/v1/promotions/{promo_id}")
        assert del_resp.status_code == 204

        confirm = await unauthenticated_client.get(f"/api/v1/promotions/{promo_id}")
        assert confirm.status_code == 404

    async def test_delete_nonexistent_promotion_returns_404(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.delete(f"/api/v1/promotions/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Promotion not found."

    async def test_delete_invalid_uuid_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.delete("/api/v1/promotions/not-a-uuid")
        assert resp.status_code == 422

    async def test_passenger_cannot_delete_promotion(
        self, passenger_client: AsyncClient, seed_promotions
    ):
        promo_id = seed_promotions["active_b"].id
        resp = await passenger_client.delete(f"/api/v1/promotions/{promo_id}")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_delete_promotion(
        self, unauthenticated_client: AsyncClient, seed_promotions
    ):
        promo_id = seed_promotions["active_b"].id
        resp = await unauthenticated_client.delete(f"/api/v1/promotions/{promo_id}")
        assert resp.status_code == 401