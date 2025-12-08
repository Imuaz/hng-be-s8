"""
Authentication routes for user signup and login.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    UserSignup,
    UserLogin,
    UserResponse,
    Token,
    Logout,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.auth import (
    create_user,
    authenticate_user,
    create_user_token,
    blacklist_token,
    create_password_reset_token,
    reset_password,
)
from app.dependencies.rate_limit import RateLimiter
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Rate limiters
signup_limiter = RateLimiter(requests_limit=10, time_window=60)
login_limiter = RateLimiter(requests_limit=5, time_window=60)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(signup_limiter)],
)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Register a new user account.

    **Request Body:**
    - `email`: Valid email address (must be unique)
    - `username`: Username (3-50 characters, must be unique)
    - `password`: Password (minimum 6 characters)

    **Returns:**
    - User information (id, email, username, created_at, is_active)

    **Errors:**
    - `400 Bad Request`: Email or username already exists
    """
    user = create_user(db, user_data)
    return user


@router.post("/login", response_model=Token, dependencies=[Depends(login_limiter)])
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with username and password to receive a JWT access token.

    **Request Body:**
    - `username`: User's username
    - `password`: User's password

    **Returns:**
    - `access_token`: JWT token for authentication
    - `token_type`: "bearer"

    **Errors:**
    - `401 Unauthorized`: Invalid credentials
    - `400 Bad Request`: Inactive user account

    **Usage:**
    Include the token in subsequent requests using the Authorization header:
    ```
    Authorization: Bearer <access_token>
    ```
    """
    user = authenticate_user(db, user_data.username, user_data.password)
    access_token = create_user_token(user)

    access_token = create_user_token(user)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Logout the current user by blacklisting their token.
    """
    token = credentials.credentials
    blacklist_token(db, token)
    return {"message": "Successfully logged out"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    """
    Request a password reset token for the given email.

    **Returns:**
    - `message`: Instructions
    - `reset_token`: The generated token (DEMO ONLY - normally sent via email)
    """
    token = create_password_reset_token(db, request.email)
    return {"message": "Password reset token generated", "reset_token": token}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(
    request: ResetPasswordRequest, db: Session = Depends(get_db)
):
    """
    Reset password using a valid token.
    """
    reset_password(db, request.token, request.new_password)
    return {"message": "Password successfully reset"}
