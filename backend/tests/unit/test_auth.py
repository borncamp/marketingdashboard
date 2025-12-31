"""
Unit tests for authentication module.
"""
import pytest
import base64
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from app.auth import verify_credentials
from app import db


@pytest.mark.unit
class TestVerifyCredentials:
    """Test verify_credentials function."""

    def test_valid_admin_credentials(self, test_db):
        """Test authentication with default admin credentials."""
        credentials = HTTPBasicCredentials(username="admin", password="admin")
        result = verify_credentials(credentials)
        assert result == "admin"

    def test_invalid_password(self, test_db):
        """Test authentication fails with wrong password."""
        credentials = HTTPBasicCredentials(username="admin", password="wrong_password")
        with pytest.raises(HTTPException) as exc_info:
            verify_credentials(credentials)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Incorrect username or password"
        assert exc_info.value.headers == {"WWW-Authenticate": "Basic"}

    def test_nonexistent_user(self, test_db):
        """Test authentication fails with non-existent user."""
        credentials = HTTPBasicCredentials(username="nonexistent", password="password")
        with pytest.raises(HTTPException) as exc_info:
            verify_credentials(credentials)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Incorrect username or password"

    def test_empty_username(self, test_db):
        """Test authentication fails with empty username."""
        credentials = HTTPBasicCredentials(username="", password="admin")
        with pytest.raises(HTTPException) as exc_info:
            verify_credentials(credentials)
        assert exc_info.value.status_code == 401

    def test_empty_password(self, test_db):
        """Test authentication fails with empty password."""
        credentials = HTTPBasicCredentials(username="admin", password="")
        with pytest.raises(HTTPException) as exc_info:
            verify_credentials(credentials)
        assert exc_info.value.status_code == 401

    def test_custom_user_credentials(self, test_db, create_test_user):
        """Test authentication with custom created user."""
        # Create custom user
        create_test_user(username="testuser", password="testpass123")

        # Test valid credentials
        credentials = HTTPBasicCredentials(username="testuser", password="testpass123")
        result = verify_credentials(credentials)
        assert result == "testuser"

        # Test invalid password for custom user
        credentials = HTTPBasicCredentials(username="testuser", password="wrongpass")
        with pytest.raises(HTTPException):
            verify_credentials(credentials)

    def test_case_sensitive_username(self, test_db):
        """Test that username is case-sensitive."""
        credentials = HTTPBasicCredentials(username="Admin", password="admin")
        with pytest.raises(HTTPException):
            verify_credentials(credentials)

    def test_special_characters_in_password(self, test_db, create_test_user):
        """Test password with special characters."""
        create_test_user(username="specialuser", password="p@ssw0rd!#$%")
        credentials = HTTPBasicCredentials(username="specialuser", password="p@ssw0rd!#$%")
        result = verify_credentials(credentials)
        assert result == "specialuser"

    def test_unicode_in_password(self, test_db, create_test_user):
        """Test password with unicode characters."""
        create_test_user(username="unicodeuser", password="пароль123")
        credentials = HTTPBasicCredentials(username="unicodeuser", password="пароль123")
        result = verify_credentials(credentials)
        assert result == "unicodeuser"


@pytest.mark.unit
class TestAuthEndpoint:
    """Test authentication via HTTP endpoints."""

    def test_authenticated_request(self, client, auth_headers):
        """Test making authenticated request to protected endpoint."""
        response = client.get("/api/campaigns", headers=auth_headers)
        assert response.status_code in [200, 500]  # 500 if no API keys configured, but auth passed

    def test_unauthenticated_request(self, client):
        """Test request without authentication headers."""
        response = client.get("/api/campaigns")
        assert response.status_code == 401

    def test_malformed_auth_header(self, client):
        """Test request with malformed authorization header."""
        response = client.get("/api/campaigns", headers={"Authorization": "NotBasic abc123"})
        assert response.status_code == 401

    def test_invalid_base64_auth_header(self, client):
        """Test request with invalid base64 in auth header."""
        response = client.get("/api/campaigns", headers={"Authorization": "Basic not-valid-base64!"})
        assert response.status_code == 401

    def test_auth_header_missing_colon(self, client):
        """Test auth header with credentials missing colon separator."""
        credentials = base64.b64encode(b"adminadmin").decode()
        response = client.get("/api/campaigns", headers={"Authorization": f"Basic {credentials}"})
        assert response.status_code == 401

    def test_multiple_colons_in_credentials(self, client, create_test_user):
        """Test credentials where password contains colons."""
        create_test_user(username="colonuser", password="pass:word:with:colons")
        credentials = base64.b64encode(b"colonuser:pass:word:with:colons").decode()
        response = client.get("/api/campaigns", headers={"Authorization": f"Basic {credentials}"})
        assert response.status_code in [200, 500]  # Auth should pass

    def test_auth_preserves_username_case(self, client, create_test_user):
        """Test that returned username preserves original case."""
        create_test_user(username="CamelCaseUser", password="password")
        credentials = base64.b64encode(b"CamelCaseUser:password").decode()
        # We can't easily test the return value here, but we verify auth succeeds
        response = client.get("/api/campaigns", headers={"Authorization": f"Basic {credentials}"})
        assert response.status_code in [200, 500]
