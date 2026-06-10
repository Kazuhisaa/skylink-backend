from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.core.limiter import limiter
from app.database import get_db
from app.services.admin import dashboard_service

router = APIRouter(prefix="/admin", tags=["Admin - Dashboard"])


@router.get("/kpi", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_kpi(request: Request, db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_kpi_summary(db)


@router.get("/kpi/revenue-by-route", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def get_revenue_by_route(request: Request, db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_revenue_by_route(db)
