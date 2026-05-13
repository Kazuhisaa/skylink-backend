from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.auth.dependencies import require_admin
from app.schemas.admin import BookingReportRead
from app.services import admin_service
from app.core.limiter import limiter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/reports", response_model=BookingReportRead, dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_booking_report(
    request: Request,
    date_from: Optional[datetime] = Query(None, description="Filter from date e.g. 2026-05-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="Filter to date e.g. 2026-05-31T23:59:59Z"),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_booking_report(db, date_from, date_to)


