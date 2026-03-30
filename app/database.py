import os
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
from fastapi import HTTPException


# ========== Production ==========
# Find the .env file in the backend root
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
  "host": os.getenv("DB_HOST"),
  "port": int(os.getenv("DB_PORT", 5432)),
  "user": os.getenv("DB_USER"),
  "password": os.getenv("DB_PASSWORD"),
  "database": os.getenv("DB_NAME"),
}

_pool = None

async def get_pool():
  global _pool
  if _pool is None:
    try:
      _pool = await asyncpg.create_pool(
        **DB_CONFIG,
        min_size=2,             # Keep 2 connections always open  / Faster response, no cold connection
        max_size=10,            # Never open more than 10         / Supabase free tier safe limit
        command_timeout=30,     # Kill query after 30 seconds     / Prevents hanging requests
        max_inactive_connection_lifetime=300, # Close idle connections after 5 min / Supabase aggressively kills idle connections, this handles it gracefully
      )
      

    except (OSError, asyncpg.PostgresConnectionError, asyncpg.CannotConnectNowError, Exception) as e:
      raise HTTPException(
        status_code=503,
        detail="Unable to connect to the database. Please try again later."
      )
  return _pool
