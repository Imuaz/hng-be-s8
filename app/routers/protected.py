"""
Protected routes demonstrating different authentication types.
"""

from fastapi import APIRouter, Depends
from app.models.auth import User
from app.dependencies.auth import require_user, require_service, get_current_auth

router = APIRouter(prefix="/protected", tags=["Protected Routes (Demo)"])


@router.get("/user")
async def protected_user_only(user: User = Depends(require_user)):
    """
    Protected route - **ONLY** accepts JWT Bearer token.

    **Authentication:** JWT Bearer token required

    **Returns:**
    - Greeting message with username

    **Errors:**
    - `401 Unauthorized`: Invalid, missing, or expired JWT token

    **Example:**
    ```bash
    curl -H "Authorization: Bearer <token>" http://localhost:8000/protected/user
    ```
    """
    return {
        "message": f"Hello {user.username}!",
        "user_id": user.id,
        "email": user.email,
        "auth_type": "JWT Bearer Token",
    }


@router.get("/service")
async def protected_service_only(service: dict = Depends(require_service)):
    """
    Protected route - **ONLY** accepts API key.

    **Authentication:** API key required (via x-api-key header)

    **Returns:**
    - Greeting message with service name

    **Errors:**
    - `401 Unauthorized`: Invalid, missing, or expired API key

    **Example:**
    ```bash
    curl -H "x-api-key: sk_xxxxx" http://localhost:8000/protected/service
    ```
    """
    return {
        "message": f"Hello {service['name']}!",
        "service_name": service["name"],
        "api_key_id": service["api_key_id"],
        "user_id": service["user_id"],
        "auth_type": "API Key",
    }


@router.get("/any")
async def protected_any_auth(auth: dict = Depends(get_current_auth)):
    """
    Protected route - accepts **EITHER** JWT Bearer token **OR** API key.

    **Authentication:** JWT Bearer token OR API key

    **Returns:**
    - Greeting message with authentication details

    **Errors:**
    - `401 Unauthorized`: No valid authentication provided

    **Examples:**
    ```bash
    # Using JWT token
    curl -H "Authorization: Bearer <token>" http://localhost:8000/protected/any

    # Using API key
    curl -H "x-api-key: sk_xxxxx" http://localhost:8000/protected/any
    ```
    """
    if auth["type"] == "user":
        return {
            "message": f"Hello user {auth['username']}!",
            "auth_type": "JWT Bearer Token",
            "details": auth,
        }
    else:  # service
        return {
            "message": f"Hello service {auth['name']}!",
            "auth_type": "API Key",
            "details": auth,
        }
