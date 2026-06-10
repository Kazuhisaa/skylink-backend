import uuid
from datetime import datetime, timezone

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.auth import LoginAttempt
from app.models.bookings import Booking
from app.models.flights import Aircraft, AircraftSeat, Airport, Flight, SeatClass


# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_admin_report_data(test_session_factory, seed_users):
    admin_user = seed_users["admin"]
    origin = Airport(
        iata_code="AD1",
        name="Ninoy Aquino International Airport",
        city="Manila",
        country="Philippines",
        timezone="Asia/Manila",
    )
    destination = Airport(
        iata_code="AD2",
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
        "admin_user": admin_user,
    }
    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(Booking).where(
                    Booking.id.in_(
                        [
                            booking_jan.id,
                            booking_mar_confirmed.id,
                            booking_mar_cancelled.id,
                        ]
                    )
                )
            )
            await session.execute(delete(Flight).where(Flight.id == flight.id))
            await session.execute(
                delete(AircraftSeat).where(AircraftSeat.seat_class_id == seat_class.id)
            )
            await session.execute(delete(SeatClass).where(SeatClass.id == seat_class.id))
            await session.execute(delete(Aircraft).where(Aircraft.id == aircraft.id))
            await session.execute(
                delete(Airport).where(Airport.id.in_([origin.id, destination.id]))
            )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_login_attempts(test_session_factory, seed_users):
    admin_user = seed_users["admin"]
    attempts = [
        LoginAttempt(
            id=uuid.uuid4(),
            email=admin_user.email,
            ip_address="192.168.1.1",
            attempted_at=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
        ),
        LoginAttempt(
            id=uuid.uuid4(),
            email="unknown@test.com",
            ip_address="10.0.0.1",
            attempted_at=datetime(2026, 4, 2, 11, 0, tzinfo=timezone.utc),
        ),
        LoginAttempt(
            id=uuid.uuid4(),
            email="another@test.com",
            ip_address="10.0.0.2",
            attempted_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
        ),
    ]
    async with test_session_factory() as session:
        async with session.begin():
            session.add_all(attempts)
    yield attempts
    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(LoginAttempt).where(LoginAttempt.id.in_([a.id for a in attempts]))
            )


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/reports  — booking report
# ══════════════════════════════════════════════════════════════════════════════
class TestGetBookingReport:
    async def test_admin_can_access_report(self, admin_client: AsyncClient, seed_admin_report_data):
        resp = await admin_client.get("/api/v1/admin/reports")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_report(
        self, passenger_client: AsyncClient, seed_admin_report_data
    ):
        resp = await passenger_client.get("/api/v1/admin/reports")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_report(self, unauthenticated_client: AsyncClient):
        resp = await unauthenticated_client.get("/api/v1/admin/reports")
        assert resp.status_code == 401

    async def test_report_has_correct_fields(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        data = resp.json()
        assert "total_bookings" in data
        assert "confirmed_bookings" in data
        assert "cancelled_bookings" in data
        assert "total_revenue" in data
        assert "confirmed_revenue" in data
        assert "monthly_revenue" in data

    async def test_monthly_revenue_is_list(self, admin_client: AsyncClient, seed_admin_report_data):
        resp = await admin_client.get("/api/v1/admin/reports")
        data = resp.json()
        assert isinstance(data["monthly_revenue"], list)
        if data["monthly_revenue"]:
            point = data["monthly_revenue"][0]
            assert "month" in point
            assert "year" in point
            assert "revenue" in point
            assert "bookings" in point

    async def test_unfiltered_report_counts_all_seeded_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        data = resp.json()
        assert data["total_bookings"] >= 3
        assert data["confirmed_bookings"] >= 2
        assert data["cancelled_bookings"] >= 1

    async def test_unfiltered_revenue_includes_all_seeded_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        data = resp.json()
        assert data["total_revenue"] >= 10_000
        assert data["confirmed_revenue"] >= 8_000

    async def test_date_range_filters_to_march_bookings_only(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports?date_from=2026-03-01T00:00:00Z&date_to=2026-03-31T23:59:59Z"
        )
        data = resp.json()
        assert data["total_bookings"] == 2
        assert data["confirmed_bookings"] == 1
        assert data["cancelled_bookings"] == 1
        assert data["total_revenue"] == 5_000
        assert data["confirmed_revenue"] == 3_000

    async def test_date_from_only_excludes_earlier_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports?date_from=2026-02-01T00:00:00Z")
        data = resp.json()
        assert data["total_bookings"] >= 2
        assert data["total_revenue"] >= 5_000

    async def test_date_to_only_excludes_later_bookings(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports?date_to=2026-01-31T23:59:59Z")
        data = resp.json()
        assert data["total_bookings"] >= 1
        assert data["confirmed_revenue"] >= 5_000

    async def test_date_range_with_no_bookings_returns_zeros(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports?date_from=2020-01-01T00:00:00Z&date_to=2020-01-02T00:00:00Z"
        )
        data = resp.json()
        assert data["total_bookings"] == 0
        assert data["total_revenue"] == 0
        assert data["monthly_revenue"] == []

    async def test_date_filters_echoed_in_response(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports?date_from=2026-03-01T00:00:00Z&date_to=2026-03-31T23:59:59Z"
        )
        data = resp.json()
        assert data["date_from"] is not None
        assert data["date_to"] is not None

    async def test_no_filters_date_fields_are_null(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports")
        data = resp.json()
        assert data["date_from"] is None
        assert data["date_to"] is None

    async def test_invalid_date_format_returns_422(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/reports?date_from=not-a-date")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/reports/routes
# ══════════════════════════════════════════════════════════════════════════════
class TestGetRouteReport:
    async def test_admin_can_access_route_report(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports/routes")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_route_report(self, passenger_client: AsyncClient):
        resp = await passenger_client.get("/api/v1/admin/reports/routes")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_route_report(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/reports/routes")
        assert resp.status_code == 401

    async def test_route_report_has_correct_fields(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports/routes")
        data = resp.json()
        assert "routes" in data
        assert "date_from" in data
        assert "date_to" in data
        assert isinstance(data["routes"], list)

    async def test_route_report_points_have_correct_shape(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports/routes")
        data = resp.json()
        if data["routes"]:
            point = data["routes"][0]
            assert "route" in point
            assert "bookings" in point
            assert "revenue" in point

    async def test_route_report_contains_seeded_route(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports/routes")
        data = resp.json()
        routes = [r["route"] for r in data["routes"]]
        assert any("AD1" in r and "AD2" in r for r in routes)

    async def test_route_report_date_filter(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports/routes"
            "?date_from=2020-01-01T00:00:00Z"
            "&date_to=2020-01-02T00:00:00Z"
        )
        data = resp.json()
        assert data["routes"] == []

    async def test_route_report_invalid_date_returns_422(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/reports/routes?date_from=bad-date")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/reports/cancellations
# ══════════════════════════════════════════════════════════════════════════════
class TestGetCancellationReport:
    async def test_admin_can_access_cancellation_report(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports/cancellations")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_cancellation_report(self, passenger_client: AsyncClient):
        resp = await passenger_client.get("/api/v1/admin/reports/cancellations")
        assert resp.status_code == 403

    async def test_cancellation_report_has_correct_fields(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports/cancellations")
        data = resp.json()
        assert "monthly_cancellations" in data
        assert isinstance(data["monthly_cancellations"], list)

    async def test_cancellation_report_points_have_correct_shape(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get("/api/v1/admin/reports/cancellations")
        data = resp.json()
        if data["monthly_cancellations"]:
            point = data["monthly_cancellations"][0]
            assert "month" in point
            assert "year" in point
            assert "total_bookings" in point
            assert "cancelled_bookings" in point
            assert "cancellation_rate" in point

    async def test_cancellation_rate_is_correct(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports/cancellations"
            "?date_from=2026-03-01T00:00:00Z"
            "&date_to=2026-03-31T23:59:59Z"
        )
        data = resp.json()
        assert len(data["monthly_cancellations"]) == 1
        point = data["monthly_cancellations"][0]
        assert point["total_bookings"] == 2
        assert point["cancelled_bookings"] == 1
        assert point["cancellation_rate"] == 50.0

    async def test_cancellation_report_empty_range_returns_empty(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.get(
            "/api/v1/admin/reports/cancellations"
            "?date_from=2020-01-01T00:00:00Z"
            "&date_to=2020-01-02T00:00:00Z"
        )
        data = resp.json()
        assert data["monthly_cancellations"] == []

    async def test_cancellation_report_invalid_date_returns_422(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/reports/cancellations?date_from=bad-date")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/reports/user-growth
# ══════════════════════════════════════════════════════════════════════════════
class TestGetUserGrowthReport:
    async def test_admin_can_access_user_growth_report(self, admin_client: AsyncClient, seed_users):
        resp = await admin_client.get("/api/v1/admin/reports/user-growth")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_user_growth_report(self, passenger_client: AsyncClient):
        resp = await passenger_client.get("/api/v1/admin/reports/user-growth")
        assert resp.status_code == 403

    async def test_user_growth_report_has_correct_fields(
        self, admin_client: AsyncClient, seed_users
    ):
        resp = await admin_client.get("/api/v1/admin/reports/user-growth")
        data = resp.json()
        assert "monthly_growth" in data
        assert isinstance(data["monthly_growth"], list)

    async def test_user_growth_points_have_correct_shape(
        self, admin_client: AsyncClient, seed_users
    ):
        resp = await admin_client.get("/api/v1/admin/reports/user-growth")
        data = resp.json()
        if data["monthly_growth"]:
            point = data["monthly_growth"][0]
            assert "month" in point
            assert "year" in point
            assert "new_users" in point

    async def test_user_growth_counts_seeded_users(self, admin_client: AsyncClient, seed_users):
        resp = await admin_client.get("/api/v1/admin/reports/user-growth")
        data = resp.json()
        total = sum(p["new_users"] for p in data["monthly_growth"])
        assert total >= 2  # at least admin + passenger seeded

    async def test_user_growth_empty_range_returns_empty(self, admin_client: AsyncClient):
        resp = await admin_client.get(
            "/api/v1/admin/reports/user-growth"
            "?date_from=2000-01-01T00:00:00Z"
            "&date_to=2000-01-02T00:00:00Z"
        )
        data = resp.json()
        assert data["monthly_growth"] == []

    async def test_user_growth_invalid_date_returns_422(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/reports/user-growth?date_from=bad-date")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/activity-logs
# ══════════════════════════════════════════════════════════════════════════════
class TestGetActivityLogs:
    async def test_admin_can_access_activity_logs(
        self, admin_client: AsyncClient, seed_login_attempts
    ):
        resp = await admin_client.get("/api/v1/admin/activity-logs")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_activity_logs(self, passenger_client: AsyncClient):
        resp = await passenger_client.get("/api/v1/admin/activity-logs")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_activity_logs(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/activity-logs")
        assert resp.status_code == 401

    async def test_activity_logs_has_correct_fields(
        self, admin_client: AsyncClient, seed_login_attempts
    ):
        resp = await admin_client.get("/api/v1/admin/activity-logs")
        data = resp.json()
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)
        assert isinstance(data["total"], int)

    async def test_activity_log_entries_have_correct_shape(
        self, admin_client: AsyncClient, seed_login_attempts
    ):
        resp = await admin_client.get("/api/v1/admin/activity-logs")
        data = resp.json()
        if data["logs"]:
            log = data["logs"][0]
            assert "id" in log
            assert "email" in log
            assert "attempted_at" in log

    async def test_activity_logs_pagination(self, admin_client: AsyncClient, seed_login_attempts):
        resp = await admin_client.get("/api/v1/admin/activity-logs?page=1&size=1")
        data = resp.json()
        assert len(data["logs"]) <= 1

    async def test_activity_logs_search_by_email(
        self, admin_client: AsyncClient, seed_login_attempts
    ):
        resp = await admin_client.get("/api/v1/admin/activity-logs?search=unknown@test.com")
        data = resp.json()
        assert all("unknown" in log["email"] for log in data["logs"])

    async def test_activity_logs_date_filter(self, admin_client: AsyncClient, seed_login_attempts):
        resp = await admin_client.get(
            "/api/v1/admin/activity-logs"
            "?date_from=2026-04-01T00:00:00Z"
            "&date_to=2026-04-30T23:59:59Z"
        )
        data = resp.json()
        assert data["total"] >= 2

    async def test_activity_logs_empty_range(self, admin_client: AsyncClient, seed_login_attempts):
        resp = await admin_client.get(
            "/api/v1/admin/activity-logs"
            "?date_from=2000-01-01T00:00:00Z"
            "&date_to=2000-01-02T00:00:00Z"
        )
        data = resp.json()
        assert data["total"] == 0
        assert data["logs"] == []

    async def test_activity_logs_invalid_date_returns_422(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/activity-logs?date_from=bad-date")
        assert resp.status_code == 422

    async def test_activity_logs_invalid_page_returns_422(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/activity-logs?page=0")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/airports/public
# ══════════════════════════════════════════════════════════════════════════════
class TestPublicAirportEndpoints:
    async def test_public_list_airports_no_auth_required(self, unauthenticated_client: AsyncClient):
        resp = await unauthenticated_client.get("/api/v1/admin/airports/public")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_public_get_airport_by_iata(
        self, unauthenticated_client: AsyncClient, seed_admin_report_data
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/airports/public/AD1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["iata_code"] == "AD1"

    async def test_public_get_nonexistent_iata_returns_404(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/airports/public/ZZZ")
        assert resp.status_code == 404


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

    async def test_admin_can_create_airport_with_optional_fields(self, admin_client: AsyncClient):
        payload = {
            "iata_code": "OPT",
            "name": "Optional Airport",
            "city": "Opt City",
            "country": "Philippines",
            "timezone": "Asia/Manila",
            "about": "A great airport.",
            "highlights": ["Modern terminal", "Fast wifi"],
            "best_time": "November to April",
            "image_url": "https://example.com/airport.jpg",
        }
        resp = await admin_client.post("/api/v1/admin/airports", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["about"] == "A great airport."
        assert data["highlights"] == ["Modern terminal", "Fast wifi"]
        assert data["image_url"] == "https://example.com/airport.jpg"

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
        created = await admin_client.post(
            "/api/v1/admin/airports",
            json={
                "iata_code": "UPD",
                "name": "Old Airport",
                "city": "Old City",
                "country": "PH",
                "timezone": "Asia/Manila",
            },
        )
        airport_id = created.json()["id"]
        updated = await admin_client.put(
            f"/api/v1/admin/airports/{airport_id}",
            json={"name": "Updated Airport", "city": "Updated City"},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated Airport"

    async def test_admin_can_update_airport_image_url(self, admin_client: AsyncClient):
        created = await admin_client.post(
            "/api/v1/admin/airports",
            json={
                "iata_code": "IMG",
                "name": "Image Airport",
                "city": "City",
                "country": "PH",
                "timezone": "Asia/Manila",
            },
        )
        airport_id = created.json()["id"]
        updated = await admin_client.put(
            f"/api/v1/admin/airports/{airport_id}",
            json={"image_url": "https://example.com/new.jpg"},
        )
        assert updated.status_code == 200
        assert updated.json()["image_url"] == "https://example.com/new.jpg"

    async def test_admin_can_delete_unused_airport(self, admin_client: AsyncClient):
        created = await admin_client.post(
            "/api/v1/admin/airports",
            json={
                "iata_code": "DEL",
                "name": "Delete Airport",
                "city": "Delete City",
                "country": "PH",
                "timezone": "Asia/Manila",
            },
        )
        airport_id = created.json()["id"]
        deleted = await admin_client.delete(f"/api/v1/admin/airports/{airport_id}")
        assert deleted.status_code == 204

    async def test_delete_airport_used_by_flight_returns_409(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        airport_id = seed_admin_report_data["origin"].id
        resp = await admin_client.delete(f"/api/v1/admin/airports/{airport_id}")
        assert resp.status_code == 409

    async def test_update_nonexistent_airport_returns_404(self, admin_client: AsyncClient):
        resp = await admin_client.put(
            "/api/v1/admin/airports/999999",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_delete_nonexistent_airport_returns_404(self, admin_client: AsyncClient):
        resp = await admin_client.delete("/api/v1/admin/airports/999999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN AIRCRAFT CRUD
# ══════════════════════════════════════════════════════════════════════════════
class TestAdminAircraftCRUD:
    async def test_admin_can_list_aircraft(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/aircraft")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_passenger_cannot_list_aircraft(self, passenger_client: AsyncClient):
        resp = await passenger_client.get("/api/v1/admin/aircraft")
        assert resp.status_code == 403

    async def test_admin_can_create_aircraft(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        payload = {
            "model": "Airbus A321",
            "registration": "RP-TST01",
            "seat_configurations": [
                {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 10},
            ],
        }
        resp = await admin_client.post("/api/v1/admin/aircraft", json=payload)
        assert resp.status_code == 201
        assert resp.json()["registration"] == "RP-TST01"

    async def test_aircraft_response_includes_seats(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        payload = {
            "model": "ATR Check",
            "registration": "RP-CHK01",
            "seat_configurations": [
                {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 5},
            ],
        }
        resp = await admin_client.post("/api/v1/admin/aircraft", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "seats" in data
        assert len(data["seats"]) == 5

    async def test_duplicate_aircraft_registration_returns_409(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        payload = {
            "model": "Boeing 777",
            "registration": "RP-DUP01",
            "seat_configurations": [
                {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 5},
            ],
        }
        first = await admin_client.post("/api/v1/admin/aircraft", json=payload)
        assert first.status_code == 201
        second = await admin_client.post("/api/v1/admin/aircraft", json=payload)
        assert second.status_code == 409

    async def test_admin_can_update_aircraft(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        created = await admin_client.post(
            "/api/v1/admin/aircraft",
            json={
                "model": "ATR 72",
                "registration": "RP-UPD01",
                "seat_configurations": [
                    {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 5},
                ],
            },
        )
        aircraft_id = created.json()["id"]
        updated = await admin_client.put(
            f"/api/v1/admin/aircraft/{aircraft_id}",
            json={"model": "ATR 72-600"},
        )
        assert updated.status_code == 200
        assert updated.json()["model"] == "ATR 72-600"

    async def test_admin_can_delete_unused_aircraft(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        created = await admin_client.post(
            "/api/v1/admin/aircraft",
            json={
                "model": "Delete Aircraft",
                "registration": "RP-DEL01",
                "seat_configurations": [
                    {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 3},
                ],
            },
        )
        aircraft_id = created.json()["id"]
        resp = await admin_client.delete(f"/api/v1/admin/aircraft/{aircraft_id}")
        assert resp.status_code == 204

    async def test_delete_aircraft_used_by_flight_returns_409(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.delete(
            f"/api/v1/admin/aircraft/{seed_admin_report_data['aircraft'].id}"
        )
        assert resp.status_code == 409

    async def test_update_nonexistent_aircraft_returns_404(self, admin_client: AsyncClient):
        resp = await admin_client.put(
            "/api/v1/admin/aircraft/999999",
            json={"model": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_delete_nonexistent_aircraft_returns_404(self, admin_client: AsyncClient):
        resp = await admin_client.delete("/api/v1/admin/aircraft/999999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN SEAT CLASS CRUD
# ══════════════════════════════════════════════════════════════════════════════
class TestAdminSeatClassCRUD:
    async def test_admin_can_list_seat_classes(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/admin/seat-classes")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_passenger_cannot_list_seat_classes(self, passenger_client: AsyncClient):
        resp = await passenger_client.get("/api/v1/admin/seat-classes")
        assert resp.status_code == 403

    async def test_admin_can_create_seat_class(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json={"name": f"PremiumEconomy-{uuid.uuid4().hex[:4]}"},
        )
        assert resp.status_code == 201
        assert "name" in resp.json()

    async def test_duplicate_seat_class_name_returns_409(self, admin_client: AsyncClient):
        name = f"DupClass-{uuid.uuid4().hex[:4]}"
        first = await admin_client.post("/api/v1/admin/seat-classes", json={"name": name})
        assert first.status_code == 201
        second = await admin_client.post("/api/v1/admin/seat-classes", json={"name": name})
        assert second.status_code == 409

    async def test_admin_can_update_seat_class(self, admin_client: AsyncClient):
        created = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json={"name": f"UpdClass-{uuid.uuid4().hex[:4]}"},
        )
        seat_class_id = created.json()["id"]
        new_name = f"Updated-{uuid.uuid4().hex[:4]}"
        updated = await admin_client.put(
            f"/api/v1/admin/seat-classes/{seat_class_id}",
            json={"name": new_name},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == new_name

    async def test_admin_can_delete_unused_seat_class(self, admin_client: AsyncClient):
        created = await admin_client.post(
            "/api/v1/admin/seat-classes",
            json={"name": f"DelClass-{uuid.uuid4().hex[:4]}"},
        )
        seat_class_id = created.json()["id"]
        resp = await admin_client.delete(f"/api/v1/admin/seat-classes/{seat_class_id}")
        assert resp.status_code == 204

    async def test_delete_seat_class_used_by_booking_returns_409(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        resp = await admin_client.delete(
            f"/api/v1/admin/seat-classes/{seed_admin_report_data['seat_class'].id}"
        )
        assert resp.status_code == 409

    async def test_update_nonexistent_seat_class_returns_404(self, admin_client: AsyncClient):
        resp = await admin_client.put(
            "/api/v1/admin/seat-classes/999999",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_delete_nonexistent_seat_class_returns_404(self, admin_client: AsyncClient):
        resp = await admin_client.delete("/api/v1/admin/seat-classes/999999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN AIRCRAFT SEATS
# ══════════════════════════════════════════════════════════════════════════════
class TestAdminAircraftSeats:
    async def test_admin_can_list_aircraft_seats(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        aircraft_id = seed_admin_report_data["aircraft"].id
        resp = await admin_client.get(f"/api/v1/admin/aircraft/{aircraft_id}/seats")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_passenger_cannot_list_aircraft_seats(
        self, passenger_client: AsyncClient, seed_admin_report_data
    ):
        aircraft_id = seed_admin_report_data["aircraft"].id
        resp = await passenger_client.get(f"/api/v1/admin/aircraft/{aircraft_id}/seats")
        assert resp.status_code == 403

    async def test_admin_can_add_seats_to_aircraft(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        created = await admin_client.post(
            "/api/v1/admin/aircraft",
            json={
                "model": "Seat Test AC",
                "registration": f"RP-ST{uuid.uuid4().hex[:4].upper()}",
                "seat_configurations": [
                    {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 2},
                ],
            },
        )
        aircraft_id = created.json()["id"]
        resp = await admin_client.post(
            f"/api/v1/admin/aircraft/{aircraft_id}/seats",
            json=[
                {"seat_class_id": seed_admin_report_data["seat_class"].id, "seat_number": "99A"},
                {"seat_class_id": seed_admin_report_data["seat_class"].id, "seat_number": "99B"},
            ],
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 2

    async def test_add_duplicate_seat_number_returns_409(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        created = await admin_client.post(
            "/api/v1/admin/aircraft",
            json={
                "model": "Dup Seat AC",
                "registration": f"RP-DS{uuid.uuid4().hex[:4].upper()}",
                "seat_configurations": [
                    {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 1},
                ],
            },
        )
        aircraft_id = created.json()["id"]
        await admin_client.post(
            f"/api/v1/admin/aircraft/{aircraft_id}/seats",
            json=[
                {"seat_class_id": seed_admin_report_data["seat_class"].id, "seat_number": "DUP1"}
            ],
        )
        resp = await admin_client.post(
            f"/api/v1/admin/aircraft/{aircraft_id}/seats",
            json=[
                {"seat_class_id": seed_admin_report_data["seat_class"].id, "seat_number": "DUP1"}
            ],
        )
        assert resp.status_code == 409

    async def test_admin_can_delete_aircraft_seat(
        self, admin_client: AsyncClient, seed_admin_report_data
    ):
        created_ac = await admin_client.post(
            "/api/v1/admin/aircraft",
            json={
                "model": "Del Seat AC",
                "registration": f"RP-DL{uuid.uuid4().hex[:4].upper()}",
                "seat_configurations": [
                    {"seat_class_id": seed_admin_report_data["seat_class"].id, "quantity": 1},
                ],
            },
        )
        aircraft_id = created_ac.json()["id"]
        seats_resp = await admin_client.post(
            f"/api/v1/admin/aircraft/{aircraft_id}/seats",
            json=[{"seat_class_id": seed_admin_report_data["seat_class"].id, "seat_number": "X1"}],
        )
        seat_id = seats_resp.json()[0]["id"]
        resp = await admin_client.delete(f"/api/v1/admin/aircraft/seats/{seat_id}")
        assert resp.status_code == 204

    async def test_delete_nonexistent_seat_returns_404(self, admin_client: AsyncClient):
        resp = await admin_client.delete("/api/v1/admin/aircraft/seats/999999")
        assert resp.status_code == 404
