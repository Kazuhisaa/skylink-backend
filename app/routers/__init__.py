from app.routers.admin.aircraft import router as admin_aircraft_router
from app.routers.admin.airports import router as admin_airports_router
from app.routers.admin.bookings import router as admin_bookings_router
from app.routers.admin.dashboard import router as admin_dashboard_router
from app.routers.admin.flights import router as admin_flights_router
from app.routers.admin.ml import router as admin_ml_router
from app.routers.admin.promotions import router as admin_promotions_router
from app.routers.admin.reports import router as admin_reports_router
from app.routers.admin.users import router as admin_users_router
from app.routers.airports import router as airports_router
from app.routers.auth import router as auth_router
from app.routers.bookings import router as bookings_router
from app.routers.flights import router as flights_router
from app.routers.payments import router as payments_router
from app.routers.promotions import router as promotions_router
from app.routers.users import router as users_router

routers = [
    admin_dashboard_router,
    admin_reports_router,
    admin_airports_router,
    admin_aircraft_router,
    admin_flights_router,
    admin_bookings_router,
    admin_promotions_router,
    admin_ml_router,
    auth_router,
    airports_router,
    flights_router,
    bookings_router,
    promotions_router,
    payments_router,
    users_router,
    admin_users_router,
]
