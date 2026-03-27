from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")



def debug_mode():
  return {
    "debug": DEBUG,
    "docs_url": "/docs" if DEBUG else None,
    "redoc_url": "/redoc" if DEBUG else None,
    "openapi_url": "/openapi.json" if DEBUG else None
  }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=()"
    if not DEBUG:
      response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
    

def configure_middlewares(app):
  #app.add_middleware(SecurityHeadersMiddleware)

  # Trusted host
  app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts= ALLOWED_HOSTS  # replace with your production hosts
  )

  # CORS
  app.add_middleware(
    CORSMiddleware,
    #allow_origins=ALLOWED_ORIGINS,  # replace with frontend URL
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    #allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    allow_credentials=True
  )