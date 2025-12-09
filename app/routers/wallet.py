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
    """
    wallet = get_wallet_by_user(db, auth["user_id"])
    # Convert balance from kobo to Naira for user-facing response
    balance_naira = float(wallet.balance) / 100
    return {"balance": f"{balance_naira:.2f}", "wallet_number": wallet.wallet_number}


@router.post(
    "/deposit", response_model=DepositResponse, status_code=status.HTTP_201_CREATED
)
async def create_deposit(
    deposit_data: DepositRequest,
    auth: dict = Depends(require_permission("deposit")),
    db: Session = Depends(get_db),
):
    """
    Initialize a Paystack deposit.

    **Auth**: JWT or API key with `deposit` permission

    **Request**:
    - `amount`: Amount in kobo (minimum 10000 kobo = 100 NGN)

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
async def create_transfer(
    transfer_data: TransferRequest,
    auth: dict = Depends(require_permission("transfer")),
    db: Session = Depends(get_db),
):
    """
    Transfer funds to another wallet.

    **Auth**: JWT or API key with `transfer` permission

    **Request**:
    - `wallet_number`: Recipient's 13-digit wallet number
    - `amount`: Amount in kobo

    **Errors**:
    - Insufficient balance
    - Invalid recipient wallet
    - Cannot transfer to self
    """
    wallet = get_wallet_by_user(db, auth["user_id"])
    result = transfer_funds(
        db, wallet.id, transfer_data.wallet_number, transfer_data.amount
    )
    return result


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    transaction_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    auth: dict = Depends(require_permission("read")),
    db: Session = Depends(get_db),
):
    """
    Get transaction history with pagination.

    **Auth**: JWT or API key with `read` permission

    **Params**:
    - transaction_type: Optional filter (deposit, transfer_in, transfer_out)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    """
    transactions = get_transaction_history(
        db, auth["user_id"], transaction_type, page, limit
    )
    # Convert amounts from kobo to Naira for display
    for txn in transactions:
        txn.amount = float(txn.amount) / 100
    return transactions
