"""
Authentication service layer.
Business logic for user authentication and JWT token management.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta, datetime
from app.models.auth import User, TokenBlacklist
from app.schemas.auth import UserSignup, UserLogin
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.config import settings


def create_user(db: Session, user_data: UserSignup) -> User:
    """
    Create a new user in the database.

    Args:
        db: Database session
        user_data: User signup data

    Returns:
        Created user object

    Raises:
        HTTPException: If email or username already exists
    """
    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, username: str, password: str) -> User:
    """
    Authenticate a user with username and password.

    Args:
        db: Database session
        username: User's username
        password: Plain text password

    Returns:
        Authenticated user object

    Raises:
        HTTPException: If credentials are invalid
    """
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account"
        )

    return user


def create_user_token(user: User) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user: User object

    Returns:
        JWT access token string
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # user.id is UUID, convert to str
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return access_token


def blacklist_token(db: Session, token: str):
    """
    Blacklist a JWT token (Logout).

    Args:
        db: Database session
        token: JWT token string
    """
    from app.utils.security import decode_access_token

    payload = decode_access_token(token)
    if not payload:
        return  # Already invalid

    # We use the token signature or jti if available.
    # Simply storing the token string might be too large if large payload.
    # Standard JWT has 'jti' (unique identifier). If we didn't add 'jti', we can hash the token.
    # Let's check `create_access_token` in utils.
    # It doesn't seem to add 'jti' by default.
    # So we will store the raw token or hash of the token.
    # Let's use the token itself for simplicity here as it's just a ref pointer.
    # But wait, `token_jti` column in model implies JTI.
    # Let's just use the token string as JTI for now, or hash it.

    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Check if already blacklisted
    if db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == token_hash).first():
        return

    # Calculate expiration to clean up db later
    exp_timestamp = payload.get("exp")
    if exp_timestamp:
        expires_at = datetime.utcfromtimestamp(exp_timestamp)
    else:
        expires_at = datetime.utcnow() + timedelta(days=1)  # Fallback

    blacklist_entry = TokenBlacklist(token_jti=token_hash, expires_at=expires_at)
    db.add(blacklist_entry)
    db.commit()


def is_token_blacklisted(db: Session, token: str) -> bool:
    """
    Check if a token is blacklisted.
    """
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    entry = (
        db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == token_hash).first()
    )
    return entry is not None


def create_password_reset_token(db: Session, email: str) -> str:
    """
    Generate a password reset token for an email address.

    Args:
        db: Database session
        email: User email

    Returns:
        The plain reset token string (simulating an email send)

    Raises:
        HTTPException: If email not registered
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Security: Don't reveal if user exists or not, but for this task we might fail fast?
        # Standard: return None or send dummy email.
        # But Requirement implies we return the token for testing.
        # Use explicit error for clarity in this specific task context.
        # Or better, just raise 404 so user knows.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    import secrets
    import hashlib

    # Generate token
    token = secrets.token_hex(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Store hash and expiry (15 mins)
    user.reset_token_hash = token_hash
    user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=15)

    db.commit()

    return token


def reset_password(db: Session, token: str, new_password: str):
    """
    Reset user password using a valid token.

    Args:
        db: Database session
        token: The plain reset token
        new_password: The new password

    Raises:
        HTTPException: If token is invalid or expired
    """
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    user = db.query(User).filter(User.reset_token_hash == token_hash).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
        )

    if user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
        )

    # Update password
    user.hashed_password = get_password_hash(new_password)

    # Clear token
    user.reset_token_hash = None
    user.reset_token_expires_at = None

    db.commit()
