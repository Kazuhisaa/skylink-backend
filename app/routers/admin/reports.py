from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.schemas.admin.reports import (
    ActivityLogListRead,
    BookingReportRead,
    CancellationReportRead,
    RouteReportRead,
    UserGrowthReportRead,
)
from app.services.admin import reports_service

router = APIRouter(prefix="/admin", tags=["Admin - Reports"])


@router.get("/reports", response_model=BookingReportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_booking_report(
    request: Request,
    date_from: Optional[datetime] = Query(
        None, description="Filter from date e.g. 2026-05-01T00:00:00Z"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter to date e.g. 2026-05-31T23:59:59Z"
    ),
    db: AsyncSession = Depends(get_db),
):
    return await reports_service.get_booking_report(db, date_from, date_to)


@router.get(
    "/reports/routes", response_model=RouteReportRead, dependencies=[Depends(require_admin)]
)
@limiter.limit("30/minute")
async def get_route_report(
    request: Request,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await reports_service.get_route_report(db, date_from, date_to)


# ─── Cancellation Report ──────────────────────────────────────────────────────────────────
@router.get(
    "/reports/cancellations",
    response_model=CancellationReportRead,
    dependencies=[Depends(require_admin)],
)
@limiter.limit("30/minute")
async def get_cancellation_report(
    request: Request,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await reports_service.get_cancellation_report(db, date_from, date_to)


# ─── User Growth ──────────────────────────────────────────────────────────────────
@router.get(
    "/reports/user-growth",
    response_model=UserGrowthReportRead,
    dependencies=[Depends(require_admin)],
)
@limiter.limit("30/minute")
async def get_user_growth_report(
    request: Request,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await reports_service.get_user_growth_report(db, date_from, date_to)


@router.get(
    "/activity-logs", response_model=ActivityLogListRead, dependencies=[Depends(require_admin)]
)
@limiter.limit("30/minute")
async def get_activity_logs(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(8, ge=1, le=100),
    search: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await reports_service.get_activity_logs(db, page, size, search, date_from, date_to)
