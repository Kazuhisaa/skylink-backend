import uuid
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import delete
from app.models.bookings import Booking, Passenger
from app.models.flights import Airport, Aircraft, SeatClass, Flight, FlightSeatPricing
from app.models.audit import RescheduleHistory, Cancellation

# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_booking_data(test_session_factory, seed_users):
    """Seed airports, aircraft, seat classes, and one scheduled flight."""
    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([
                Airport(id=10, iata_code="MNL", name="Ninoy Aquino International Airport", city="Manila", country="Philippines", timezone="Asia/Manila"),
                Airport(id=11, iata_code="CEB", name="Mactan-Cebu International Airport", city="Cebu", country="Philippines", timezone="Asia/Manila"),
                Aircraft(id=10, model="Airbus A320", total_seats=180, registration="RP-C9999"),
                SeatClass(id=10, name="Economy"),
                SeatClass(id=11, name="Business"),
            ])

    flight_id = uuid.uuid4()
    cancelled_flight_id = uuid.uuid4()

    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([
                Flight(
                    id=flight_id,
                    flight_number="BK-001",
                    aircraft_id=10,
                    origin_airport_id=10,
                    destination_airport_id=11,
                    departure_time=datetime(2025, 12, 1, 8, 0, tzinfo=timezone.utc),
                    arrival_time=datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc),
                    status="scheduled",
                    created_by=seed_users["admin"].id,
                ),
                Flight(
                    id=cancelled_flight_id,
                    flight_number="BK-002",
                    aircraft_id=10,
                    origin_airport_id=10,
                    destination_airport_id=11,
                    departure_time=datetime(2025, 12, 2, 8, 0, tzinfo=timezone.utc),
                    arrival_time=datetime(2025, 12, 2, 10, 0, tzinfo=timezone.utc),
                    status="cancelled",
                    created_by=seed_users["admin"].id,
                ),
                FlightSeatPricing(flight_id=flight_id, seat_class_id=10, total_seats=150, available_seats=150, price=480000),
                FlightSeatPricing(flight_id=flight_id, seat_class_id=11, total_seats=30, available_seats=30, price=1200000),
                FlightSeatPricing(flight_id=cancelled_flight_id, seat_class_id=10, total_seats=150, available_seats=150, price=480000),
            ])

    yield {
        "flight_id": flight_id,
        "cancelled_flight_id": cancelled_flight_id,
        "economy_id": 10,
        "business_id": 11,
        "admin": seed_users["admin"],
        "passenger": seed_users["passenger"],
    }

    async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(RescheduleHistory))
                await session.execute(delete(Cancellation))
                await session.execute(delete(Passenger))
                await session.execute(delete(Booking))
                await session.execute(delete(FlightSeatPricing))
                await session.execute(delete(Flight).where(Flight.id.in_([flight_id, cancelled_flight_id])))
                await session.execute(delete(SeatClass).where(SeatClass.id.in_([10, 11])))
                await session.execute(delete(Aircraft).where(Aircraft.id == 10))
                await session.execute(delete(Airport).where(Airport.id.in_([10, 11])))


@pytest_asyncio.fixture(loop_scope="session")
async def seed_one_booking(test_session_factory, seed_booking_data, seed_users):
    """Create one confirmed booking owned by the passenger user."""
    booking_id = uuid.uuid4()
    async with test_session_factory() as session:
        async with session.begin():
            booking = Booking(
                id=booking_id,
                user_id=seed_users["passenger"].id,
                flight_id=seed_booking_data["flight_id"],
                seat_class_id=seed_booking_data["economy_id"],
                seat_number="12A",
                status="confirmed",
                total_price=480000,
            )
            session.add(booking)
            await session.flush()
            session.add(Passenger(
                booking_id=booking_id,
                first_name="Juan",
                last_name="Dela Cruz",
                date_of_birth=datetime(1990, 1, 1).date(),
                passport_number="P1234567",
                nationality="Filipino",
            ))

    yield booking_id

    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(delete(RescheduleHistory).where(RescheduleHistory.booking_id == booking_id))
            await session.execute(delete(Cancellation).where(Cancellation.booking_id == booking_id))
            await session.execute(delete(Passenger).where(Passenger.booking_id == booking_id))
            await session.execute(delete(Booking).where(Booking.id == booking_id))


def valid_booking_payload(flight_id: uuid.UUID, seat_class_id: int) -> dict:
    return {
        "flight_id": str(flight_id),
        "seat_class_id": seat_class_id,
        "seat_number": "10A",
        "passengers": [
            {
                "first_name": "Maria",
                "last_name": "Santos",
                "date_of_birth": "1995-05-15",
                "passport_number": "P9999999",
                "nationality": "Filipino",
            }
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# POST /bookings  — create booking
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateBooking:
    async def test_passenger_can_create_booking(
        self, passenger_client: AsyncClient, seed_booking_data
    ):
        payload = valid_booking_payload(seed_booking_data["flight_id"], seed_booking_data["economy_id"])
        resp = await passenger_client.post("/api/v1/bookings", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "confirmed"
        assert data["seat_class"]["id"] == seed_booking_data["economy_id"]
        assert len(data["passengers"]) == 1
        assert "flight" in data

    async def test_unauthenticated_cannot_create_booking(
        self, unauthenticated_client: AsyncClient, seed_booking_data
    ):
        payload = valid_booking_payload(seed_booking_data["flight_id"], seed_booking_data["economy_id"])
        resp = await unauthenticated_client.post("/api/v1/bookings", json=payload)
        assert resp.status_code == 401

    async def test_booking_nonexistent_flight_returns_404(
        self, passenger_client: AsyncClient, seed_booking_data
    ):
        payload = valid_booking_payload(uuid.uuid4(), seed_booking_data["economy_id"])
        resp = await passenger_client.post("/api/v1/bookings", json=payload)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Flight not found."

    async def test_booking_cancelled_flight_returns_400(
        self, passenger_client: AsyncClient, seed_booking_data
    ):
        payload = valid_booking_payload(seed_booking_data["cancelled_flight_id"], seed_booking_data["economy_id"])
        resp = await passenger_client.post("/api/v1/bookings", json=payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Flight is not available for booking."

    async def test_booking_invalid_seat_class_returns_404(
        self, passenger_client: AsyncClient, seed_booking_data
    ):
        payload = valid_booking_payload(seed_booking_data["flight_id"], 9999)
        resp = await passenger_client.post("/api/v1/bookings", json=payload)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Seat class not available for this flight."

    async def test_booking_no_passengers_returns_422(
        self, passenger_client: AsyncClient, seed_booking_data
    ):
        payload = valid_booking_payload(seed_booking_data["flight_id"], seed_booking_data["economy_id"])
        payload["passengers"] = []
        resp = await passenger_client.post("/api/v1/bookings", json=payload)
        assert resp.status_code == 422

    async def test_booking_missing_required_fields_returns_422(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.post("/api/v1/bookings", json={})
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /bookings  — list user bookings
# ══════════════════════════════════════════════════════════════════════════════

class TestGetUserBookings:
    async def test_passenger_can_list_own_bookings(
        self, passenger_client: AsyncClient, seed_one_booking
    ):
        resp = await passenger_client.get("/api/v1/bookings")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_list_contains_seeded_booking(
        self, passenger_client: AsyncClient, seed_one_booking
    ):
        resp = await passenger_client.get("/api/v1/bookings?size=100")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(seed_one_booking) in ids

    async def test_unauthenticated_cannot_list_bookings(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/bookings")
        assert resp.status_code == 401

    async def test_pagination_size(
        self, passenger_client: AsyncClient, seed_one_booking
    ):
        resp = await passenger_client.get("/api/v1/bookings?page=1&size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1
        assert data["size"] == 1

    async def test_invalid_page_returns_422(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.get("/api/v1/bookings?page=0")
        assert resp.status_code == 422

    async def test_invalid_size_returns_422(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.get("/api/v1/bookings?size=0")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /bookings/{booking_id}  — get single booking
# ══════════════════════════════════════════════════════════════════════════════

class TestGetBooking:
    async def test_passenger_can_get_own_booking(
        self, passenger_client: AsyncClient, seed_one_booking
    ):
        resp = await passenger_client.get(f"/api/v1/bookings/{seed_one_booking}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(seed_one_booking)
        assert data["status"] == "confirmed"
        assert "flight" in data
        assert "passengers" in data
        assert "seat_class" in data

    async def test_nonexistent_booking_returns_404(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.get(f"/api/v1/bookings/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Booking not found."

    async def test_invalid_uuid_returns_422(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.get("/api/v1/bookings/not-a-uuid")
        assert resp.status_code == 422

    async def test_unauthenticated_cannot_get_booking(
        self, unauthenticated_client: AsyncClient, seed_one_booking
    ):
        resp = await unauthenticated_client.get(f"/api/v1/bookings/{seed_one_booking}")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# PUT /bookings/{booking_id}/reschedule
# ══════════════════════════════════════════════════════════════════════════════

class TestRescheduleBooking:
    async def test_passenger_can_reschedule_booking(
        self, passenger_client: AsyncClient, seed_booking_data, test_session_factory, seed_users
    ):
        # Create a fresh booking to reschedule
        booking_id = uuid.uuid4()
        new_flight_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(Flight(
                    id=new_flight_id,
                    flight_number="BK-RSC",
                    aircraft_id=10,
                    origin_airport_id=10,
                    destination_airport_id=11,
                    departure_time=datetime(2025, 12, 5, 8, 0, tzinfo=timezone.utc),
                    arrival_time=datetime(2025, 12, 5, 10, 0, tzinfo=timezone.utc),
                    status="scheduled",
                    created_by=seed_users["admin"].id,
                ))
                session.add(FlightSeatPricing(
                    flight_id=new_flight_id,
                    seat_class_id=seed_booking_data["economy_id"],
                    total_seats=150,
                    available_seats=150,
                    price=480000,
                ))
                session.add(Booking(
                    id=booking_id,
                    user_id=seed_users["passenger"].id,
                    flight_id=seed_booking_data["flight_id"],
                    seat_class_id=seed_booking_data["economy_id"],
                    status="confirmed",
                    total_price=480000,
                ))
                await session.flush()
                session.add(Passenger(
                    booking_id=booking_id,
                    first_name="Reschedule",
                    last_name="Test",
                    date_of_birth=datetime(1990, 1, 1).date(),
                    passport_number="P0000001",
                    nationality="Filipino",
                ))

        resp = await passenger_client.put(
            f"/api/v1/bookings/{booking_id}/reschedule",
            json={"new_flight_id": str(new_flight_id), "reason": "Change of plans"},
        )
        assert resp.status_code == 200
        assert resp.json()["flight"]["flight_number"] == "BK-RSC"

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(RescheduleHistory).where(RescheduleHistory.booking_id == booking_id))
                await session.execute(delete(Passenger).where(Passenger.booking_id == booking_id))
                await session.execute(delete(Booking).where(Booking.id == booking_id))
                await session.execute(delete(FlightSeatPricing).where(FlightSeatPricing.flight_id == new_flight_id))
                await session.execute(delete(Flight).where(Flight.id == new_flight_id))

    async def test_reschedule_to_same_flight_returns_400(
        self, passenger_client: AsyncClient, seed_one_booking, seed_booking_data
    ):
        resp = await passenger_client.put(
            f"/api/v1/bookings/{seed_one_booking}/reschedule",
            json={"new_flight_id": str(seed_booking_data["flight_id"])},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "New flight is the same as current flight."

    async def test_reschedule_to_nonexistent_flight_returns_404(
        self, passenger_client: AsyncClient, seed_one_booking
    ):
        resp = await passenger_client.put(
            f"/api/v1/bookings/{seed_one_booking}/reschedule",
            json={"new_flight_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "New flight not found."

    async def test_reschedule_nonexistent_booking_returns_404(
        self, passenger_client: AsyncClient, seed_booking_data
    ):
        resp = await passenger_client.put(
            f"/api/v1/bookings/{uuid.uuid4()}/reschedule",
            json={"new_flight_id": str(seed_booking_data["flight_id"])},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Booking not found."

    async def test_unauthenticated_cannot_reschedule(
        self, unauthenticated_client: AsyncClient, seed_one_booking, seed_booking_data
    ):
        resp = await unauthenticated_client.put(
            f"/api/v1/bookings/{seed_one_booking}/reschedule",
            json={"new_flight_id": str(seed_booking_data["flight_id"])},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /bookings/{booking_id}  — cancel booking
# ══════════════════════════════════════════════════════════════════════════════

class TestCancelBooking:
    async def test_passenger_can_cancel_booking(
        self, passenger_client: AsyncClient, seed_booking_data, test_session_factory, seed_users
    ):
        booking_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(Booking(
                    id=booking_id,
                    user_id=seed_users["passenger"].id,
                    flight_id=seed_booking_data["flight_id"],
                    seat_class_id=seed_booking_data["economy_id"],
                    status="confirmed",
                    total_price=480000,
                ))
                await session.flush()
                session.add(Passenger(
                    booking_id=booking_id,
                    first_name="Cancel",
                    last_name="Test",
                    date_of_birth=datetime(1990, 1, 1).date(),
                    passport_number="P0000002",
                    nationality="Filipino",
                ))

        resp = await passenger_client.request(
            "DELETE",
            f"/api/v1/bookings/{booking_id}",
            json={"reason": "No longer needed"},
        )
        assert resp.status_code == 204

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(Cancellation).where(Cancellation.booking_id == booking_id))
                await session.execute(delete(Passenger).where(Passenger.booking_id == booking_id))
                await session.execute(delete(Booking).where(Booking.id == booking_id))

    async def test_cancel_already_cancelled_booking_returns_400(
        self, passenger_client: AsyncClient, seed_booking_data, test_session_factory, seed_users
    ):
        booking_id = uuid.uuid4()
        async with test_session_factory() as session:
            async with session.begin():
                session.add(Booking(
                    id=booking_id,
                    user_id=seed_users["passenger"].id,
                    flight_id=seed_booking_data["flight_id"],
                    seat_class_id=seed_booking_data["economy_id"],
                    status="cancelled",
                    total_price=480000,
                ))
                await session.flush()
                session.add(Passenger(
                    booking_id=booking_id,
                    first_name="Already",
                    last_name="Cancelled",
                    date_of_birth=datetime(1990, 1, 1).date(),
                    passport_number="P0000003",
                    nationality="Filipino",
                ))

        resp = await passenger_client.request(
            "DELETE",
            f"/api/v1/bookings/{booking_id}",
            json={"reason": "test"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Booking is already cancelled."

        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(delete(Passenger).where(Passenger.booking_id == booking_id))
                await session.execute(delete(Booking).where(Booking.id == booking_id))

    async def test_cancel_nonexistent_booking_returns_404(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.request(
            "DELETE",
            f"/api/v1/bookings/{uuid.uuid4()}",
            json={"reason": "test"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Booking not found."

    async def test_unauthenticated_cannot_cancel(
        self, unauthenticated_client: AsyncClient, seed_one_booking
    ):
        resp = await unauthenticated_client.request(
            "DELETE",
            f"/api/v1/bookings/{seed_one_booking}",
            json={"reason": "test"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# GET /bookings/admin/all  — admin list all bookings
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminGetAllBookings:
    async def test_admin_all_route_conflicts_with_booking_id_param(
        self, admin_client: AsyncClient, seed_one_booking
    ):
        # /bookings/admin/all will be matched by /{booking_id} first,
        # "admin" is not a valid UUID so FastAPI returns 422, not 200.
        # This documents the known router ordering bug.
        resp = await admin_client.get("/api/v1/bookings/admin/all")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_admin_all(
        self, passenger_client: AsyncClient
    ):
        resp = await passenger_client.get("/api/v1/bookings/admin/all")
        assert resp.status_code == 403  # same routing conflict, never reaches auth check