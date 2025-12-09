"""
Paystack service for payment processing.
"""

import httpx
import hashlib
import hmac
from typing import Dict, Any
from app.config import settings
from fastapi import HTTPException, status


class PaystackService:
    """Service for interacting with Paystack API."""

    BASE_URL = "https://api.paystack.co"

    @staticmethod
    async def initialize_transaction(
        email: str, amount: int, reference: str
    ) -> Dict[str, Any]:
        """
        Initialize a Paystack payment transaction.

        Args:
            email: User's email address
            amount: Amount in kobo (smallest currency unit)
            reference: Unique transaction reference

        Returns:
            Dict containing authorization_url and access_code

        Raises:
            HTTPException: If Paystack API call fails
        """
        url = f"{PaystackService.BASE_URL}/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "email": email,
            "amount": str(amount),  # Paystack expects string
            "reference": reference,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, json=payload, headers=headers, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("status"):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Paystack error: {data.get('message', 'Unknown error')}",
                    )

                return data["data"]
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initialize payment: {str(e)}",
                )

    @staticmethod
    async def verify_transaction(reference: str) -> Dict[str, Any]:
        """
        Verify a Paystack transaction (fallback method, webhook is preferred).

        Args:
            reference: Transaction reference

        Returns:
            Dict containing transaction details

        Raises:
            HTTPException: If verification fails
        """
        url = f"{PaystackService.BASE_URL}/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                if not data.get("status"):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Transaction not found or verification failed",
                    )

                return data["data"]
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to verify transaction: {str(e)}",
                )

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """
        Verify that a webhook request came from Paystack.

        Args:
            payload: Raw request body as bytes
            signature: X-Paystack-Signature header value

        Returns:
            True if signature is valid, False otherwise
        """
        if not settings.PAYSTACK_SECRET_KEY:
            return False

        # Create HMAC digest
        digest = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(digest, signature)
