from fastapi import FastAPI
from app.core.middleware import configure_middlewares
from app.core.limiter import configure_limiter
from app.core.redis import redis_client
from app.core.settings import settings
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(**settings.app_config)

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


from app.routers import routers
from app.routers.pnr import router as pnr_router

for router in routers:
    app.include_router(router, prefix=API_PREFIX)

# Special case for PNR to match frontend expectation (/api/pnr/status)
app.include_router(pnr_router, prefix="/api")
