"""
Pydantic schemas for wallet and transaction operations.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal


# Wallet Schemas
class WalletResponse(BaseModel):
    """Schema for wallet data in responses."""

    id: UUID
    wallet_number: str
    balance: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


# Deposit Schemas
class DepositRequest(BaseModel):
    """Schema for initiating a deposit."""

    amount: Decimal = Field(
        ...,
        gt=0,
        description="Amount to deposit in kobo (minimum 10000 kobo = 100 NGN)",
    )

    @field_validator("amount")
    def validate_minimum_amount(cls, value):
        """Paystack requires minimum 100 NGN (10000 kobo)."""
        if value < 10000:
            raise ValueError("Minimum deposit amount is 10000 kobo (100 NGN)")
        return value


class DepositResponse(BaseModel):
    """Schema for deposit initialization response."""

    reference: str
    authorization_url: str
    amount: Decimal
    status: str = "pending"


# Transfer Schemas
class TransferRequest(BaseModel):
    """Schema for wallet-to-wallet transfer."""

    wallet_number: str = Field(
        ...,
        min_length=13,
        max_length=13,
        description="Recipient's 13-digit wallet number",
    )
    amount: Decimal = Field(..., gt=0, description="Amount to transfer in kobo")


class TransferResponse(BaseModel):
    """Schema for transfer response."""

    status: str
    message: str
    reference: Optional[str] = None


# Transaction Schemas
class TransactionResponse(BaseModel):
    """Schema for transaction data in responses."""

    id: UUID
    reference: str
    type: str
    amount: Decimal
    status: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Balance Schema
class BalanceResponse(BaseModel):
    """Schema for balance response."""

    balance: Decimal
    wallet_number: str
