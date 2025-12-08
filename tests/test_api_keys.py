"""
Tests for API key management endpoints.
"""

import pytest
from fastapi import status
from datetime import datetime, timedelta


class TestCreateAPIKey:
    """Tests for API key creation endpoint."""

    def test_create_api_key_success(self, client, auth_token):
        """Test successful API key creation."""
        response = client.post(
            "/keys/create",
            json={"name": "My Test Service"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "My Test Service"
        assert data["key"].startswith("sk_")
        assert "id" in data
        assert "created_at" in data
        assert "expires_at" in data
        assert data["is_revoked"] is False

    def test_create_api_key_custom_expiration(self, client, auth_token):
        """Test API key creation with custom expiration."""
        response = client.post(
            "/keys/create",
            json={"name": "Short-lived Key", "expires_in_days": 30},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify expiration is approximately 30 days from now
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        delta = expires_at - created_at
        assert 29 <= delta.days <= 31  # Allow some tolerance

    def test_create_api_key_no_auth(self, client):
        """Test API key creation without authentication."""
        response = client.post("/keys/create", json={"name": "Test Service"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_api_key_with_api_key_auth(self, client, sample_api_key):
        """Test that API keys cannot be created using API key auth."""
        response = client.post(
            "/keys/create",
            json={"name": "New Service"},
            headers={"x-api-key": sample_api_key.key},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_api_key_name(self, client, auth_token, sample_api_key):
        """Test creating an API key with a name that already exists."""
        # sample_api_key already exists with name "Test Service"
        response = client.post(
            "/keys/create",
            json={"name": "Test Service"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]


class TestListAPIKeys:
    """Tests for listing API keys endpoint."""

    def test_list_api_keys_success(self, client, auth_token, sample_api_key):
        """Test successful listing of API keys."""
        response = client.get(
            "/keys", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check first key
        key = data[0]
        assert "name" in key
        assert "id" in key
        assert "created_at" in key
        assert "expires_at" in key

    def test_list_api_keys_no_auth(self, client):
        """Test listing API keys without authentication."""
        response = client.get("/keys")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_api_keys_empty(self, client, auth_token):
        """Test listing when user has no API keys."""
        response = client.get(
            "/keys", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestRevokeAPIKey:
    """Tests for API key revocation endpoint."""

    def test_delete_api_key_success(self, client, auth_token, sample_api_key):
        """Test successful API key deletion."""
        response = client.delete(
            f"/keys/{sample_api_key.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deleted successfully" in data["message"].lower()

    def test_revoke_api_key_not_found(self, client, auth_token):
        """Test revoking non-existent API key."""
        import uuid

        random_id = uuid.uuid4()
        response = client.delete(
            f"/keys/{random_id}", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_api_key_no_auth(self, client, sample_api_key):
        """Test revoking API key without authentication."""
        response = client.delete(f"/keys/{sample_api_key.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
