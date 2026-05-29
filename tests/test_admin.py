import uuid
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.bookings import Booking
from app.models.flights import Airport, Aircraft, SeatClass, Flight


# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_admin_report_data(test_session_factory, seed_users):
    """
    Seeds the minimum FK chain required to create Bookings:
      Airport × 2 → Aircraft → Flight → SeatClass → Booking × 3

    Booking statuses: confirmed, confirmed, cancelled
    total_price:      5000,     3000,     2000
    booked_at:        2026-01-10, 2026-03-15, 2026-03-20

    Depends on seed_users so the admin user (used as Flight.created_by
    and Booking.user_id) already exists.
    """
    admin_user = seed_users["admin"]

    origin = Airport(
        iata_code="MNL",
        name="Ninoy Aquino International Airport",
        city="Manila",
        country="Philippines",
        timezone="Asia/Manila",
    )
    destination = Airport(
        iata_code="CEB",
        name="Mactan-Cebu International Airport",
        city="Cebu",
        country="Philippines",
        timezone="Asia/Manila",
    )
    aircraft = Aircraft(
        model="Airbus A320",
        total_seats=180,
        registration=f"RP-{uuid.uuid4().hex[:6].upper()}",
    )
    seat_class = SeatClass(name=f"Economy-{uuid.uuid4().hex[:4]}")

    flight = Flight(
        id=uuid.uuid4(),
        flight_number=f"PR{uuid.uuid4().hex[:4].upper()}",
        departure_time=datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc),
        arrival_time=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
        status="scheduled",
        created_by=admin_user.id,
    )

    booking_jan = Booking(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        seat_number="1A",
        status="confirmed",
        total_price=5000,
        booked_at=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
    )
    booking_mar_confirmed = Booking(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        seat_number="2B",
        status="confirmed",
        total_price=3000,
        booked_at=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
    )
    booking_mar_cancelled = Booking(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        seat_number="3C",
        status="cancelled",
        total_price=2000,
        booked_at=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
    )

    async with test_session_factory() as session:
        async with session.begin():
            session.add_all([origin, destination, aircraft, seat_class])
            await session.flush()

            flight.aircraft_id = aircraft.id
            flight.origin_airport_id = origin.id
            flight.destination_airport_id = destination.id
            session.add(flight)
            await session.flush()

            for booking in [booking_jan, booking_mar_confirmed, booking_mar_cancelled]:
                booking.flight_id = flight.id
                booking.seat_class_id = seat_class.id
            session.add_all([booking_jan, booking_mar_confirmed, booking_mar_cancelled])

    yield {
        "booking_jan": booking_jan,
        "booking_mar_confirmed": booking_mar_confirmed,
        "booking_mar_cancelled": booking_mar_cancelled,
        "flight": flight,
        "seat_class": seat_class,
        "aircraft": aircraft,
        "origin": origin,
        "destination": destination,
    }

    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(Booking).where(
                    Booking.id.in_([
                        booking_jan.id,
                        booking_mar_confirmed.id,
                        booking_mar_cancelled.id,
                    ])
                )
            )
            await session.execute(delete(Flight).where(Flight.id == flight.id))
            await session.execute(delete(SeatClass).where(SeatClass.id == seat_class.id))
            await session.execute(delete(Aircraft).where(Aircraft.id == aircraft.id))
            await session.execute(
                delete(Airport).where(Airport.id.in_([origin.id, destination.id]))
            )


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/reports
# ══════════════════════════════════════════════════════════════════════════════

class TestGetBookingReport:

    # ── Access control ────────────────────────────────────────────────────────

    async def test_admin_can_access_report(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_report(
        self, passenger_client: AsyncClient, seed_admin_report_data
    ):
        resp = await passenger_client.get("/api/v1/admin/reports")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_report(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/reports")
        assert resp.status_code == 401

    # ── Response shape ────────────────────────────────────────────────────────

    async def test_report_has_correct_fields(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_bookings" in data
        assert "confirmed_bookings" in data
        assert "cancelled_bookings" in data
        assert "total_revenue" in data
        assert "confirmed_revenue" in data

    # ── Unfiltered totals ─────────────────────────────────────────────────────

    async def test_unfiltered_report_counts_all_seeded_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        assert resp.status_code == 200
        data = resp.json()
        # At minimum our 3 seeded bookings must be counted
        assert data["total_bookings"] >= 3
        assert data["confirmed_bookings"] >= 2
        assert data["cancelled_bookings"] >= 1

    async def test_unfiltered_revenue_includes_all_seeded_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        data = resp.json()
        # Our 3 bookings add 10 000 total and 8 000 confirmed
        assert data["total_revenue"] >= 10_000
        assert data["confirmed_revenue"] >= 8_000

    # ── Date filtering ────────────────────────────────────────────────────────

    async def test_date_range_filters_to_march_bookings_only(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports"
            "?date_from=2026-03-01T00:00:00Z"
            "&date_to=2026-03-31T23:59:59Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only the 2 March bookings should appear
        assert data["total_bookings"] == 2
        assert data["confirmed_bookings"] == 1
        assert data["cancelled_bookings"] == 1
        assert data["total_revenue"] == 5_000       # 3000 + 2000
        assert data["confirmed_revenue"] == 3_000

    async def test_date_from_only_excludes_earlier_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports?date_from=2026-02-01T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        # Jan booking is excluded; at least the 2 March ones remain
        assert data["total_bookings"] >= 2
        assert data["total_revenue"] >= 5_000

    async def test_date_to_only_excludes_later_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports?date_to=2026-01-31T23:59:59Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only the Jan booking falls within range
        assert data["total_bookings"] >= 1
        assert data["confirmed_revenue"] >= 5_000

    async def test_date_range_with_no_bookings_returns_zeros(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports"
            "?date_from=2020-01-01T00:00:00Z"
            "&date_to=2020-01-02T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_bookings"] == 0
        assert data["confirmed_bookings"] == 0
        assert data["cancelled_bookings"] == 0
        assert data["total_revenue"] == 0
        assert data["confirmed_revenue"] == 0

    # ── date_from/date_to echoed in response ──────────────────────────────────

    async def test_date_filters_are_echoed_in_response(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports"
            "?date_from=2026-03-01T00:00:00Z"
            "&date_to=2026-03-31T23:59:59Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["date_from"] is not None
        assert data["date_to"] is not None

    async def test_no_filters_date_fields_are_null(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["date_from"] is None
        assert data["date_to"] is None

    # ── Invalid query params ──────────────────────────────────────────────────

    async def test_invalid_date_format_returns_422(
        self, admin_client: AsyncClient
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports?date_from=not-a-date"
        )
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN AIRPORT CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminAirportCRUD:

    async def test_admin_can_list_airports(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/airports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_passenger_cannot_list_airports(self, passenger_client: AsyncClient):
        resp = await passenger_client.get("/api/v1/admin/airports")
        assert resp.status_code == 403

    async def test_admin_can_create_airport(self, admin_client: AsyncClient):
        payload = {
            "iata_code": "TST",
            "name": "Test Airport",
            "city": "Test City",
            "country": "Philippines",
            "timezone": "Asia/Manila",
        }

        resp = await admin_client.post("/api/v1/admin/airports", json=payload)

        assert resp.status_code == 201

        data = resp.json()

        assert data["iata_code"] == "TST"
        assert data["name"] == "Test Airport"

    async def test_duplicate_airport_iata_returns_409(self, admin_client: AsyncClient):
        payload = {
            "iata_code": "DUP",
            "name": "Duplicate Airport",
            "city": "City",
            "country": "PH",
            "timezone": "Asia/Manila",
        }

        first = await admin_client.post("/api/v1/admin/airports", json=payload)
        assert first.status_code == 201

        second = await admin_client.post("/api/v1/admin/airports", json=payload)

        assert second.status_code == 409

    async def test_admin_can_update_airport(self, admin_client: AsyncClient):
        create_payload = {
            "iata_code": "UPD",
            "name": "Old Airport",
            "city": "Old City",
            "country": "PH",
            "timezone": "Asia/Manila",
        }

        created = await admin_client.post("/api/v1/admin/airports", json=create_payload)

        airport_id = created.json()["id"]

        update_payload = {
            "name": "Updated Airport",
            "city": "Updated City",
        }

        updated = await admin_client.put(
            f"/api/v1/admin/airports/{airport_id}",
            json=update_payload,
        )

        assert updated.status_code == 200

        data = updated.json()

        assert data["name"] == "Updated Airport"
        assert data["city"] == "Updated City"

    async def test_admin_can_delete_unused_airport(self, admin_client: AsyncClient):
        payload = {
            "iata_code": "DEL",
            "name": "Delete Airport",
            "city": "Delete City",
            "country": "PH",
            "timezone": "Asia/Manila",
        }

        created = await admin_client.post("/api/v1/admin/airports", json=payload)

        airport_id = created.json()["id"]

        deleted = await admin_client.delete(
            f"/api/v1/admin/airports/{airport_id}"
        )

        assert deleted.status_code == 204

        get_resp = await admin_client.get("/api/v1/admin/airports")

        ids = [airport["id"] for airport in get_resp.json()]

        assert airport_id not in ids

    async def test_delete_airport_used_by_flight_returns_409(
        self,
        admin_client: AsyncClient,
        seed_admin_report_data,
    ):
        airport_id = seed_admin_report_data["origin"].id

        resp = await admin_client.delete(
            f"/api/v1/admin/airports/{airport_id}"
        )

        assert resp.status_code == 409


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN AIRCRAFT CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminAircraftCRUD:

    async def test_admin_can_list_aircraft(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/aircraft")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_admin_can_create_aircraft(self, admin_client: AsyncClient):
        payload = {
            "model": "Airbus A321",
            "total_seats": 220,
            "registration": "RP-TST01",
        }

        resp = await admin_client.post("/api/v1/admin/aircraft", json=payload)

        assert resp.status_code == 201

        data = resp.json()

        assert data["registration"] == "RP-TST01"

    async def test_duplicate_aircraft_registration_returns_409(
        self,
        admin_client: AsyncClient,
    ):
        payload = {
            "model": "Boeing 777",
            "total_seats": 300,
            "registration": "RP-DUP01",
        }

        first = await admin_client.post("/api/v1/admin/aircraft", json=payload)

        assert first.status_code == 201

        second = await admin_client.post("/api/v1/admin/aircraft", json=payload)

        assert second.status_code == 409

    async def test_admin_can_update_aircraft(self, admin_client: AsyncClient):
        create_payload = {
            "model": "ATR 72",
            "total_seats": 70,
            "registration": "RP-UPD01",
        }

        created = await admin_client.post(
            "/api/v1/admin/aircraft",
            json=create_payload,
        )

        aircraft_id = created.json()["id"]

        update_payload = {
            "model": "ATR 72-600",
            "total_seats": 78,
            "registration": "RP-UPD01",
        }

        updated = await admin_client.put(
            f"/api/v1/admin/aircraft/{aircraft_id}",
            json=update_payload,
        )

        assert updated.status_code == 200

        data = updated.json()

        assert data["model"] == "ATR 72-600"
        assert data["total_seats"] == 78

    async def test_admin_can_delete_unused_aircraft(
        self,
        admin_client: AsyncClient,
    ):
        payload = {
            "model": "Delete Aircraft",
            "total_seats": 100,
            "registration": "RP-DEL01",
        }

        created = await admin_client.post(
            "/api/v1/admin/aircraft",
            json=payload,
        )

        aircraft_id = created.json()["id"]

        deleted = await admin_client.delete(
            f"/api/v1/admin/aircraft/{aircraft_id}"
        )

        assert deleted.status_code == 204

    async def test_delete_aircraft_used_by_flight_returns_409(
        self,
        admin_client: AsyncClient,
        seed_admin_report_data,
    ):
        aircraft_id = seed_admin_report_data["aircraft"].id

        resp = await admin_client.delete(
            f"/api/v1/admin/aircraft/{aircraft_id}"
        )

        assert resp.status_code == 409


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN SEAT CLASS CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminSeatClassCRUD:

    async def test_admin_can_list_seat_classes(
        self,
        admin_client: AsyncClient,
    ):
        resp = await admin_client.get("/api/v1/admin/seat-classes")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_admin_can_create_seat_class(
        self,
        admin_client: AsyncClient,
    ):
        payload = {
            "name": "Premium Economy Test"
        }

        resp = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json=payload,
        )

        assert resp.status_code == 201

        data = resp.json()

        assert data["name"] == "Premium Economy Test"

    async def test_duplicate_seat_class_returns_409(
        self,
        admin_client: AsyncClient,
    ):
        payload = {
            "name": "Duplicate Class"
        }

        first = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json=payload,
        )

        assert first.status_code == 201

        second = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json=payload,
        )

        assert second.status_code == 409

    async def test_admin_can_update_seat_class(
        self,
        admin_client: AsyncClient,
    ):
        created = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json={"name": "Old Class"},
        )

        seat_class_id = created.json()["id"]

        updated = await admin_client.put(
            f"/api/v1/admin/seat-classes/{seat_class_id}",
            json={"name": "Updated Class"},
        )

        assert updated.status_code == 200

        data = updated.json()

        assert data["name"] == "Updated Class"

    async def test_admin_can_delete_unused_seat_class(
        self,
        admin_client: AsyncClient,
    ):
        created = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json={"name": "Delete Class"},
        )

        seat_class_id = created.json()["id"]

        deleted = await admin_client.delete(
            f"/api/v1/admin/seat-classes/{seat_class_id}"
        )

        assert deleted.status_code == 204

    async def test_delete_seat_class_in_use_returns_409(
        self,
        admin_client: AsyncClient,
        seed_admin_report_data,
    ):
        seat_class_id = seed_admin_report_data["seat_class"].id

        resp = await admin_client.delete(
            f"/api/v1/admin/seat-classes/{seat_class_id}"
        )

        assert resp.status_code == 409