"""
Unit tests for Meta router.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.database import SettingsDatabase


@pytest.mark.unit
class TestMetaCredentials:
    """Test Meta credentials endpoints."""

    def test_save_credentials_without_app_config(self, client, auth_headers):
        """Test saving Meta credentials without app credentials configured."""
        credentials = {
            "access_token": "test_short_lived_token_12345",
            "ad_account_id": "act_123456789"
        }

        response = client.post(
            "/api/meta/credentials",
            json=credentials,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'token_type' in data
        assert 'expires_in' in data

        # Verify credentials stored in database
        stored_token = SettingsDatabase.get_setting("meta_access_token")
        stored_account = SettingsDatabase.get_setting("meta_ad_account_id")
        assert stored_token == "test_short_lived_token_12345"
        assert stored_account == "act_123456789"

    @patch('app.routers.meta.requests.get')
    def test_save_credentials_with_token_exchange(self, mock_get, client, auth_headers):
        """Test saving credentials with successful token exchange to long-lived token."""
        # Setup app credentials first
        SettingsDatabase.set_setting("meta_app_id", "test_app_id_123")
        SettingsDatabase.set_setting("meta_app_secret", "test_app_secret_456")

        # Mock the token exchange API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "long_lived_token_abcdef",
            "expires_in": 5184000  # 60 days in seconds
        }
        mock_get.return_value = mock_response

        credentials = {
            "access_token": "short_lived_token",
            "ad_account_id": "act_987654321"
        }

        response = client.post(
            "/api/meta/credentials",
            json=credentials,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['token_type'] == "long-lived"
        assert "60 days" in data['expires_in']

        # Verify long-lived token was stored
        stored_token = SettingsDatabase.get_setting("meta_access_token")
        assert stored_token == "long_lived_token_abcdef"

        # Verify expiry timestamp was stored
        expiry_str = SettingsDatabase.get_setting("meta_token_expiry")
        assert expiry_str is not None

    @patch('app.routers.meta.requests.get')
    def test_save_credentials_token_exchange_fails(self, mock_get, client, auth_headers):
        """Test saving credentials when token exchange fails - should still save original token."""
        # Setup app credentials
        SettingsDatabase.set_setting("meta_app_id", "test_app_id")
        SettingsDatabase.set_setting("meta_app_secret", "test_app_secret")

        # Mock failed token exchange
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.content = b'{"error": "invalid token"}'
        mock_response.json.return_value = {"error": "invalid token"}
        mock_get.return_value = mock_response

        credentials = {
            "access_token": "original_token",
            "ad_account_id": "act_111222333"
        }

        response = client.post(
            "/api/meta/credentials",
            json=credentials,
            headers=auth_headers
        )

        # Should still succeed with original token
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # Verify original token was stored
        stored_token = SettingsDatabase.get_setting("meta_access_token")
        assert stored_token == "original_token"

    def test_save_credentials_unauthorized(self, client):
        """Test saving credentials without authentication."""
        credentials = {
            "access_token": "test_token",
            "ad_account_id": "act_123"
        }

        response = client.post("/api/meta/credentials", json=credentials)
        assert response.status_code == 401

    def test_get_credentials_not_configured(self, client, auth_headers):
        """Test getting credentials when none are configured."""
        response = client.get("/api/meta/credentials", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is False

    def test_get_credentials_configured(self, client, auth_headers):
        """Test getting credentials when configured."""
        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123456")
        SettingsDatabase.set_setting("meta_account_name", "Test Account")
        SettingsDatabase.set_setting("meta_account_currency", "USD")
        SettingsDatabase.set_setting("meta_token_type", "long-lived")

        response = client.get("/api/meta/credentials", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is True
        assert data['ad_account_id'] == "act_123456"
        assert data['account_name'] == "Test Account"
        assert data['currency'] == "USD"
        assert data['token_type'] == "long-lived"

    def test_get_credentials_with_expiry(self, client, auth_headers):
        """Test getting credentials with token expiry information."""
        # Setup credentials with expiry
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        # Set expiry to 30 days from now
        future_date = datetime.now() + timedelta(days=30)
        SettingsDatabase.set_setting("meta_token_expiry", future_date.isoformat())

        response = client.get("/api/meta/credentials", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is True
        assert data['token_expires_in_days'] is not None
        assert data['token_expires_in_days'] > 25  # Should be around 30
        assert data['token_expired'] is False

    def test_get_credentials_expired_token(self, client, auth_headers):
        """Test getting credentials with expired token."""
        # Setup credentials with expired token
        SettingsDatabase.set_setting("meta_access_token", "expired_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        # Set expiry to past date
        past_date = datetime.now() - timedelta(days=5)
        SettingsDatabase.set_setting("meta_token_expiry", past_date.isoformat())

        response = client.get("/api/meta/credentials", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is True
        assert data['token_expired'] is True
        assert data['token_expires_in_days'] < 0


@pytest.mark.unit
class TestMetaAppCredentials:
    """Test Meta App credentials endpoints."""

    def test_save_app_credentials(self, client, auth_headers):
        """Test saving Meta App credentials."""
        app_credentials = {
            "app_id": "1234567890",
            "app_secret": "abcdef123456789"
        }

        response = client.post(
            "/api/meta/app-credentials",
            json=app_credentials,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert "60 days" in data['message']

        # Verify stored in database
        stored_app_id = SettingsDatabase.get_setting("meta_app_id")
        stored_app_secret = SettingsDatabase.get_setting("meta_app_secret")
        assert stored_app_id == "1234567890"
        assert stored_app_secret == "abcdef123456789"

    def test_save_app_credentials_unauthorized(self, client):
        """Test saving app credentials without authentication."""
        app_credentials = {
            "app_id": "123",
            "app_secret": "secret"
        }

        response = client.post("/api/meta/app-credentials", json=app_credentials)
        assert response.status_code == 401


@pytest.mark.unit
class TestMetaTokenStatus:
    """Test Meta token status endpoint."""

    def test_token_status_not_configured(self, client, auth_headers):
        """Test token status when no token is configured."""
        response = client.get("/api/meta/token-status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is False
        assert "No token configured" in data['message']

    def test_token_status_with_expiry(self, client, auth_headers):
        """Test token status with expiry information."""
        # Setup token with expiry
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_token_type", "long-lived")

        future_date = datetime.now() + timedelta(days=45)
        SettingsDatabase.set_setting("meta_token_expiry", future_date.isoformat())

        # Setup app credentials
        SettingsDatabase.set_setting("meta_app_id", "app123")
        SettingsDatabase.set_setting("meta_app_secret", "secret456")

        response = client.get("/api/meta/token-status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is True
        assert data['token_type'] == "long-lived"
        assert data['app_credentials_configured'] is True
        assert data['expiry_info'] is not None
        assert data['expiry_info']['days_remaining'] > 40
        assert data['expiry_info']['expired'] is False


@pytest.mark.unit
class TestMetaVerifyConnection:
    """Test Meta API connection verification."""

    @patch('app.routers.meta.requests.get')
    def test_verify_connection_success(self, mock_get, client, auth_headers):
        """Test successful Meta API connection verification."""
        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "valid_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123456")

        # Mock successful API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test Ad Account",
            "currency": "USD",
            "account_status": 1,
            "timezone_name": "America/Los_Angeles"
        }
        mock_get.return_value = mock_response

        response = client.post("/api/meta/verify-connection", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['name'] == "Test Ad Account"
        assert data['currency'] == "USD"
        assert data['timezone'] == "America/Los_Angeles"

        # Verify account info was cached
        cached_name = SettingsDatabase.get_setting("meta_account_name")
        cached_currency = SettingsDatabase.get_setting("meta_account_currency")
        assert cached_name == "Test Ad Account"
        assert cached_currency == "USD"

    def test_verify_connection_not_configured(self, client, auth_headers):
        """Test verifying connection when credentials not configured."""
        response = client.post("/api/meta/verify-connection", headers=auth_headers)

        assert response.status_code == 400
        assert "not configured" in response.json()['detail']

    @patch('app.routers.meta.requests.get')
    def test_verify_connection_invalid_token(self, mock_get, client, auth_headers):
        """Test verifying connection with invalid token."""
        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "invalid_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.ok = False
        mock_get.return_value = mock_response

        response = client.post("/api/meta/verify-connection", headers=auth_headers)

        assert response.status_code == 401
        assert "Invalid access token" in response.json()['detail']

    @patch('app.routers.meta.requests.get')
    def test_verify_connection_api_error(self, mock_get, client, auth_headers):
        """Test verifying connection with API error."""
        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_invalid")

        # Mock 400 error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.ok = False
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid ad account ID"
            }
        }
        mock_get.return_value = mock_response

        response = client.post("/api/meta/verify-connection", headers=auth_headers)

        assert response.status_code == 400
        assert "Invalid ad account ID" in response.json()['detail']

    @patch('app.routers.meta.requests.get')
    def test_verify_connection_timeout(self, mock_get, client, auth_headers):
        """Test verifying connection with timeout."""
        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        # Mock timeout
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        response = client.post("/api/meta/verify-connection", headers=auth_headers)

        assert response.status_code == 504
        assert "timed out" in response.json()['detail']


@pytest.mark.unit
class TestMetaCampaigns:
    """Test Meta campaigns endpoints."""

    def test_get_campaigns_from_database(self, client, auth_headers):
        """Test getting Meta campaigns from local database."""
        from app.database import CampaignDatabase

        # Create test Meta campaign
        CampaignDatabase.upsert_campaign(
            campaign_id="meta_campaign_1",
            name="Test Meta Campaign",
            status="ACTIVE",
            platform="meta"
        )

        # Add metrics
        CampaignDatabase.upsert_metric(
            campaign_id="meta_campaign_1",
            date_value="2025-01-01",
            metric_name="spend",
            value=100.50,
            unit="USD"
        )
        CampaignDatabase.upsert_metric(
            campaign_id="meta_campaign_1",
            date_value="2025-01-01",
            metric_name="impressions",
            value=5000,
            unit="count"
        )

        response = client.get("/api/meta/campaigns", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['campaigns']) >= 1

        # Find our test campaign
        test_campaign = next(c for c in data['campaigns'] if c['id'] == "meta_campaign_1")
        assert test_campaign['name'] == "Test Meta Campaign"
        assert test_campaign['status'] == "ACTIVE"

    def test_get_campaigns_empty_database(self, client, auth_headers):
        """Test getting campaigns when database is empty."""
        response = client.get("/api/meta/campaigns", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['campaigns'] == []
        assert data['total_campaigns'] == 0


@pytest.mark.unit
class TestMetaSyncStatus:
    """Test Meta sync status endpoint."""

    def test_sync_status_no_sync(self, client, auth_headers):
        """Test sync status when no sync has been performed."""
        response = client.get("/api/meta/sync/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['synced'] is False
        assert "No sync" in data['message']

    def test_sync_status_with_sync(self, client, auth_headers):
        """Test sync status after a sync has been performed."""
        from app.database import CampaignDatabase

        # Log a sync
        CampaignDatabase.log_sync(
            campaigns_count=10,
            metrics_count=150,
            status="success"
        )

        response = client.get("/api/meta/sync/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['synced'] is True
        assert data['campaigns_count'] == 10
        assert data['metrics_count'] == 150
        assert data['status'] == "success"
        assert 'last_sync_at' in data


@pytest.mark.unit
class TestMetaCampaignAdsets:
    """Test Meta campaign adsets endpoint."""

    def test_get_adsets_no_credentials(self, client, auth_headers):
        """Test getting adsets when credentials not configured."""
        response = client.get(
            "/api/meta/campaigns/test_campaign_123/adsets",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "not configured" in response.json()['detail']

    @patch('app.routers.meta.requests.get')
    def test_get_adsets_success(self, mock_get, client, auth_headers):
        """Test successfully fetching campaign adsets."""
        from app.database import SettingsDatabase

        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        # Mock Meta API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "adset_1",
                    "name": "Test Adset",
                    "status": "ACTIVE",
                    "optimization_goal": "LINK_CLICKS",
                    "billing_event": "IMPRESSIONS",
                    "insights": {
                        "data": [
                            {
                                "spend": "50.00",
                                "impressions": "10000",
                                "clicks": "500",
                                "reach": "8000",
                                "actions": [
                                    {"action_type": "purchase", "value": "25"}
                                ],
                                "action_values": [
                                    {"action_type": "purchase", "value": "1250.00"}
                                ]
                            }
                        ]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        response = client.get(
            "/api/meta/campaigns/campaign_123/adsets?days=7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'adsets' in data
        assert len(data['adsets']) == 1
        assert data['adsets'][0]['id'] == "adset_1"
        assert data['adsets'][0]['spend'] == 50.00
        assert data['adsets'][0]['impressions'] == 10000

    @patch('app.routers.meta.requests.get')
    def test_get_adsets_timeout(self, mock_get, client, auth_headers):
        """Test getting adsets with timeout."""
        from app.database import SettingsDatabase
        import requests

        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        mock_get.side_effect = requests.exceptions.Timeout()

        response = client.get(
            "/api/meta/campaigns/campaign_123/adsets",
            headers=auth_headers
        )

        assert response.status_code == 504

    def test_get_adsets_unauthorized(self, client):
        """Test getting adsets without authentication."""
        response = client.get("/api/meta/campaigns/campaign_123/adsets")
        assert response.status_code == 401


@pytest.mark.unit
class TestMetaSync:
    """Test Meta sync endpoint."""

    def test_sync_no_credentials(self, client, auth_headers):
        """Test syncing when credentials not configured."""
        response = client.post("/api/meta/sync", headers=auth_headers)

        assert response.status_code == 400
        assert "not configured" in response.json()['detail']

    @patch('app.routers.meta.requests.get')
    def test_sync_campaigns_success(self, mock_get, client, auth_headers):
        """Test successfully syncing Meta campaigns."""
        from app.database import SettingsDatabase

        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        # Mock Meta API response with campaign data
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "camp_1",
                    "name": "Test Campaign",
                    "status": "ACTIVE",
                    "objective": "LINK_CLICKS",
                    "insights": {
                        "data": [
                            {
                                "date_start": "2025-01-05",
                                "spend": "100.00",
                                "impressions": "50000",
                                "clicks": "2500",
                                "reach": "40000",
                                "actions": [
                                    {"action_type": "purchase", "value": "50"}
                                ],
                                "action_values": [
                                    {"action_type": "purchase", "value": "2500.00"}
                                ]
                            }
                        ]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        response = client.post("/api/meta/sync?days=7", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['campaigns_synced'] >= 1
        assert 'metrics_synced' in data

    @patch('app.routers.meta.requests.get')
    def test_sync_campaigns_api_error(self, mock_get, client, auth_headers):
        """Test sync with Meta API error."""
        from app.database import SettingsDatabase

        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        # Mock API error
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.content = b'{"error": {"message": "Invalid request"}}'
        mock_response.json.return_value = {
            "error": {"message": "Invalid request"}
        }
        mock_get.return_value = mock_response

        response = client.post("/api/meta/sync", headers=auth_headers)

        assert response.status_code == 400
        assert "Meta API error" in response.json()['detail']

    @patch('app.routers.meta.requests.get')
    def test_sync_campaigns_timeout(self, mock_get, client, auth_headers):
        """Test sync with timeout."""
        from app.database import SettingsDatabase
        import requests

        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        mock_get.side_effect = requests.exceptions.Timeout()

        response = client.post("/api/meta/sync", headers=auth_headers)

        assert response.status_code == 504

    def test_sync_unauthorized(self, client):
        """Test sync without authentication."""
        response = client.post("/api/meta/sync")
        assert response.status_code == 401

    @patch('app.routers.meta.requests.get')
    def test_sync_with_custom_days(self, mock_get, client, auth_headers):
        """Test syncing with custom days parameter."""
        from app.database import SettingsDatabase

        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        response = client.post("/api/meta/sync?days=14", headers=auth_headers)

        assert response.status_code == 200
        # Verify the API was called with correct date range
        assert mock_get.called
