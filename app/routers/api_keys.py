"""
API Key management routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.auth import APIKeyCreate, APIKeyResponse, APIKeyListResponse
from app.services.api_keys import (
    create_api_key,
    list_user_api_keys,
    revoke_api_key,
    delete_api_key,
)
from app.dependencies.auth import get_current_auth
from uuid import UUID

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post(
    "/create", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_new_api_key(
    key_data: APIKeyCreate,
    auth: dict = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    """
    Create a new API key (requires user authentication via JWT).

    **Authentication:** Requires JWT Bearer token (user authentication only)

    **Request Body:**
    - `name`: Descriptive name for the API key (1-100 characters)
    - `expires_in_days`: Optional expiration period in days (1-3650, default: 365)

    **Returns:**
    - Complete API key information including the generated key
    - **IMPORTANT:** Save the `key` value - it won't be shown again!

    **Errors:**
    - `401 Unauthorized`: Invalid or missing JWT token
    - `403 Forbidden`: Only user accounts can create API keys

    **Usage:**
    Use the generated API key in requests via the `x-api-key` header:
    ```
    x-api-key: sk_xxxxxxxxxxxxx
    ```
    """
    # Only users can create API keys
    if auth["type"] != "user":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only user accounts can create API keys",
        )

    api_key = create_api_key(
        db,
        user_id=auth["user_id"],
        name=key_data.name,
        expires_in_days=key_data.expires_in_days,
    )

    return api_key


@router.get("", response_model=List[APIKeyListResponse])
async def list_api_keys(
    auth: dict = Depends(get_current_auth), db: Session = Depends(get_db)
):
    """
    List all API keys for the authenticated user.

    **Authentication:** Requires JWT Bearer token (user authentication only)

    **Returns:**
    - List of API keys (without exposing the actual key values)

    **Errors:**
    - `401 Unauthorized`: Invalid or missing JWT token
    - `403 Forbidden`: Only user accounts can list API keys
    """
    # Only users can list their API keys
    if auth["type"] != "user":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only user accounts can list API keys",
        )

    api_keys = list_user_api_keys(db, auth["user_id"])
    return api_keys


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def delete_key(
    key_id: UUID, auth: dict = Depends(get_current_auth), db: Session = Depends(get_db)
):
    """
    Permanently delete an API key.

    **Authentication:** Requires JWT Bearer token (user authentication only)

    **Path Parameters:**
    - `key_id`: ID of the API key to delete
    """
    # Only users can delete their API keys
    if auth["type"] != "user":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only user accounts can delete API keys",
        )

    delete_api_key(db, key_id, auth["user_id"])
    return {"message": "API key deleted successfully", "key_id": key_id}


@router.post("/{key_id}/revoke")
async def revoke_key(
    key_id: UUID, auth: dict = Depends(get_current_auth), db: Session = Depends(get_db)
):
    """
    Revoke an API key (Soft Delete).

    **Authentication:** Requires JWT Bearer token (user authentication only)

    **Path Parameters:**
    - `key_id`: ID of the API key to revoke

    **Returns:**
    - Success message
    """
    # Only users can revoke their API keys
    if auth["type"] != "user":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only user accounts can revoke API keys",
        )

    revoke_api_key(db, key_id, auth["user_id"])

    return {"message": "API key revoked successfully", "key_id": key_id}
