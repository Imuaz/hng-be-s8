"""
Tests for authentication endpoints.
"""

import pytest
from fastapi import status


class TestSignup:
    """Tests for user signup endpoint."""

    def test_signup_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepass123",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert "created_at" in data
        assert data["is_active"] is True

    def test_signup_duplicate_email(self, client, sample_user):
        """Test signup with duplicate email."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",  # Already exists
                "username": "differentuser",
                "password": "password123",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_duplicate_username(self, client, sample_user):
        """Test signup with duplicate username."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "different@example.com",
                "username": "testuser",  # Already exists
                "password": "password123",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already taken" in response.json()["detail"].lower()

    def test_signup_invalid_email(self, client):
        """Test signup with invalid email format."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "not-an-email",
                "username": "newuser",
                "password": "password123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_short_password(self, client):
        """Test signup with password shorter than minimum."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "short",  # Less than 6 characters
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client, sample_user):
        """Test successful login."""
        response = client.post(
            "/auth/login", json={"username": "testuser", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, sample_user):
        """Test login with incorrect password."""
        response = client.post(
            "/auth/login", json={"username": "testuser", "password": "wrongpassword"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent username."""
        response = client.post(
            "/auth/login", json={"username": "nonexistent", "password": "password123"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, client, sample_user, db):
        """Test login with inactive user account."""
        # Deactivate user
        sample_user.is_active = False
        db.commit()

        response = client.post(
            "/auth/login", json={"username": "testuser", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inactive" in response.json()["detail"].lower()
