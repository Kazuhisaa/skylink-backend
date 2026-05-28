from fastapi import APIRouter
from app.database import engine
from sqlalchemy import text

router = APIRouter(prefix="/health")

@router.get("/")
def health_check():
    return {"status": "ok"}

# Local testing only. -> Postman to check db health http://127.0.0.1:8000/health/db
@router.get("/db")
async def health_check_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)} # str(e) change to unavailable after debug