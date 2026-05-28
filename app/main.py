from fastapi import FastAPI
from app.core.config import configure_middlewares, debug_mode
from app.core.limiter import configure_limiter
from app.core.redis import redis_client
import logging
import app.models  

from app.auth import router as authentications
from app.routers.admin import router as admin_router
from app.routers.users import router as users_router
from app.routers.flights import router as flights_router
from app.routers.bookings import router as bookings_router
from app.routers.promotions import router as promotions_router

from tests import test_health


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(**debug_mode())

@app.on_event("startup")
async def startup_event():
    await redis_client.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.disconnect()


# Apply middleware and limiter
configure_middlewares(app)
configure_limiter(app)

API_PREFIX = "/api/v1"

# Auth
app.include_router(authentications.router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(users_router, prefix="/api/v1")



# App logic
app.include_router(flights_router, prefix=API_PREFIX)
app.include_router(bookings_router, prefix=API_PREFIX)
app.include_router(promotions_router, prefix=API_PREFIX)


# Health check
app.include_router(test_health.router)
