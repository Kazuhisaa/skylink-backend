import logging

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.settings import settings

logger = logging.getLogger(__name__)

REDIS_URL = settings.REDIS_URL

# Use Redis for rate limiting storage to support distributed scaling, fallback to in-memory if Redis is offline
storage_uri = REDIS_URL
if REDIS_URL.startswith("redis://") or REDIS_URL.startswith("rediss://"):
    try:
        import redis

        # Test connection quickly
        client = redis.from_url(REDIS_URL, socket_connect_timeout=1)
        client.ping()
        logger.info("Successfully connected to Redis for rate limiting storage.")
    except Exception as e:
        logger.warning(
            f"Could not connect to Redis at {REDIS_URL}: {e}. Falling back to in-memory rate limiting storage."
        )
        storage_uri = "memory://"
else:
    storage_uri = "memory://"

limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri)


def configure_limiter(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
