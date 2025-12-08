"""
Authentication dependency functions for FastAPI.
Handles JWT and API key authentication.
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.auth import User
from app.utils.security import decode_access_token
from app.services.api_keys import validate_api_key
from app.services.auth import is_token_blacklisted
import uuid

# HTTP Bearer scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Authenticate user via JWT Bearer token.

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        User object if valid token, None otherwise

    Raises:
        HTTPException: If token is expired
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    sub = payload.get("sub")
    if sub is None:
        return None

    try:
        # Convert sub (string) to UUID object
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        return None

    # Check if token is blacklisted
    if is_token_blacklisted(db, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()

    if user is None or not user.is_active:
        return None

    return user


async def get_service_from_api_key(
    x_api_key: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    Authenticate service via API key header.

    Args:
        x_api_key: API key from request header
        db: Database session

    Returns:
        Service info dict if valid API key, None otherwise

    Raises:
        HTTPException: If API key is expired
    """
    if not x_api_key:
        return None

    return validate_api_key(db, x_api_key)


async def get_current_auth(
    user: Optional[User] = Depends(get_current_user_from_token),
    service: Optional[dict] = Depends(get_service_from_api_key),
) -> dict:
    """
    Combined authentication middleware.
    Accepts either JWT token OR API key.

    Args:
        user: User from JWT token (if provided)
        service: Service info from API key (if provided)

    Returns:
        Authentication info dict

    Raises:
        HTTPException: If neither valid JWT nor API key provided
    """
    if user:
        return {
            "type": "user",
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
        }
    elif service:
        return service
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_user(
    user: Optional[User] = Depends(get_current_user_from_token),
) -> User:
    """
    Require JWT user authentication.
    Use this dependency when endpoint should ONLY accept JWT tokens.

    Args:
        user: User from JWT token

    Returns:
        User object

    Raises:
        HTTPException: If no valid JWT token provided
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_service(
    service: Optional[dict] = Depends(get_service_from_api_key),
) -> dict:
    """
    Require API key authentication.
    Use this dependency when endpoint should ONLY accept API keys.

    Args:
        service: Service info from API key

    Returns:
        Service info dict

    Raises:
        HTTPException: If no valid API key provided
    """
    if not service:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key authentication required",
        )
    return service
