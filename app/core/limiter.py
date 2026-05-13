import os
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Use Redis for rate limiting storage to support distributed scaling
limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL)

def configure_limiter(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
