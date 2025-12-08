"""
API Key service layer.
Business logic for API key generation, validation, and management.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from app.models.auth import APIKey
from app.utils.security import generate_api_key, get_key_hash
from app.config import settings

# Simple in-memory cache: {key_hash: (api_key_dict, expiration_timestamp)}
API_KEY_CACHE = {}


def convert_expiry_to_datetime(expiry: str) -> datetime:
    """
    Convert expiry format (1H, 1D, 1M, 1Y) to datetime.

    Args:
        expiry: Expiry string (e.g., "1H", "7D", "1M", "1Y")

    Returns:
        Expiration datetime
    """
    unit = expiry[-1].upper()
    amount = int(expiry[:-1])

    if unit == "H":
        return datetime.utcnow() + timedelta(hours=amount)
    elif unit == "D":
        return datetime.utcnow() + timedelta(days=amount)
    elif unit == "M":
        return datetime.utcnow() + timedelta(days=amount * 30)  # Approximate month
    elif unit == "Y":
        return datetime.utcnow() + timedelta(days=amount * 365)  # Approximate year
    else:
        raise ValueError(f"Invalid expiry unit: {unit}")


def create_api_key(
    db: Session, user_id: UUID, name: str, permissions: List[str], expiry: str = "1Y"
) -> APIKey:
    """
    Create a new API key for a user.

    Args:
        db: Database session
        user_id: ID of the user creating the API key
        name: Name/description of the API key
        permissions: List of permissions (deposit, transfer, read)
        expiry: Expiry format (1H, 1D, 1M, 1Y)

    Returns:
        Created API key object

    Raises:
        HTTPException: If validation fails
    """
    # Check if key with same name already exists for this user
    existing_key = (
        db.query(APIKey).filter(APIKey.user_id == user_id, APIKey.name == name).first()
    )
    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key with this name already exists",
        )

    # Check 5 active keys limit
    active_keys_count = (
        db.query(APIKey)
        .filter(
            APIKey.user_id == user_id,
            APIKey.is_revoked == False,
            APIKey.expires_at > datetime.utcnow(),
        )
        .count()
    )

    if active_keys_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 5 active API keys allowed. Please revoke an existing key first.",
        )

    # Generate unique API key
    plain_key = generate_api_key()
    key_hash = get_key_hash(plain_key)

    # Calculate expiration date from format
    expires_at = convert_expiry_to_datetime(expiry)

    # Serialize permissions as JSON string
    import json

    permissions_json = json.dumps(permissions)

    # Create API key record
    db_api_key = APIKey(
        key_hash=key_hash,
        name=name,
        user_id=user_id,
        permissions=permissions_json,
        expires_at=expires_at,
    )

    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)

    # Attach plain key to object for one-time display (not persisted)
    db_api_key.key = plain_key

    return db_api_key


def validate_api_key(db: Session, key: str) -> Optional[dict]:
    """
    Validate an API key and update its last_used_at timestamp.

    Args:
        db: Database session
        key: API key string to validate

    Returns:
        Dictionary with API key info or None if invalid

    Raises:
        HTTPException: If API key is expired
    """
    key_hash = get_key_hash(key)

    # Check cache
    if key_hash in API_KEY_CACHE:
        cached_data, valid_until = API_KEY_CACHE[key_hash]
        if datetime.utcnow() < valid_until:
            # Update last_used_at in background?
            # For strictness we skip DB write on cache hit for speed, or use a background task.
            # Here we prioritized speed, so we skip DB write.
            return cached_data
        else:
            del API_KEY_CACHE[key_hash]

    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_revoked == False)
        .first()
    )

    if not api_key:
        return None

    # Check if expired
    if api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key has expired"
        )

    # Update last used timestamp
    api_key.last_used_at = datetime.utcnow()
    db.commit()

    # Parse permissions from JSON
    import json

    permissions = json.loads(api_key.permissions or '["read"]')

    result = {
        "api_key_id": api_key.id,
        "user_id": api_key.user_id,
        "name": api_key.name,
        "permissions": permissions,
        "type": "service",
    }

    # Cache for 5 minutes
    API_KEY_CACHE[key_hash] = (result, datetime.utcnow() + timedelta(minutes=5))

    return result

    return result


def list_user_api_keys(db: Session, user_id: UUID) -> List[APIKey]:
    """
    Get all API keys for a user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        List of API key objects
    """
    return db.query(APIKey).filter(APIKey.user_id == user_id).all()


def revoke_api_key(db: Session, key_id: UUID, user_id: UUID) -> APIKey:
    """
    Revoke an API key (Soft Delete).

    Args:
        db: Database session
        key_id: ID of the API key to revoke
        user_id: ID of the user (for authorization check)

    Returns:
        Revoked API key object

    Raises:
        HTTPException: If API key not found
    """
    api_key = (
        db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user_id).first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    api_key.is_revoked = True
    db.commit()
    db.refresh(api_key)

    # Invalidate cache
    # Since we don't have the original key string here, we can't easily remove it from cache
    # if the cache key is the hash.
    # However, since we query DB on cache miss, and revocation updates DB,
    # we just need to ensure we don't rely on stale cache.
    # But wait, if cached, we return cached data and ignore DB.
    # So we MUST invalidate cache.
    # Problem: 'revoke_api_key' input is 'key_id', not 'key'.
    # We can't derive 'key_hash' from 'key_id'.
    # Solution: We can't selectively invalidate efficiently without storing map id->hash.
    # OR we accept 5 min delay in revocation (acceptable for "Speed").
    # OR we clear entire cache check (heavy).
    # OR we add key_hash to cache value so we can iterate.

    # Let's iterate cache to remove by ID (O(N) but N is cache size).
    keys_to_remove = []
    for k, (v, _) in API_KEY_CACHE.items():
        if v["api_key_id"] == key_id:
            keys_to_remove.append(k)

    for k in keys_to_remove:
        del API_KEY_CACHE[k]

    return api_key


def delete_api_key(db: Session, key_id: UUID, user_id: UUID):
    """
    Parmanently remove an API key (Hard Delete).

    Args:
        db: Database session
        key_id: ID of the API key to delete
        user_id: ID of the user (for authorization check)

    Raises:
        HTTPException: If API key not found
    """
    api_key = (
        db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user_id).first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Invalidate cache before delete
    keys_to_remove = []
    for k, (v, _) in API_KEY_CACHE.items():
        if v["api_key_id"] == key_id:
            keys_to_remove.append(k)

    for k in keys_to_remove:
        del API_KEY_CACHE[k]

    db.delete(api_key)
    db.commit()
