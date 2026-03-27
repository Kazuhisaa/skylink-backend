from fastapi import APIRouter
from app.database import get_pool

router = APIRouter(prefix="/health")

@router.get("/")
def health_check():
  return {"status": "ok"}


# Local testing only. -> Postman to check db health http://127.0.0.1:8000/health/db
@router.get("/db")
async def health_check_db():
  try:
    pool = await get_pool()
    async with pool.acquire() as conn:
      await conn.fetchval("SELECT 1")
    return {"status": "ok", "database": "connected"}
  except Exception as e:
    return {"status": "error", "database": "unavailable"} # str(e) change the unavailable during local practice
