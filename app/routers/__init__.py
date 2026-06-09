from app.routers.admin import router as admin_router
from app.routers.users import router as users_router
from app.routers.flights import router as flights_router
from app.routers.bookings import router as bookings_router
from app.routers.promotions import router as promotions_router
from app.routers.ml import router as ml_router
from app.routers.auth import router as auth_router

routers = [
    auth_router,
    admin_router,
    users_router,
    flights_router,
    bookings_router,
    promotions_router,
    ml_router,
]