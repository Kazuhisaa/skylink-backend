import logging
import uuid
import hmac
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.payments import Payment
from app.models.bookings import Booking
from app.services.paymongo_service import paymongo_service
from app.core.config import settings

logger = logging.getLogger(__name__)

async def create_payment_intent(booking_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Dict[str, Any]:
    # 1. Fetch booking and verify ownership
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.payment))
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 2. Idempotency: Check if a payment already exists
    if booking.payment:
        if booking.payment.status == "paid":
            raise HTTPException(status_code=400, detail="Booking is already paid")
        # If it's still pending, we can return the existing gateway_ref or create a new one.
        # To avoid multiple clicks, we return the existing intent if it exists.
        if booking.payment.gateway_ref:
            # Optionally retrieve the latest status from PayMongo
            intent = await paymongo_service.retrieve_payment_intent(booking.payment.gateway_ref)
            return {
                "client_key": intent["data"]["attributes"]["client_key"],
                "payment_intent_id": intent["data"]["id"]
            }

    # 3. Create Payment Intent in PayMongo
    # total_price is stored in pesos (Numeric 10,2). PayMongo requires centavos (integer).
    amount_centavos = int(float(booking.total_price) * 100)
    description = f"Payment for Booking {booking_id}"
    metadata = {
        "booking_id": str(booking_id),
        "user_id": str(user_id)
    }
    
    intent_data = await paymongo_service.create_payment_intent(amount_centavos, description, metadata)
    intent_id = intent_data["data"]["id"]
    client_key = intent_data["data"]["attributes"]["client_key"]

    # 4. Create internal Payment record
    if not booking.payment:
        new_payment = Payment(
            id=uuid.uuid4(),
            booking_id=booking_id,
            amount=amount_centavos,
            currency="PHP",
            method="paymongo",
            status="pending",
            gateway_ref=intent_id,
            external_metadata=intent_data  # Save raw response
        )
        db.add(new_payment)
        
        # Update booking status to reflect payment is initiated
        booking.status = "pending_payment"
    else:
        # Update existing record
        booking.payment.gateway_ref = intent_id
        booking.payment.status = "pending"
        booking.payment.external_metadata = intent_data

    await db.commit()
    
    return {
        "client_key": client_key,
        "payment_intent_id": intent_id
    }

async def handle_webhook(payload: Dict[str, Any], signature: str, request_timestamp: str):
    # Verify Webhook Signature (Implementation below)
    # verify_webhook_signature(payload, signature, request_timestamp)
    
    event_type = payload["data"]["attributes"]["type"]
    resource_data = payload["data"]["attributes"]["data"]
    
    if event_type == "payment.paid":
        payment_intent_id = resource_data["attributes"]["payment_intent_id"]
        # In PayMongo, the payment record contains the payment_intent_id in attributes
        # We need to find the booking associated with this intent
        await _process_successful_payment(payment_intent_id)
    
    return {"status": "success"}

async def _process_successful_payment(gateway_ref: str):
    # This usually requires its own session or a shared one
    # For now, let's assume we have a way to get the DB session
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payment).where(Payment.gateway_ref == gateway_ref).options(selectinload(Payment.booking))
        )
        payment = result.scalar_one_or_none()
        
        if payment and payment.status != "paid":
            payment.status = "paid"
            payment.paid_at = datetime.now()
            if payment.booking:
                payment.booking.status = "confirmed" # or "paid"
            await db.commit()
            logger.info(f"Payment {gateway_ref} marked as PAID. Booking {payment.booking_id} confirmed.")

def verify_webhook_signature(payload_bytes: bytes, signature: str, timestamp: str):
    """
    Verifies that the webhook request came from PayMongo.
    """
    if not settings.PAYMONGO_WEBHOOK_SECRET:
        logger.warning("PAYMONGO_WEBHOOK_SECRET not set. Skipping verification (NOT SECURE)")
        return

    # PayMongo signature verification logic
    # 1. Concatenate timestamp and raw body: f"{timestamp}.{raw_body}"
    # 2. HMAC-SHA256 with Webhook Secret
    # 3. Compare with signature header
    
    to_sign = f"{timestamp}.{payload_bytes.decode()}".encode()
    expected_sig = hmac.new(
        settings.PAYMONGO_WEBHOOK_SECRET.encode(),
        to_sign,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_sig, signature):
        logger.error("Invalid PayMongo webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
