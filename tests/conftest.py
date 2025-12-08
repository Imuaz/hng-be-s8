"""
Pytest fixtures for testing.
"""

import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.models.auth import User, APIKey
from app.utils.security import get_password_hash, get_key_hash
from datetime import datetime, timedelta

# Set test environment
os.environ["TESTING"] = "1"

# NOW import the app AFTER setting the environment
from main import app

# Test database URL (in-memory SQLite for testing)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Create a test client with database override.
    """

    # Override the database dependency to use test database
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Apply the override before creating client
    app.dependency_overrides[get_db] = override_get_db

    # Create test client (without triggering lifespan)
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db):
    """
    Create a sample user for testing.
    """
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_api_key(db, sample_user):
    """
    Create a sample API key for testing.
    """
    plain_key = "sk_test_key_123456789"
    api_key = APIKey(
        key_hash=get_key_hash(plain_key),
        name="Test Service",
        user_id=sample_user.id,
        expires_at=datetime.utcnow() + timedelta(days=365),
        is_revoked=False,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    # Attach plain key for tests to use
    api_key.key = plain_key
    return api_key


@pytest.fixture
def auth_token(client, sample_user):
    """
    Get an authentication token for the sample user.
    """
    response = client.post(
        "/auth/login", json={"username": "testuser", "password": "testpass123"}
    )
    return response.json()["access_token"]
