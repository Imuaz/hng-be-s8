"""
SQLAlchemy ORM models for Wallet and Transaction.
"""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Uuid,
    Numeric,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.database import Base


class TransactionType(str, enum.Enum):
    """Transaction type enumeration."""

    DEPOSIT = "deposit"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class TransactionStatus(str, enum.Enum):
    """Transaction status enumeration."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Wallet(Base):
    """Wallet model for user wallets."""

    __tablename__ = "wallets"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    wallet_number = Column(String(13), unique=True, index=True, nullable=False)
    balance = Column(Numeric(precision=15, scale=2), default=0.00, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship(
        "Transaction", back_populates="wallet", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Wallet(id={self.id}, wallet_number='{self.wallet_number}', balance={self.balance})>"


class Transaction(Base):
    """Transaction model for wallet transactions."""

    __tablename__ = "transactions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    reference = Column(String, unique=True, index=True, nullable=False)
    wallet_id = Column(
        Uuid(as_uuid=True), ForeignKey("wallets.id"), nullable=False, index=True
    )
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    status = Column(
        SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False
    )
    description = Column(String, nullable=True)
    metadata = Column(String, nullable=True)  # JSON as string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationship
    wallet = relationship("Wallet", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, reference='{self.reference}', type={self.type}, amount={self.amount}, status={self.status})>"
