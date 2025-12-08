"""
SQLAlchemy ORM models for User and APIKey.
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for Google OAuth users
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Google OAuth
    google_id = Column(String, unique=True, index=True, nullable=True)

    # Password Reset
    reset_token_hash = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)

    # Relationships
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    wallet = relationship(
        "Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class APIKey(Base):
    """API Key model for service-to-service authentication."""

    __tablename__ = "api_keys"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permissions = Column(
        String, nullable=False, default='["read"]'
    )  # JSON array as string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Relationship to user
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class TokenBlacklist(Base):
    """Model for blacklisted JWT tokens (Logout)."""

    __tablename__ = "token_blacklist"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    token_jti = Column(String, unique=True, index=True, nullable=False)
    # Store expiration so we can eventually clean up old blacklisted tokens
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TokenBlacklist(jti='{self.token_jti}')>"
