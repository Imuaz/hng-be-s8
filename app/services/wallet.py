"""
Wallet service layer.
Business logic for wallet and transaction management.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
import json
import secrets
import string

from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.models.auth import User
from app.services.paystack import PaystackService


def generate_wallet_number() -> str:
    """
    Generate a unique 13-digit wallet number.

    Returns:
        13-digit string
    """
    # Generate 13-digit number (not starting with 0)
    first_digit = secrets.choice(string.digits[1:])
    remaining_digits = "".join(secrets.choice(string.digits) for _ in range(12))
    return first_digit + remaining_digits


def create_wallet(db: Session, user_id: UUID) -> Wallet:
    """
    Create a wallet for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Created wallet object
    """
    # Check if user already has a wallet
    existing_wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if existing_wallet:
        return existing_wallet

    # Generate unique wallet number
    while True:
        wallet_number = generate_wallet_number()
        if not db.query(Wallet).filter(Wallet.wallet_number == wallet_number).first():
            break

    wallet = Wallet(
        user_id=user_id, wallet_number=wallet_number, balance=Decimal("0.00")
    )

    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    return wallet


def get_wallet_by_user(db: Session, user_id: UUID) -> Wallet:
    """
    Get wallet by user ID.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Wallet object

    Raises:
        HTTPException: If wallet not found
    """
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found. Please contact support.",
        )
    return wallet


def get_wallet_by_number(db: Session, wallet_number: str) -> Wallet:
    """
    Get wallet by wallet number.

    Args:
        db: Database session
        wallet_number: Wallet number

    Returns:
        Wallet object

    Raises:
        HTTPException: If wallet not found
    """
    wallet = db.query(Wallet).filter(Wallet.wallet_number == wallet_number).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipient wallet not found"
        )
    return wallet


async def initiate_deposit(db: Session, user_id: UUID, amount: Decimal) -> dict:
    """
    Initiate a deposit using Paystack.

    Args:
        db: Database session
        user_id: User ID
        amount: Amount to deposit in kobo

    Returns:
        Dict with reference and authorization_url
    """
    # Get user and wallet
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    wallet = get_wallet_by_user(db, user_id)

    # Generate unique reference
    reference = f"DEP-{secrets.token_urlsafe(16)}"

    # Create pending transaction
    transaction = Transaction(
        reference=reference,
        wallet_id=wallet.id,
        type=TransactionType.DEPOSIT,
        amount=amount,
        status=TransactionStatus.PENDING,
        description=f"Deposit via Paystack",
        metadata=json.dumps({"email": user.email}),
    )

    db.add(transaction)
    db.commit()

    # Initialize Paystack transaction
    try:
        paystack_result = await PaystackService.initialize_transaction(
            email=user.email, amount=int(amount), reference=reference
        )

        return {
            "reference": reference,
            "authorization_url": paystack_result["authorization_url"],
            "amount": amount,
            "status": "pending",
        }
    except Exception as e:
        # Mark transaction as failed
        transaction.status = TransactionStatus.FAILED
        db.commit()
        raise


async def process_webhook(db: Session, payload: dict) -> bool:
    """
    Process Paystack webhook for successful payment.
    IDEMPOTENT: Safe to call multiple times with the same reference.

    Args:
        db: Database session
        payload: Webhook payload from Paystack

    Returns:
        True if processed successfully
    """
    event = payload.get("event")
    if event != "charge.success":
        return False

    data = payload.get("data", {})
    reference = data.get("reference")
    amount = data.get("amount")  # in kobo
    paystack_status = data.get("status")

    if not reference or paystack_status != "success":
        return False

    # Find transaction
    transaction = (
        db.query(Transaction).filter(Transaction.reference == reference).first()
    )

    if not transaction:
        # Log this - could be a fraudulent webhook
        return False

    # Check if already processed (idempotency)
    if transaction.status == TransactionStatus.SUCCESS:
        return True  # Already processed, no-op

    # Verify amount matches
    if int(transaction.amount) != amount:
        transaction.status = TransactionStatus.FAILED
        transaction.metadata = json.dumps(
            {
                "error": "Amount mismatch",
                "expected": str(transaction.amount),
                "received": str(amount),
            }
        )
        db.commit()
        return False

    # Update transaction status
    transaction.status = TransactionStatus.SUCCESS
    transaction.metadata = json.dumps(
        {
            **json.loads(transaction.metadata or "{}"),
            "paystack_reference": data.get("id"),
            "processed_at": datetime.utcnow().isoformat(),
        }
    )

    # Credit wallet
    wallet = db.query(Wallet).filter(Wallet.id == transaction.wallet_id).first()
    wallet.balance += transaction.amount
    wallet.updated_at = datetime.utcnow()

    db.commit()

    return True


def transfer_funds(
    db: Session, sender_wallet_id: UUID, recipient_wallet_number: str, amount: Decimal
) -> dict:
    """
    Transfer funds from one wallet to another.
    ATOMIC: Both debit and credit succeed or fail together.

    Args:
        db: Database session
        sender_wallet_id: Sender's wallet ID
        recipient_wallet_number: Recipient's wallet number
        amount: Amount to transfer in kobo

    Returns:
        Dict with status and message

    Raises:
        HTTPException: For various error conditions
    """
    # Get sender wallet
    sender_wallet = db.query(Wallet).filter(Wallet.id == sender_wallet_id).first()
    if not sender_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sender wallet not found"
        )

    # Get recipient wallet
    recipient_wallet = get_wallet_by_number(db, recipient_wallet_number)

    # Check for self-transfer
    if sender_wallet.id == recipient_wallet.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to your own wallet",
        )

    # Check sender balance
    if sender_wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance"
        )

    # Generate reference
    reference = f"TRF-{secrets.token_urlsafe(16)}"

    try:
        # Create debit transaction for sender
        debit_transaction = Transaction(
            reference=f"{reference}-OUT",
            wallet_id=sender_wallet.id,
            type=TransactionType.TRANSFER_OUT,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            description=f"Transfer to {recipient_wallet.wallet_number}",
            metadata=json.dumps(
                {
                    "recipient_wallet": recipient_wallet.wallet_number,
                    "recipient_user_id": str(recipient_wallet.user_id),
                }
            ),
        )

        # Create credit transaction for recipient
        credit_transaction = Transaction(
            reference=f"{reference}-IN",
            wallet_id=recipient_wallet.id,
            type=TransactionType.TRANSFER_IN,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            description=f"Transfer from {sender_wallet.wallet_number}",
            metadata=json.dumps(
                {
                    "sender_wallet": sender_wallet.wallet_number,
                    "sender_user_id": str(sender_wallet.user_id),
                }
            ),
        )

        # Update balances
        sender_wallet.balance -= amount
        recipient_wallet.balance += amount

        sender_wallet.updated_at = datetime.utcnow()
        recipient_wallet.updated_at = datetime.utcnow()

        # Add transactions
        db.add(debit_transaction)
        db.add(credit_transaction)

        # Commit atomically
        db.commit()

        return {
            "status": "success",
            "message": "Transfer completed",
            "reference": reference,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer failed: {str(e)}",
        )


def get_transactions(
    db: Session, wallet_id: UUID, limit: int = 50, offset: int = 0
) -> List[Transaction]:
    """
    Get transaction history for a wallet.

    Args:
        db: Database session
        wallet_id: Wallet ID
        limit: Maximum number of transactions to return
        offset: Number of transactions to skip

    Returns:
        List of transactions
    """
    transactions = (
        db.query(Transaction)
        .filter(Transaction.wallet_id == wallet_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return transactions


async def get_deposit_status(db: Session, reference: str) -> dict:
    """
    Get deposit status (optional fallback, webhook is primary).

    Args:
        db: Database session
        reference: Transaction reference

    Returns:
        Dict with transaction status
    """
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.reference == reference,
            Transaction.type == TransactionType.DEPOSIT,
        )
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    return {
        "reference": transaction.reference,
        "status": transaction.status.value,
        "amount": transaction.amount,
    }
