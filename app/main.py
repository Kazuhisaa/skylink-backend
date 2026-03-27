from fastapi import FastAPI
from app.core.config import configure_middlewares, debug_mode
from app.core.limiter import configure_limiter

from tests import test_health
import logging

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
  datefmt="%Y-%m-%d %H:%M:%S",
)


app = FastAPI(**debug_mode())

# Apply middleware and limiter
configure_middlewares(app)
configure_limiter(app)

# Auth
# app.include_router(example.router)


# App logic
# app.include_router(example.router)



# Health check
app.include_router(test_health.router)