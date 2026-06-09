import httpx
import base64
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class PayMongoService:
    def __init__(self):
        self.base_url = "https://api.paymongo.com/v1"
        self.secret_key = settings.PAYMONGO_SECRET_KEY
        if not self.secret_key:
            logger.warning("PAYMONGO_SECRET_KEY is not set")
        
        # PayMongo requires Basic Auth with Secret Key as username and empty password
        auth_str = f"{self.secret_key}:"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

    async def create_payment_intent(self, amount: int, description: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a Payment Intent in PayMongo.
        Amount should be in centavos (e.g., 10000 for PHP 100.00).
        """
        url = f"{self.base_url}/payment_intents"
        payload = {
            "data": {
                "attributes": {
                    "amount": amount,
                    "payment_method_allowed": ["card", "paymaya", "gcash", "grab_pay", "paymongo_qr"],
                    "currency": "PHP",
                    "description": description,
                    "metadata": metadata
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"PayMongo API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"PayMongo error: {e.response.json().get('errors', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Unexpected error calling PayMongo: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error calling payment gateway")

    async def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/payment_intents/{intent_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

paymongo_service = PayMongoService()
