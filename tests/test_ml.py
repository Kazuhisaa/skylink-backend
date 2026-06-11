import uuid
from datetime import datetime, timezone

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.bookings import Booking
from app.models.flights import Aircraft, Airport, Flight, FlightSeatPricing, SeatClass

# ══════════════════════════════════════════════════════════════════════════════
# SEED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_ml_data(test_session_factory, seed_users):
    admin_user = seed_users["admin"]

    origin_code = f"M{uuid.uuid4().hex[:2].upper()}"
    destination_code = f"C{uuid.uuid4().hex[:2].upper()}"

    origin = Airport(
        iata_code=origin_code,
        name="Ninoy Aquino International Airport",
        city="Manila",
        country="Philippines",
        timezone="Asia/Manila",
    )
    destination = Airport(
        iata_code=destination_code,
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
        departure_time=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
        arrival_time=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        status="scheduled",
        created_by=admin_user.id,
    )

    # Spread bookings across multiple months to give the ML models enough data
    bookings = []
    months = [
        (2025, 7),
        (2025, 8),
        (2025, 9),
        (2025, 10),
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
        (2026, 3),
        (2026, 4),
        (2026, 5),
        (2026, 6),
    ]
    for year, month in months:
        for _ in range(3):
            bookings.append(
                Booking(
                    id=uuid.uuid4(),
                    user_id=admin_user.id,
                    seat_number=f"{uuid.uuid4().hex[:2].upper()}",
                    status="confirmed",
                    total_price=5000 + (month * 100),
                    booked_at=datetime(year, month, 10, 12, 0, tzinfo=timezone.utc),
                )
            )

    # One cancelled booking for cancellation risk training data
    cancelled_booking = Booking(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        seat_number="ZZ",
        status="cancelled",
        total_price=3000,
        booked_at=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
    )
    bookings.append(cancelled_booking)

    # A target booking to score cancellation risk against
    target_booking = Booking(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        seat_number="1A",
        status="confirmed",
        total_price=8000,
        booked_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
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

            pricing = FlightSeatPricing(
                flight_id=flight.id,
                seat_class_id=seat_class.id,
                total_seats=100,
                available_seats=40,
                price=5000,
            )
            session.add(pricing)

            for b in bookings:
                b.flight_id = flight.id
                b.seat_class_id = seat_class.id
            target_booking.flight_id = flight.id
            target_booking.seat_class_id = seat_class.id

            session.add_all(bookings)
            session.add(target_booking)

    yield {
        "flight": flight,
        "seat_class": seat_class,
        "aircraft": aircraft,
        "origin": origin,
        "destination": destination,
        "origin_code": origin_code,
        "destination_code": destination_code,
        "bookings": bookings,
        "target_booking": target_booking,
        "admin_user": admin_user,
    }

    all_booking_ids = [b.id for b in bookings] + [target_booking.id]
    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(delete(Booking).where(Booking.id.in_(all_booking_ids)))
            await session.execute(
                delete(FlightSeatPricing).where(FlightSeatPricing.flight_id == flight.id)
            )
            await session.execute(delete(Flight).where(Flight.id == flight.id))
            await session.execute(delete(SeatClass).where(SeatClass.id == seat_class.id))
            await session.execute(delete(Aircraft).where(Aircraft.id == aircraft.id))
            await session.execute(
                delete(Airport).where(Airport.id.in_([origin.id, destination.id]))
            )


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/ml/revenue-forecast
# ══════════════════════════════════════════════════════════════════════════════


class TestRevenueForecast:
    async def test_admin_can_access_revenue_forecast(self, admin_client: AsyncClient, seed_ml_data):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_revenue_forecast(
        self, passenger_client: AsyncClient, seed_ml_data
    ):
        resp = await passenger_client.get("/api/v1/admin/ml/revenue-forecast")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_revenue_forecast(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/ml/revenue-forecast")
        assert resp.status_code == 401

    async def test_revenue_forecast_has_correct_fields(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        data = resp.json()
        assert "historical" in data
        assert "forecast" in data
        assert "r2_score" in data
        assert "confidence" in data

    async def test_revenue_forecast_historical_and_forecast_are_lists(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        data = resp.json()
        assert isinstance(data["historical"], list)
        assert isinstance(data["forecast"], list)

    async def test_revenue_forecast_points_have_correct_shape(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        data = resp.json()
        if data["historical"]:
            point = data["historical"][0]
            assert "month" in point
            assert "year" in point
            assert "revenue" in point
        if data["forecast"]:
            point = data["forecast"][0]
            assert "month" in point
            assert "year" in point
            assert "revenue" in point

    async def test_revenue_forecast_default_months_ahead_is_6(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        data = resp.json()
        assert len(data["forecast"]) == 6

    async def test_revenue_forecast_custom_months_ahead(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast?months_ahead=9")
        data = resp.json()
        assert len(data["forecast"]) == 9

    async def test_revenue_forecast_months_ahead_min_is_3(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast?months_ahead=2")
        assert resp.status_code == 422

    async def test_revenue_forecast_months_ahead_max_is_12(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast?months_ahead=13")
        assert resp.status_code == 422

    async def test_revenue_forecast_r2_score_is_float(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        data = resp.json()
        if data["r2_score"] is not None:
            assert isinstance(data["r2_score"], float)

    async def test_revenue_forecast_confidence_is_valid_value(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        data = resp.json()
        if data["confidence"] is not None:
            assert data["confidence"] in ("low", "medium", "high")

    async def test_revenue_forecast_values_are_non_negative(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-forecast")
        data = resp.json()
        for point in data["forecast"]:
            assert point["revenue"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/ml/demand-forecast
# ══════════════════════════════════════════════════════════════════════════════


class TestDemandForecast:
    async def test_admin_can_access_demand_forecast(self, admin_client: AsyncClient, seed_ml_data):
        resp = await admin_client.get("/api/v1/admin/ml/demand-forecast")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_demand_forecast(
        self, passenger_client: AsyncClient, seed_ml_data
    ):
        resp = await passenger_client.get("/api/v1/admin/ml/demand-forecast")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_demand_forecast(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/ml/demand-forecast")
        assert resp.status_code == 401

    async def test_demand_forecast_has_routes_field(self, admin_client: AsyncClient, seed_ml_data):
        resp = await admin_client.get("/api/v1/admin/ml/demand-forecast")
        data = resp.json()
        assert "routes" in data
        assert isinstance(data["routes"], list)

    async def test_demand_forecast_route_points_have_correct_shape(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/demand-forecast")
        data = resp.json()
        if data["routes"]:
            route = data["routes"][0]
            assert "route" in route
            assert "predicted_bookings_next_30_days" in route
            assert "avg_monthly_bookings" in route
            assert "r2_score" in route
            assert "confidence" in route

    async def test_demand_forecast_contains_seeded_route(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        origin_code = seed_ml_data["origin"].iata_code
        destination_code = seed_ml_data["destination"].iata_code
        resp = await admin_client.get("/api/v1/admin/ml/demand-forecast")
        data = resp.json()
        routes = [r["route"] for r in data["routes"]]
        assert any(origin_code in r and destination_code in r for r in routes)

    async def test_demand_forecast_predicted_bookings_are_non_negative(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/demand-forecast")
        data = resp.json()
        for route in data["routes"]:
            assert route["predicted_bookings_next_30_days"] >= 0

    async def test_demand_forecast_confidence_is_valid_value(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/demand-forecast")
        data = resp.json()
        for route in data["routes"]:
            assert route["confidence"] in ("low", "medium", "high")

    async def test_demand_forecast_sorted_by_predicted_bookings_desc(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/demand-forecast")
        data = resp.json()
        predicted = [r["predicted_bookings_next_30_days"] for r in data["routes"]]
        assert predicted == sorted(predicted, reverse=True)


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/ml/cancellation-risk/{booking_id}
# ══════════════════════════════════════════════════════════════════════════════


class TestCancellationRisk:
    async def test_admin_can_access_cancellation_risk(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_cancellation_risk(
        self, passenger_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await passenger_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_cancellation_risk(
        self, unauthenticated_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await unauthenticated_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        assert resp.status_code == 401

    async def test_cancellation_risk_has_correct_fields(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        data = resp.json()
        assert "booking_id" in data
        assert "risk_score" in data
        assert "risk_level" in data
        assert "confidence" in data

    async def test_cancellation_risk_booking_id_matches(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        data = resp.json()
        assert str(data["booking_id"]) == str(booking_id)

    async def test_cancellation_risk_score_is_between_0_and_100(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        data = resp.json()
        if data["risk_score"] is not None:
            assert 0 <= data["risk_score"] <= 100

    async def test_cancellation_risk_level_is_valid_value(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        data = resp.json()
        assert data["risk_level"] in ("low", "medium", "high", "unknown")

    async def test_cancellation_risk_nonexistent_booking_returns_404(
        self, admin_client: AsyncClient
    ):
        fake_id = uuid.uuid4()
        resp = await admin_client.get(f"/api/v1/admin/ml/cancellation-risk/{fake_id}")
        assert resp.status_code == 404

    async def test_cancellation_risk_includes_route_when_scored(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        booking_id = seed_ml_data["target_booking"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/cancellation-risk/{booking_id}")
        data = resp.json()
        # When enough history exists, route and lead_time_days are included
        if data["risk_level"] != "unknown":
            assert "route" in data
            assert "lead_time_days" in data
            assert data["lead_time_days"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/ml/revenue-anomalies
# ══════════════════════════════════════════════════════════════════════════════


class TestRevenueAnomalies:
    async def test_admin_can_access_revenue_anomalies(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-anomalies")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_revenue_anomalies(
        self, passenger_client: AsyncClient, seed_ml_data
    ):
        resp = await passenger_client.get("/api/v1/admin/ml/revenue-anomalies")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_revenue_anomalies(
        self, unauthenticated_client: AsyncClient
    ):
        resp = await unauthenticated_client.get("/api/v1/admin/ml/revenue-anomalies")
        assert resp.status_code == 401

    async def test_revenue_anomalies_has_correct_fields(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-anomalies")
        data = resp.json()
        assert "monthly" in data
        assert "anomalies" in data
        assert "mean_revenue" in data
        assert "std_revenue" in data

    async def test_revenue_anomalies_monthly_is_list(self, admin_client: AsyncClient, seed_ml_data):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-anomalies")
        data = resp.json()
        assert isinstance(data["monthly"], list)
        assert isinstance(data["anomalies"], list)

    async def test_revenue_anomalies_monthly_points_have_correct_shape(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-anomalies")
        data = resp.json()
        if data["monthly"]:
            point = data["monthly"][0]
            assert "month" in point
            assert "year" in point
            assert "revenue" in point
            assert "z_score" in point
            assert "is_anomaly" in point
            assert "severity" in point

    async def test_revenue_anomalies_is_anomaly_matches_severity(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-anomalies")
        data = resp.json()
        for point in data["monthly"]:
            if point["is_anomaly"]:
                assert point["severity"] in ("warning", "critical")
            else:
                assert point["severity"] is None

    async def test_revenue_anomalies_anomaly_list_is_subset_of_monthly(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-anomalies")
        data = resp.json()
        anomaly_months = {(a["month"], a["year"]) for a in data["anomalies"]}
        monthly_anomaly_months = {
            (p["month"], p["year"]) for p in data["monthly"] if p["is_anomaly"]
        }
        assert anomaly_months == monthly_anomaly_months

    async def test_revenue_anomalies_mean_and_std_are_numbers(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        resp = await admin_client.get("/api/v1/admin/ml/revenue-anomalies")
        data = resp.json()
        assert isinstance(data["mean_revenue"], (int, float))
        assert isinstance(data["std_revenue"], (int, float))
        assert data["std_revenue"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/ml/pricing-suggestion/{flight_id}
# ══════════════════════════════════════════════════════════════════════════════


class TestPricingSuggestion:
    async def test_admin_can_access_pricing_suggestion(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        assert resp.status_code == 200

    async def test_passenger_cannot_access_pricing_suggestion(
        self, passenger_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await passenger_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_pricing_suggestion(
        self, unauthenticated_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await unauthenticated_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        assert resp.status_code == 401

    async def test_pricing_suggestion_has_correct_fields(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        data = resp.json()
        assert "flight_id" in data
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    async def test_pricing_suggestion_flight_id_matches(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        data = resp.json()
        assert str(data["flight_id"]) == str(flight_id)

    async def test_pricing_suggestion_items_have_correct_shape(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        data = resp.json()
        assert len(data["suggestions"]) >= 1
        item = data["suggestions"][0]
        assert "seat_class_id" in item
        assert "seat_class_name" in item
        assert "current_price" in item
        assert "suggested_price" in item
        assert "adjustment_pct" in item
        assert "occupancy_rate" in item
        assert "available_seats" in item
        assert "total_seats" in item
        assert "days_until_departure" in item
        assert "reason" in item

    async def test_pricing_suggestion_suggested_price_is_non_negative(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        data = resp.json()
        for item in data["suggestions"]:
            assert item["suggested_price"] >= 0

    async def test_pricing_suggestion_occupancy_rate_between_0_and_100(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        data = resp.json()
        for item in data["suggestions"]:
            assert 0 <= item["occupancy_rate"] <= 100

    async def test_pricing_suggestion_nonexistent_flight_returns_404(
        self, admin_client: AsyncClient
    ):
        fake_id = uuid.uuid4()
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{fake_id}")
        assert resp.status_code == 404

    async def test_pricing_suggestion_days_until_departure_is_non_negative(
        self, admin_client: AsyncClient, seed_ml_data
    ):
        flight_id = seed_ml_data["flight"].id
        resp = await admin_client.get(f"/api/v1/admin/ml/pricing-suggestion/{flight_id}")
        data = resp.json()
        for item in data["suggestions"]:
            assert item["days_until_departure"] >= 0
