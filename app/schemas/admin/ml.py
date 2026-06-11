from typing import Optional

from pydantic import BaseModel

# ─── Revenue Forecast ─────────────────────────────────────────────────────────


class RevenueForecastPoint(BaseModel):
    month: str
    year: int
    revenue: float


class RevenueForecastRead(BaseModel):
    historical: list[RevenueForecastPoint] = []
    forecast: list[RevenueForecastPoint] = []
    r2_score: Optional[float] = None
    confidence: Optional[str] = None
    message: Optional[str] = None
