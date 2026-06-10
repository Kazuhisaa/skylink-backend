from app.routers.admin.dashboard import router as admin_dashboard_router
from app.routers.admin.reports import router as admin_reports_router
from app.routers.admin.airports import router as admin_airports_router
from app.routers.admin.aircraft import router as admin_aircraft_router
from app.routers.users import router as users_router
from app.routers.flights import router as flights_router
from app.routers.bookings import router as bookings_router
from app.routers.promotions import router as promotions_router
from app.routers.ml import router as ml_router
from app.routers.auth import router as auth_router
from app.routers.payments import router as payments_router

routers = [
    auth_router,
    admin_dashboard_router,
    admin_reports_router,
    admin_airports_router,
    admin_aircraft_router,
    users_router,
    flights_router,
    bookings_router,
    promotions_router,
    ml_router,
    payments_router,
]