import os
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
from fastapi import HTTPException

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

async def get_pool():
  global _pool
  if _pool is None:
    try:
      _pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        ssl="require",
        min_size=1,
        max_size=10,
        command_timeout=30,
        max_inactive_connection_lifetime=300,
        statement_cache_size=0,
      )
    except Exception as e:
      raise Exception(str(e))
  return _pool