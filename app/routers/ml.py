from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.dependencies import require_admin
from app.schemas.ml import RevenueForecastRead
from app.services import ml_service
from app.core.limiter import limiter

router = APIRouter(prefix="/admin/ml", tags=["ML Analytics"])

# ─── Revenue Forecast ─────────────────────────────────────────────────────────

@router.get("/revenue-forecast", response_model=RevenueForecastRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_revenue_forecast(
    request: Request,
    months_ahead: int = Query(6, ge=3, le=12, description="Number of months to forecast (3–12)"),
    db: AsyncSession = Depends(get_db),
):
    return await ml_service.get_revenue_forecast(db, months_ahead)


@router.get("/demand-forecast", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_demand_forecast(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await ml_service.get_demand_forecast(db)


@router.get("/cancellation-risk/{booking_id}", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_cancellation_risk(
    request: Request,
    booking_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await ml_service.get_cancellation_risk(db, booking_id)


@router.get("/revenue-anomalies", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_revenue_anomalies(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await ml_service.get_revenue_anomalies(db)


@router.get("/pricing-suggestion/{flight_id}", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_pricing_suggestion(
    request: Request,
    flight_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await ml_service.get_pricing_suggestion(db, flight_id)
    return result