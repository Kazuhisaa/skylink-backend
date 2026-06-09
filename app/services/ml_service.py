import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

# ─── Revenue Forecast ─────────────────────────────────────────────────────────

async def get_revenue_forecast(db: AsyncSession, months_ahead: int = 6) -> dict:
    query = text("""
        SELECT
            DATE_TRUNC('month', booked_at) AS month,
            SUM(total_price) AS revenue
        FROM bookings
        WHERE status != 'cancelled'
        GROUP BY month
        ORDER BY month
    """)

    result = await db.execute(query)
    rows = result.fetchall()

    if len(rows) < 2:
        logger.warning("[ML] Not enough data for revenue forecast")
        return {"historical": [], "forecast": [], "r2_score": None, "message": "Not enough data to forecast"}

    months_numeric = np.array(range(len(rows))).reshape(-1, 1)
    revenues = np.array([float(r.revenue) for r in rows])

    # Clip outliers beyond 2 std devs so spikes don't skew the trend line
    mean = np.mean(revenues)
    std = np.std(revenues)
    revenues_clipped = np.clip(revenues, mean - 2 * std, mean + 2 * std)

    model = LinearRegression()
    model.fit(months_numeric, revenues_clipped)

    historical = [
        {
            "month": r.month.strftime("%b"),
            "year": r.month.year,
            "revenue": float(r.revenue),  # always return real revenue in historical
        }
        for r in rows
    ]

    last_index = len(rows) - 1
    last_dt = rows[-1].month

    forecast = []
    for i in range(1, months_ahead + 1):
        month = (last_dt.month - 1 + i) % 12 + 1
        year = last_dt.year + (last_dt.month - 1 + i) // 12
        predicted = float(model.predict([[last_index + i]])[0])
        forecast.append({
            "month": datetime(year, month, 1).strftime("%b"),
            "year": year,
            "revenue": max(0.0, predicted),
        })

    r2 = float(model.score(months_numeric, revenues_clipped))

    if len(rows) < 6:
        confidence = "low"
    elif r2 < 0.5 or len(rows) < 12:
        confidence = "medium"
    else:
        confidence = "high"

    logger.info(f"[ML] Revenue forecast generated — r2={r2:.3f} confidence={confidence} months_ahead={months_ahead}")

    return {
        "historical": historical,
        "forecast": forecast,
        "r2_score": round(r2, 4),
        "confidence": confidence,
    }



# ─── Demand Forecast by Route ─────────────────────────────────────────────────

async def get_demand_forecast(db: AsyncSession) -> dict:
    query = text("""
        SELECT
            a1.iata_code AS origin,
            a2.iata_code AS destination,
            DATE_TRUNC('month', b.booked_at) AS month,
            COUNT(*) AS bookings
        FROM bookings b
        JOIN flights f ON f.id = b.flight_id
        JOIN airports a1 ON a1.id = f.origin_airport_id
        JOIN airports a2 ON a2.id = f.destination_airport_id
        WHERE b.status != 'cancelled'
        GROUP BY a1.iata_code, a2.iata_code, month
        ORDER BY a1.iata_code, a2.iata_code, month
    """)

    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        return {"routes": [], "message": "Not enough data"}

    from collections import defaultdict
    route_data: dict = defaultdict(list)
    for r in rows:
        route_key = f"{r.origin} → {r.destination}"
        route_data[route_key].append(float(r.bookings))

    routes = []
    for route, monthly_counts in route_data.items():
        if len(monthly_counts) < 2:
            continue

        x = np.array(range(len(monthly_counts))).reshape(-1, 1)
        y = np.array(monthly_counts)

        mean, std = np.mean(y), np.std(y)
        y_clipped = np.clip(y, mean - 2 * std, mean + 2 * std)

        model = LinearRegression()
        model.fit(x, y_clipped)

        next_index = len(monthly_counts)
        predicted = max(0.0, float(model.predict([[next_index]])[0]))
        r2 = float(model.score(x, y_clipped))

        if len(monthly_counts) < 6:
            confidence = "low"
        elif r2 < 0.5 or len(monthly_counts) < 12:
            confidence = "medium"
        else:
            confidence = "high"

        routes.append({
            "route": route,
            "predicted_bookings_next_30_days": round(predicted),
            "avg_monthly_bookings": round(float(np.mean(y)), 1),
            "r2_score": round(r2, 4),
            "confidence": confidence,
        })

    routes.sort(key=lambda x: x["predicted_bookings_next_30_days"], reverse=True)
    logger.info(f"[ML] Demand forecast generated — routes={len(routes)}")

    return {"routes": routes}



# ─── Cancellation Risk Scoring ────────────────────────────────────────────────

async def get_cancellation_risk(db: AsyncSession, booking_id: str) -> dict:
    # fetch the target booking
    booking_query = text("""
        SELECT
            b.id,
            b.status,
            b.seat_class_id,
            b.total_price,
            b.booked_at,
            f.departure_time,
            a1.iata_code AS origin,
            a2.iata_code AS destination
        FROM bookings b
        JOIN flights f ON f.id = b.flight_id
        JOIN airports a1 ON a1.id = f.origin_airport_id
        JOIN airports a2 ON a2.id = f.destination_airport_id
        WHERE b.id = :booking_id
    """)

    result = await db.execute(booking_query, {"booking_id": booking_id})
    booking = result.fetchone()

    if not booking:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Booking not found.")

    # fetch historical bookings for feature training
    history_query = text("""
        SELECT
            b.seat_class_id,
            b.total_price,
            b.booked_at,
            f.departure_time,
            a1.iata_code AS origin,
            a2.iata_code AS destination,
            CASE WHEN b.status = 'cancelled' THEN 1 ELSE 0 END AS is_cancelled
        FROM bookings b
        JOIN flights f ON f.id = b.flight_id
        JOIN airports a1 ON a1.id = f.origin_airport_id
        JOIN airports a2 ON a2.id = f.destination_airport_id
        WHERE b.id != :booking_id
    """)

    history_result = await db.execute(history_query, {"booking_id": booking_id})
    rows = history_result.fetchall()

    if len(rows) < 10:
        return {
            "booking_id": booking_id,
            "risk_score": None,
            "risk_level": "unknown",
            "confidence": "low",
            "message": "Not enough historical data to score risk.",
        }

    # build features
    def extract_features(row, booked_at, departure_time, origin, destination):
        lead_time = max(0, (departure_time - booked_at).days)
        return [
            row.seat_class_id,
            row.total_price,
            lead_time,
            1 if origin == 'MNL' else 0,
        ]

    X, y = [], []
    for row in rows:
        features = extract_features(
            row, row.booked_at, row.departure_time, row.origin, row.destination
        )
        X.append(features)
        y.append(row.is_cancelled)

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(np.array(X))

    model = LogisticRegression(max_iter=200)
    model.fit(X_scaled, y)

    # score the target booking
    lead_time = max(0, (booking.departure_time - booking.booked_at).days)
    target_features = np.array([[
        booking.seat_class_id,
        booking.total_price,
        lead_time,
        1 if booking.origin == 'MNL' else 0,
    ]])
    target_scaled = scaler.transform(target_features)
    risk_score = float(model.predict_proba(target_scaled)[0][1]) * 100

    if risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 35:
        risk_level = "medium"
    else:
        risk_level = "low"

    logger.info(f"[ML] Cancellation risk scored — booking={booking_id} score={risk_score:.1f}% level={risk_level}")

    return {
        "booking_id": booking_id,
        "risk_score": round(risk_score, 1),
        "risk_level": risk_level,
        "confidence": "medium",
        "lead_time_days": lead_time,
        "route": f"{booking.origin} → {booking.destination}",
    }



# ─── Anomaly Detection on Revenue ─────────────────────────────────────────────

async def get_revenue_anomalies(db: AsyncSession) -> dict:
    query = text("""
        SELECT
            DATE_TRUNC('month', booked_at) AS month,
            SUM(total_price) AS revenue
        FROM bookings
        WHERE status != 'cancelled'
        GROUP BY month
        ORDER BY month
    """)

    result = await db.execute(query)
    rows = result.fetchall()

    if len(rows) < 3:
        return {"anomalies": [], "monthly": [], "message": "Not enough data"}

    revenues = np.array([float(r.revenue) for r in rows])
    mean = np.mean(revenues)
    std = np.std(revenues)

    monthly = []
    anomalies = []

    for r in rows:
        revenue = float(r.revenue)
        z_score = (revenue - mean) / std if std > 0 else 0.0
        abs_z = abs(z_score)

        if abs_z >= 2.5:
            severity = "critical"
        elif abs_z >= 1.5:
            severity = "warning"
        else:
            severity = None

        point = {
            "month": r.month.strftime("%b"),
            "year": r.month.year,
            "revenue": revenue,
            "z_score": round(z_score, 3),
            "is_anomaly": severity is not None,
            "severity": severity,
        }
        monthly.append(point)

        if severity:
            anomalies.append(point)

    logger.info(f"[ML] Anomaly detection complete — total={len(monthly)} anomalies={len(anomalies)}")

    return {
        "monthly": monthly,
        "anomalies": anomalies,
        "mean_revenue": round(float(mean), 2),
        "std_revenue": round(float(std), 2),
    }



# ─── Seat Pricing Optimization ────────────────────────────────────────────────

async def get_pricing_suggestion(db: AsyncSession, flight_id: str) -> dict:

    # fetch flight + pricing info
    flight_query = text("""
        SELECT
            f.id,
            f.departure_time,
            f.created_at,
            fsp.seat_class_id,
            fsp.total_seats,
            fsp.available_seats,
            fsp.price,
            sc.name AS seat_class_name
        FROM flights f
        JOIN flight_seat_pricing fsp ON fsp.flight_id = f.id
        JOIN seat_classes sc ON sc.id = fsp.seat_class_id
        WHERE f.id = :flight_id
    """)

    result = await db.execute(flight_query, {"flight_id": flight_id})
    rows = result.fetchall()

    if not rows:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Flight not found.")

    # fetch historical booking velocity per seat class
    velocity_query = text("""
        SELECT
            b.seat_class_id,
            DATE_TRUNC('month', b.booked_at) AS month,
            COUNT(*) AS bookings
        FROM bookings b
        JOIN flights f ON f.id = b.flight_id
        WHERE b.status != 'cancelled'
        GROUP BY b.seat_class_id, month
        ORDER BY b.seat_class_id, month
    """)

    velocity_result = await db.execute(velocity_query)
    velocity_rows = velocity_result.fetchall()
    from collections import defaultdict
    velocity_map: dict = defaultdict(list)
    for v in velocity_rows:
        velocity_map[v.seat_class_id].append(float(v.bookings))

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    suggestions = []
    for row in rows:
        days_until_departure = max(0, (row.departure_time - now).days)
        occupancy_rate = (row.total_seats - row.available_seats) / row.total_seats if row.total_seats > 0 else 0
        avg_velocity = float(np.mean(velocity_map[row.seat_class_id])) if velocity_map[row.seat_class_id] else 0

        # pricing logic:
        # high occupancy + few days left = increase price
        # low occupancy + many days left = decrease to stimulate demand
        # low occupancy + few days left = decrease aggressively to fill seats
        if occupancy_rate >= 0.85 and days_until_departure <= 30:
            adjustment_pct = 15.0
            reason = "High occupancy and close departure — increase price"
        elif occupancy_rate >= 0.7:
            adjustment_pct = 8.0
            reason = "Good occupancy — moderate price increase"
        elif occupancy_rate <= 0.3 and days_until_departure <= 14:
            adjustment_pct = -20.0
            reason = "Low occupancy near departure — aggressive discount to fill seats"
        elif occupancy_rate <= 0.5 and days_until_departure > 30:
            adjustment_pct = -10.0
            reason = "Low occupancy with time remaining — stimulate early bookings"
        else:
            adjustment_pct = 0.0
            reason = "Occupancy is healthy — no adjustment needed"

        suggested_price = round(row.price * (1 + adjustment_pct / 100))

        suggestions.append({
            "seat_class_id": row.seat_class_id,
            "seat_class_name": row.seat_class_name,
            "current_price": row.price,
            "suggested_price": suggested_price,
            "adjustment_pct": adjustment_pct,
            "occupancy_rate": round(occupancy_rate * 100, 1),
            "available_seats": row.available_seats,
            "total_seats": row.total_seats,
            "days_until_departure": days_until_departure,
            "avg_monthly_booking_velocity": round(avg_velocity, 1),
            "reason": reason,
        })
    logger.info(f"[ML] Pricing suggestion generated — flight={flight_id} classes={len(suggestions)}")
    return {
        "flight_id": flight_id,
        "suggestions": suggestions,
    }