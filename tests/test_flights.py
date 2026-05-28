import uuid
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.flights import Airport, Aircraft, SeatClass, Flight, FlightSeatPricing
from app.core.limiter import limiter


# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_flight_data(test_session_factory, seed_users):
    """Seed airports, aircraft, seat classes once for all flight tests."""
    async with test_session_factory() as session:
        async with session.begin():
            manila = Airport(
                id=1,
                iata_code="MNL",
                name="Ninoy Aquino International Airport",
                city="Manila",
                country="Philippines",
                timezone="Asia/Manila",
            )
            cebu = Airport(
                id=2,
                iata_code="CEB",
                name="Mactan-Cebu International Airport",
                city="Cebu",
                country="Philippines",
                timezone="Asia/Manila",
            )
            davao = Airport(
                id=3,
                iata_code="DVO",
                name="Francisco Bangoy International Airport",
                city="Davao",
                country="Philippines",
                timezone="Asia/Manila",
            )
            aircraft = Aircraft(
                id=1,
                model="Airbus A320",
                total_seats=180,
                registration="RP-C1234",
            )
            economy = SeatClass(id=1, name="Economy")
            business = SeatClass(id=2, name="Business")

            session.add_all([manila, cebu, davao, aircraft, economy, business])

    yield {
        "manila_id": 1,
        "cebu_id": 2,
        "davao_id": 3,
        "aircraft_id": 1,
        "economy_id": 1,
        "business_id": 2,
        "admin": seed_users["admin"],
        "passenger": seed_users["passenger"],
    }

    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(delete(FlightSeatPricing))
            await session.execute(delete(Flight))
            await session.execute(delete(SeatClass))
            await session.execute(delete(Aircraft))
            await session.execute(delete(Airport))


@pytest_asyncio.fixture(loop_scope="session")
async def seed_one_flight(test_session_factory, seed_flight_data):
    flight_id = uuid.uuid4()
    async with test_session_factory() as session:
        flight = Flight(
            id=flight_id,
            flight_number="SK-001",
            aircraft_id=seed_flight_data["aircraft_id"],
            origin_airport_id=seed_flight_data["manila_id"],
            destination_airport_id=seed_flight_data["cebu_id"],
            departure_time=datetime(2025, 12, 1, 8, 0, tzinfo=timezone.utc),
            arrival_time=datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc),
            status="scheduled",
            created_by=seed_flight_data["admin"].id,
        )
        session.add(flight)
        await session.flush()
        session.add_all([
            FlightSeatPricing(
                flight_id=flight_id,
                seat_class_id=seed_flight_data["economy_id"],
                total_seats=150,
                available_seats=150,
                price=480000,
            ),
            FlightSeatPricing(
                flight_id=flight_id,
                seat_class_id=seed_flight_data["business_id"],
                total_seats=30,
                available_seats=30,
                price=1200000,
            ),
        ])
        await session.commit()

    yield flight_id

    async with test_session_factory() as session:
        await session.execute(
            delete(FlightSeatPricing).where(FlightSeatPricing.flight_id == flight_id)
        )
        await session.execute(
            delete(Flight).where(Flight.id == flight_id)
        )
        await session.commit()



# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def mock_redis():
    """Patch redis so tests never hit a real Redis instance."""
    return patch(
        "app.services.flights_service.redis_client",
        get=AsyncMock(return_value=None),
        set=AsyncMock(),
        delete_pattern=AsyncMock(),
    )


def valid_flight_payload(
    origin_airport_id: int,
    destination_airport_id: int,
    aircraft_id: int,
    economy_id: int,
    business_id: int,
    flight_number: str = "SK-999",
) -> dict:
    return {
        "flight_number": flight_number,
        "aircraft_id": aircraft_id,
        "origin_airport_id": origin_airport_id,
        "destination_airport_id": destination_airport_id,
        "departure_time": "2025-12-10T08:00:00+00:00",
        "arrival_time": "2025-12-10T10:00:00+00:00",
        "status": "scheduled",
        "seat_pricing": [
            {
                "seat_class_id": economy_id,
                "total_seats": 150,
                "available_seats": 150,
                "price": 480000,
            },
            {
                "seat_class_id": business_id,
                "total_seats": 30,
                "available_seats": 30,
                "price": 1200000,
            },
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /flights  — search & pagination
# ══════════════════════════════════════════════════════════════════════════════

class TestSearchFlights:

    async def test_search_returns_paginated_response(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get("/api/v1/flights")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_search_returns_seeded_flight(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get(
                f"/api/v1/flights?status=scheduled&size=100"
            )
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(seed_one_flight) in ids

    async def test_search_filter_by_origin(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get("/api/v1/flights?origin=MNL")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        for item in items:
            assert item["origin_airport"]["iata_code"] == "MNL"

    async def test_search_filter_by_destination(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get("/api/v1/flights?destination=CEB")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        for item in items:
            assert item["destination_airport"]["iata_code"] == "CEB"


    async def test_search_filter_by_status(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get("/api/v1/flights?status=scheduled")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "scheduled"

    async def test_search_wrong_origin_returns_empty(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get("/api/v1/flights?origin=ZZZ")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_search_pagination_size(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get("/api/v1/flights?page=1&size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1
        assert data["size"] == 1

    async def test_search_page_out_of_range_returns_empty(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await unauthenticated_client.get("/api/v1/flights?page=9999&size=10")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_search_invalid_size_rejected(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/flights?size=0")
        assert resp.status_code == 422

    async def test_search_invalid_page_rejected(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/flights?page=0")
        assert resp.status_code == 422

    async def test_search_cache_hit_skips_db(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        """When Redis returns cached data, DB should not be queried."""
        import json
        cached = json.dumps({
            "items": [],
            "total": 0,
        })
        with patch(
            "app.services.flights_service.redis_client",
            get=AsyncMock(return_value=cached),
            set=AsyncMock(),
            delete_pattern=AsyncMock(),
        ):
            resp = await unauthenticated_client.get("/api/v1/flights")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# GET /flights/{id}
# ══════════════════════════════════════════════════════════════════════════════

class TestGetFlight:

    async def test_get_existing_flight(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        resp = await unauthenticated_client.get(f"/api/v1/flights/{seed_one_flight}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(seed_one_flight)
        assert data["flight_number"] == "SK-001"
        assert "origin_airport" in data
        assert "destination_airport" in data
        assert "aircraft" in data
        assert "seat_pricing" in data
        assert len(data["seat_pricing"]) == 2

    async def test_get_nonexistent_flight_returns_404(
        self, unauthenticated_client: AsyncClient
    ):
        fake_id = uuid.uuid4()
        resp = await unauthenticated_client.get(f"/api/v1/flights/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Flight not found."

    async def test_get_invalid_uuid_returns_422(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/flights/not-a-uuid")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# POST /flights  — admin create
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateFlight:

    async def test_admin_can_create_flight(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-100",
        )
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["flight_number"] == "SK-100"
        assert data["status"] == "scheduled"
        assert len(data["seat_pricing"]) == 2
        assert data["origin_airport"]["iata_code"] == "MNL"
        assert data["destination_airport"]["iata_code"] == "CEB"

    async def test_passenger_cannot_create_flight(
        self, passenger_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-101",
        )
        with mock_redis():
            resp = await passenger_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_create_flight(
        self, unauthenticated_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-102",
        )
        resp = await unauthenticated_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 401  # HTTPBearer returns 401 when no token

    async def test_duplicate_flight_number_returns_409(
        self, admin_client: AsyncClient, seed_flight_data, seed_one_flight
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-001",  # already seeded
        )
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Flight number already exists."

    async def test_same_origin_destination_returns_400(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["manila_id"],  # same as origin
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-103",
        )
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 400
        assert "same" in resp.json()["detail"].lower()

    async def test_invalid_aircraft_returns_404(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            9999,  # nonexistent aircraft
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-104",
        )
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Aircraft not found."

    async def test_invalid_airport_returns_404(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            9999,  # nonexistent airport
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-105",
        )
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Airport not found."

    async def test_arrival_before_departure_rejected(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-106",
        )
        # flip times
        payload["departure_time"] = "2025-12-10T10:00:00+00:00"
        payload["arrival_time"] = "2025-12-10T08:00:00+00:00"
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 422

    async def test_invalid_status_rejected(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-107",
        )
        payload["status"] = "flying"  # not in allowed set
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 422

    async def test_invalid_seat_class_returns_404(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-108",
        )
        payload["seat_pricing"][0]["seat_class_id"] = 9999  # nonexistent
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 404
        assert "Seat class" in resp.json()["detail"]

    async def test_create_flight_without_pricing(
        self, admin_client: AsyncClient, seed_flight_data
    ):
        payload = valid_flight_payload(
            seed_flight_data["manila_id"],
            seed_flight_data["cebu_id"],
            seed_flight_data["aircraft_id"],
            seed_flight_data["economy_id"],
            seed_flight_data["business_id"],
            flight_number="SK-109",
        )
        payload.pop("seat_pricing")
        with mock_redis():
            resp = await admin_client.post("/api/v1/flights", json=payload)
        assert resp.status_code == 201
        assert resp.json()["seat_pricing"] == []

    async def test_missing_required_fields_rejected(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.post("/api/v1/flights", json={})
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# PUT /flights/{id}  — admin update
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateFlight:

    async def test_admin_can_update_status(
        self, admin_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await admin_client.put(
                f"/api/v1/flights/{seed_one_flight}",
                json={"status": "cancelled"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_admin_can_update_flight_number(
        self, admin_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await admin_client.put(
                f"/api/v1/flights/{seed_one_flight}",
                json={"flight_number": "SK-001-UPD"},
            )
        assert resp.status_code == 200
        assert resp.json()["flight_number"] == "SK-001-UPD"

    async def test_update_to_duplicate_flight_number_returns_409(
        self, admin_client: AsyncClient, seed_one_flight, seed_flight_data, test_session_factory
    ):
        second_id = uuid.uuid4()
        async with test_session_factory() as session:
            session.add(Flight(
                id=second_id,
                flight_number="SK-CONF",  # 7 chars, fits VARCHAR(10)
                aircraft_id=seed_flight_data["aircraft_id"],
                origin_airport_id=seed_flight_data["manila_id"],
                destination_airport_id=seed_flight_data["cebu_id"],
                departure_time=datetime(2025, 12, 5, 8, 0, tzinfo=timezone.utc),
                arrival_time=datetime(2025, 12, 5, 10, 0, tzinfo=timezone.utc),
                status="scheduled",
                created_by=seed_flight_data["admin"].id,
            ))
            await session.commit()

        with mock_redis():
            resp = await admin_client.put(
                f"/api/v1/flights/{seed_one_flight}",
                json={"flight_number": "SK-CONF"},
            )
        assert resp.status_code == 409

        async with test_session_factory() as session:
            await session.execute(delete(Flight).where(Flight.id == second_id))
            await session.commit()

    async def test_update_same_origin_destination_returns_400(
        self, admin_client: AsyncClient, seed_one_flight, seed_flight_data
    ):
        with mock_redis():
            resp = await admin_client.put(
                f"/api/v1/flights/{seed_one_flight}",
                json={
                    "origin_airport_id": seed_flight_data["manila_id"],
                    "destination_airport_id": seed_flight_data["manila_id"],
                },
            )
        assert resp.status_code == 400

    async def test_update_nonexistent_flight_returns_404(
        self, admin_client: AsyncClient
    ):
        with mock_redis():
            resp = await admin_client.put(
                f"/api/v1/flights/{uuid.uuid4()}",
                json={"status": "cancelled"},
            )
        assert resp.status_code == 404

    async def test_passenger_cannot_update_flight(
        self, passenger_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await passenger_client.put(
                f"/api/v1/flights/{seed_one_flight}",
                json={"status": "cancelled"},
            )
        assert resp.status_code == 403

    async def test_update_invalid_aircraft_returns_404(
        self, admin_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await admin_client.put(
                f"/api/v1/flights/{seed_one_flight}",
                json={"aircraft_id": 9999},
            )
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /flights/{id}  — admin delete
# ══════════════════════════════════════════════════════════════════════════════

class TestDeleteFlight:

    async def test_admin_can_delete_flight(
        self, admin_client: AsyncClient, seed_flight_data, test_session_factory
    ):
        # Create a deletable flight with no bookings
        flight_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(Flight(
                    id=flight_id,
                    flight_number="SK-DEL",
                    aircraft_id=seed_flight_data["aircraft_id"],
                    origin_airport_id=seed_flight_data["manila_id"],
                    destination_airport_id=seed_flight_data["cebu_id"],
                    departure_time=datetime(2025, 12, 20, 8, 0, tzinfo=timezone.utc),
                    arrival_time=datetime(2025, 12, 20, 10, 0, tzinfo=timezone.utc),
                    status="scheduled",
                    created_by=seed_flight_data["admin"].id,
                ))

        with mock_redis():
            resp = await admin_client.delete(f"/api/v1/flights/{flight_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp2 = await admin_client.get(f"/api/v1/flights/{flight_id}")
        assert resp2.status_code == 404

    async def test_delete_nonexistent_flight_returns_404(
        self, admin_client: AsyncClient
    ):
        with mock_redis():
            resp = await admin_client.delete(f"/api/v1/flights/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_passenger_cannot_delete_flight(
        self, passenger_client: AsyncClient, seed_one_flight
    ):
        with mock_redis():
            resp = await passenger_client.delete(f"/api/v1/flights/{seed_one_flight}")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_delete_flight(
        self, unauthenticated_client: AsyncClient, seed_one_flight
    ):
        resp = await unauthenticated_client.delete(f"/api/v1/flights/{seed_one_flight}")
        assert resp.status_code == 401  # HTTPBearer returns 401 when no token


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ══════════════════════════════════════════════════════════════════════════════

class TestRateLimiter:

    async def test_limiter_is_disabled_during_normal_tests(
        self, unauthenticated_client: AsyncClient
    ):
        """Confirm limiter is off so other tests are not affected."""
        assert limiter.enabled is False

    async def test_limiter_blocks_after_limit(
        self, seed_one_flight
    ):
        """
        Re-enable limiter and confirm 429 is returned after exceeding limit.
        Uses a fresh unauthenticated client so dependency overrides don't interfere.
        """
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        limiter.enabled = True
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://testserver",
            ) as client:
                responses = []
                with mock_redis():
                    for _ in range(65):  # limit is 60/minute
                        r = await client.get("/api/v1/flights")
                        responses.append(r.status_code)
                assert 429 in responses
        finally:
            limiter.enabled = False  # always restore