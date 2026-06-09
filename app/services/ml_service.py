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

    model = LinearRegression()
    model.fit(months_numeric, revenues)

    historical = [
        {
            "month": r.month.strftime("%b"),
            "year": r.month.year,
            "revenue": float(r.revenue),
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

    r2 = float(model.score(months_numeric, revenues))
    logger.info(f"[ML] Revenue forecast generated — r2={r2:.3f} months_ahead={months_ahead}")

    return {
        "historical": historical,
        "forecast": forecast,
        "r2_score": round(r2, 4),
    }