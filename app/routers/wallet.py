"""
Wallet routes for deposits, transfers, and transaction history.
"""

import json
from fastapi import APIRouter, Depends, status, Request, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.wallet import (
    WalletResponse,
    DepositRequest,
    DepositResponse,
    TransferRequest,
    TransferResponse,
    TransactionResponse,
    BalanceResponse,
)
from app.services.wallet import (
    get_wallet_by_user,
    initiate_deposit,
    process_webhook,
    transfer_funds,
    get_transactions,
    get_deposit_status,
)
from app.services.paystack import PaystackService
from app.dependencies.auth import get_current_auth, require_permission

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    auth: dict = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Get wallet balance.

    **Auth**: JWT or API key with `read` permission

    **Returns**: Balance in kobo (e.g., 10000 = ₦100.00)
    """
    wallet = get_wallet_by_user(db, auth["user_id"])
    return {"balance": str(wallet.balance), "wallet_number": wallet.wallet_number}


@router.post(
    "/deposit", response_model=DepositResponse, status_code=status.HTTP_201_CREATED
)
async def initialize_deposit(
    deposit_data: DepositRequest,
    auth: dict = Depends(require_permission("deposit")),
    db: Session = Depends(get_db),
):
    """
    Initialize Paystack deposit.

    **Auth**: JWT or API key with `deposit` permission

    **Amount**: In kobo (e.g., 10000 = ₦100.00)

    **Returns**: Paystack payment link for user to complete payment

    **Response**:
    - `authorization_url`: Paystack payment link
    - `reference`: Transaction reference
    """
    result = await initiate_deposit(db, auth["user_id"], deposit_data.amount)
    return result


@router.post("/paystack/webhook", status_code=status.HTTP_200_OK)
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Paystack webhooks (MANDATORY for crediting wallets).

    ⚠️ **CANNOT TEST IN SWAGGER UI** - Called by Paystack servers only!

    **Testing Instructions:**
    1. Configure webhook in Paystack Dashboard:
       - URL: `https://hng-be-s8-production.up.railway.app/wallet/paystack/webhook`
       - Event: "Successful Payment" or "All Events"
    2. Make a real test payment via `/wallet/deposit`
    3. Complete payment on Paystack checkout page
    4. Paystack will automatically call this webhook
    5. Wallet will be credited automatically

    **Manual Test (Signature Validation):**
    ```bash
    curl -X POST https://hng-be-s8-production.up.railway.app/wallet/paystack/webhook \
      -H "Content-Type: application/json" \
      -d '{"event":"charge.success"}'
    # Should return 401 (signature validation working)
    ```

    **No authentication required** - validates via Paystack signature.

    **Security**: Verifies X-Paystack-Signature header
    """
    # Get raw body and signature
    body = await request.body()
    signature = request.headers.get("X-Paystack-Signature", "")

    # Verify signature
    if not PaystackService.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    # Parse payload
    payload = json.loads(body)

    # Process webhook
    success = await process_webhook(db, payload)

    return {"status": success}


@router.get("/deposit/{reference}/status")
async def check_deposit_status(
    reference: str,
    auth: dict = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Check deposit status (fallback method, webhook is primary).

    **Auth**: JWT or API key with `read` permission

    **Note**: This does NOT credit wallets - only the webhook does that.
    """
    status_data = await get_deposit_status(db, reference)
    return status_data


@router.post("/transfer", response_model=TransferResponse)
async def transfer_money(
    transfer_data: TransferRequest,
    auth: dict = Depends(require_permission("transfer")),
    db: Session = Depends(get_db),
):
    """
    Transfer funds to another wallet.

    **Auth**: JWT or API key with `transfer` permission

    **Amount**: In kobo (e.g., 10000 = ₦100.00)

    **Validates**:
    - Sufficient balance
    - Valid recipient wallet
    - Cannot transfer to self

    **Errors**:
    - 400: Insufficient balance
    - 404: Invalid recipient wallet
    - 400: Cannot transfer to self
    """
    wallet = get_wallet_by_user(db, auth["user_id"])
    result = transfer_funds(
        db, wallet.id, transfer_data.wallet_number, transfer_data.amount
    )
    return result


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions_endpoint(
    limit: int = 50,
    offset: int = 0,
    auth: dict = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Get transaction history with pagination.

    **Auth**: JWT or API key with `read` permission

    **Query Parameters**:
    - `limit`: Max transactions to return (default: 50)
    - `offset`: Number of transactions to skip (default: 0)

    **Returns**: Amounts in kobo (e.g., 10000 = ₦100.00)
    """
    wallet = get_wallet_by_user(db, auth["user_id"])
    transactions = get_transactions(db, wallet.id, limit, offset)
    return transactions
