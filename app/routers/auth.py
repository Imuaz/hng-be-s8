"""
Authentication router for user login, signup, password reset, and Google OAuth.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    UserSignup,
    UserLogin,
    Token,
    UserResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.auth import (
    create_user,
    authenticate_user,
    create_user_token,
    blacklist_token,
    is_token_blacklisted,
    create_password_reset_token,
    reset_password,
)
from app.services.google_oauth import oauth
from app.config import settings
from app.models.auth import User
from app.services.wallet import create_wallet
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


@router.get("/google", tags=["Google OAuth"])
async def google_login(request: Request):
    """
    Initiate Google OAuth sign-in.
    Redirects user to Google consent screen.
    """
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=Token, tags=["Google OAuth"])
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback.
    Creates or logs in user and returns JWT token.
    """
    try:
        # Get access token from Google
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get("userinfo")
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google",
            )

        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name", email.split("@")[0])

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required user information",
            )

        # Check if user exists by google_id
        user = db.query(User).filter(User.google_id == google_id).first()

        if not user:
            # Check if email already exists (user signed up with username/password)
            user = db.query(User).filter(User.email == email).first()
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                db.commit()
            else:
                # Create new user
                user = User(
                    email=email,
                    username=name,
                    google_id=google_id,
                    hashed_password=None,  # No password for Google users
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                # Auto-create wallet
                create_wallet(db, user.id)

        # Generate JWT token
        access_token = create_user_token(user)

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth failed: {str(e)}",
        )
