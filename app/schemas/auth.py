"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import re


# User Schemas
class UserSignup(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
        title="Email Address",
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username for the account",
        examples=["johndoe123"],
        title="Username",
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
        examples=["StrongPass1!"],
        title="Password",
    )

    @field_validator("password")
    def validate_password(cls, value):
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", value):
            raise ValueError("Password must contain at least one special character")
        return value


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(
        ...,
        description="Registered username",
        examples=["johndoe123"],
        title="Username",
    )
    password: str = Field(
        ..., description="User's password", examples=["StrongPass1!"], title="Password"
    )


class UserResponse(BaseModel):
    """Schema for user data in responses."""

    id: UUID
    email: str
    username: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token data."""

    user_id: Optional[UUID] = None


class Logout(BaseModel):
    """Schema for user logout."""

    # No fields needed for a simple logout request,
    # as the token is typically sent in the header.
    pass


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting a password reset."""

    email: EmailStr = Field(
        ...,
        description="Email address associated with the account",
        examples=["user@example.com"],
        title="Email Address",
    )


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password with a token."""

    token: str = Field(
        ...,
        description="The password reset token received via email",
        examples=["9f85c15e..."],
        title="Reset Token",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password (must follow complexity rules)",
        examples=["NewStrongPass2@"],
        title="New Password",
    )

    @field_validator("new_password")
    def validate_password(cls, value):
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", value):
            raise ValueError("Password must contain at least one special character")
        return value


# API Key Schemas
class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = Field(
        default=["read"], description="Permissions: deposit, transfer, read"
    )
    expiry: str = Field(
        default="1Y",
        description="Expiry format: 1H (hour), 1D (day), 1M (month), 1Y (year)",
        pattern="^[0-9]+[HDMY]$",
    )

    @field_validator("permissions")
    def validate_permissions(cls, value):
        """Validate that permissions are valid."""
        valid_permissions = {"deposit", "transfer", "read"}
        for perm in value:
            if perm not in valid_permissions:
                raise ValueError(
                    f"Invalid permission: {perm}. Must be one of: {valid_permissions}"
                )
        if not value:
            raise ValueError("At least one permission is required")
        return value

    @field_validator("expiry")
    def validate_expiry_format(cls, value):
        """Validate expiry format."""
        if not value:
            raise ValueError("Expiry is required")

        unit = value[-1].upper()
        try:
            amount = int(value[:-1])
        except ValueError:
            raise ValueError("Invalid expiry format. Use format like: 1H, 1D, 1M, 1Y")

        if unit not in ["H", "D", "M", "Y"]:
            raise ValueError(
                "Expiry unit must be H (hour), D (day), M (month), or Y (year)"
            )

        if amount <= 0:
            raise ValueError("Expiry amount must be positive")

        return value


class APIKeyResponse(BaseModel):
    """Schema for API key data in responses."""

    id: UUID
    key: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Schema for listing API keys (without exposing the actual key)."""

    id: UUID
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyRolloverRequest(BaseModel):
    """Schema for rolling over an expired API key."""

    expired_key_id: UUID = Field(
        ..., description="ID of the expired API key to rollover"
    )
    expiry: str = Field(
        default="1M",
        description="Expiry format for new key: 1H (hour), 1D (day), 1M (month), 1Y (year)",
        pattern="^[0-9]+[HDMY]$",
    )

    @field_validator("expiry")
    def validate_expiry_format(cls, value):
        """Validate expiry format."""
        if not value:
            raise ValueError("Expiry is required")

        unit = value[-1].upper()
        try:
            amount = int(value[:-1])
        except ValueError:
            raise ValueError("Invalid expiry format. Use format like: 1H, 1D, 1M, 1Y")

        if unit not in ["H", "D", "M", "Y"]:
            raise ValueError(
                "Expiry unit must be H (hour), D (day), M (month), or Y (year)"
            )

        if amount <= 0:
            raise ValueError("Expiry amount must be positive")

        return value
