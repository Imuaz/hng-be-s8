"""
Tests for protected routes with different authentication types.
"""

import pytest
from fastapi import status


class TestProtectedUserOnly:
    """Tests for JWT-only protected route."""

    def test_access_with_jwt(self, client, auth_token):
        """Test accessing user-only route with JWT token."""
        response = client.get(
            "/protected/user", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "testuser" in data["message"].lower()
        assert "user_id" in data

    def test_access_without_auth(self, client):
        """Test accessing user-only route without authentication."""
        response = client.get("/protected/user")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_with_api_key(self, client, sample_api_key):
        """Test that API key cannot access JWT-only route."""
        response = client.get(
            "/protected/user", headers={"x-api-key": sample_api_key.key}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedServiceOnly:
    """Tests for API-key-only protected route."""

    def test_access_with_api_key(self, client, sample_api_key):
        """Test accessing service-only route with API key."""
        response = client.get(
            "/protected/service", headers={"x-api-key": sample_api_key.key}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "service" in data["message"].lower()
        assert data["service_name"] == "Test Service"

    def test_access_without_auth(self, client):
        """Test accessing service-only route without authentication."""
        response = client.get("/protected/service")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_with_jwt(self, client, auth_token):
        """Test that JWT cannot access API-key-only route."""
        response = client.get(
            "/protected/service", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedAnyAuth:
    """Tests for route accepting either JWT or API key."""

    def test_access_with_jwt(self, client, auth_token):
        """Test accessing flexible route with JWT token."""
        response = client.get(
            "/protected/any", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["auth_type"] == "JWT Bearer Token"
        assert "user" in data["message"].lower()

    def test_access_with_api_key(self, client, sample_api_key):
        """Test accessing flexible route with API key."""
        response = client.get(
            "/protected/any", headers={"x-api-key": sample_api_key.key}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["auth_type"] == "API Key"
        assert "service" in data["message"].lower()

    def test_access_without_auth(self, client):
        """Test accessing flexible route without any authentication."""
        response = client.get("/protected/any")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
