from fastapi import APIRouter, Depends, Request, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.services import payments_service
from app.core.limiter import limiter

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)

@router.post("/create-intent")
@limiter.limit("5/minute")
async def create_payment_intent(
    request: Request,
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a PayMongo Payment Intent for a specific booking.
    Rate limited to prevent abuse.
    """
    return await payments_service.create_payment_intent(booking_id, current_user.id, db)

@router.post("/webhook")
async def paymongo_webhook(
    request: Request,
    paymongo_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook listener for PayMongo events.
    Verifies signature and updates booking/payment status.
    """
    # 1. Get raw body for signature verification
    body_bytes = await request.body()
    
    # 2. Extract timestamp and signature from header
    # PayMongo signature header looks like: t=12345,te=...,li=...
    if not paymongo_signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    try:
        parts = {}
        for item in paymongo_signature.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                parts[k.strip()] = v.strip()
        
        timestamp = parts.get("t")
        # PayMongo uses 'te' for test mode and 'li' for live mode signatures
        signature = parts.get("te") or parts.get("li")
        
        if not timestamp or not signature:
            logger.error(f"Incomplete signature header. Parts found: {list(parts.keys())}")
            raise HTTPException(status_code=400, detail="Invalid signature format")
            
        # 3. Verify Signature
        payments_service.verify_webhook_signature(body_bytes, signature, timestamp)
        
        # 4. Handle Event
        payload = await request.json()
        return await payments_service.handle_webhook(payload, signature, timestamp)
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        # We return 200 or 4xx but PayMongo expects a 2xx to stop retrying.
        # If it's a verification failure, we return 401.
        if isinstance(e, HTTPException):
            raise e
        return {"status": "error", "message": str(e)}
