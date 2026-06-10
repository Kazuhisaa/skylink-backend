import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/skylink"

    # App
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",")]

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Mail
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "no-reply@skylink.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Skylink"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Test
    TEST_DATABASE_URL: str = ""

    # PayMongo
    PAYMONGO_SECRET_KEY: str = ""
    PAYMONGO_PUBLIC_KEY: str = ""
    PAYMONGO_WEBHOOK_SECRET: str = ""


    # Alembic
    @property
    def SYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if "postgresql://" in url and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url.replace("postgresql+asyncpg", "postgresql+psycopg2")

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if "postgresql://" in url and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # FastAPI Documentation
    @property
    def app_config(self) -> dict:
        return {
            "debug": self.DEBUG,
            "docs_url": "/docs" if self.DEBUG else None,
            "redoc_url": "/redoc" if self.DEBUG else None,
            "openapi_url": "/openapi.json" if self.DEBUG else None,
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()