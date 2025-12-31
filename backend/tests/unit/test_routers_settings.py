"""
Unit tests for settings router.
"""
import pytest
from app.database import SettingsDatabase
from app.services.settings_manager import settings_manager


@pytest.mark.unit
class TestSettingsRouter:
    """Test settings API endpoints."""

    def test_get_settings_status_not_configured(self, client, auth_headers):
        """Test getting settings status when not configured."""
        response = client.get("/api/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is False
        assert data['has_google_ads'] is False

    def test_get_settings_status_configured(self, client, auth_headers):
        """Test getting settings status when configured."""
        # Save test settings
        SettingsDatabase.set_setting('google_ads_customer_id', '1234567890')
        SettingsDatabase.set_setting('google_ads_developer_token', 'test-token')
        SettingsDatabase.set_setting('google_ads_client_id', 'test-client-id')
        SettingsDatabase.set_setting('google_ads_client_secret', 'test-secret')
        SettingsDatabase.set_setting('google_ads_refresh_token', 'test-refresh')

        response = client.get("/api/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['configured'] is True
        assert data['has_google_ads'] is True
        assert 'customer_id_masked' in data
        assert '****' in data['customer_id_masked']

    def test_update_settings(self, client, auth_headers):
        """Test updating settings."""
        settings_data = {
            "google_ads": {
                "customer_id": "1234567890",
                "developer_token": "test-dev-token",
                "client_id": "test-client-id.apps.googleusercontent.com",
                "client_secret": "test-client-secret",
                "refresh_token": "test-refresh-token"
            }
        }

        response = client.post(
            "/api/settings",
            json=settings_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'customer_id_masked' in data

    def test_update_settings_unauthorized(self, client):
        """Test updating settings without auth."""
        settings_data = {
            "google_ads": {
                "customer_id": "1234567890",
                "developer_token": "test-token",
                "client_id": "test-id",
                "client_secret": "test-secret",
                "refresh_token": "test-refresh"
            }
        }

        response = client.post("/api/settings", json=settings_data)

        assert response.status_code == 401

    def test_validate_settings(self, client, auth_headers, monkeypatch):
        """Test validating settings without saving."""
        # Mock the GoogleAdsAdapter to avoid actual API calls
        class MockAdapter:
            def __init__(self, *args, **kwargs):
                pass

            def test_connection(self):
                return True

        import app.routers.settings
        monkeypatch.setattr(app.routers.settings, 'GoogleAdsAdapter', MockAdapter)

        settings_data = {
            "customer_id": "1234567890",
            "developer_token": "test-token",
            "client_id": "test-id",
            "client_secret": "test-secret",
            "refresh_token": "test-refresh"
        }

        response = client.post(
            "/api/settings/validate",
            json=settings_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'valid' in data or 'success' in data

    def test_delete_settings(self, client, auth_headers):
        """Test deleting settings."""
        # First create some settings
        SettingsDatabase.set_setting('google_ads_customer_id', '1234567890')

        response = client.delete("/api/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_change_password(self, client, auth_headers):
        """Test changing user password."""
        password_data = {
            "current_password": "admin",
            "new_password": "newpassword123"
        }

        response = client.post(
            "/api/settings/change-password",
            json=password_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_change_password_wrong_current(self, client, auth_headers):
        """Test changing password with wrong current password."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }

        response = client.post(
            "/api/settings/change-password",
            json=password_data,
            headers=auth_headers
        )

        assert response.status_code == 400 or response.status_code == 401

    def test_get_shopify_settings(self, client, auth_headers):
        """Test getting Shopify settings."""
        # Save Shopify settings
        SettingsDatabase.set_setting('shopify_shop_name', 'test-shop')
        SettingsDatabase.set_setting('shopify_access_token', 'test-token')

        response = client.get("/api/shopify/credentials", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert 'shop_url' in data or 'configured' in data

    def test_update_shopify_settings(self, client, auth_headers):
        """Test updating Shopify settings."""
        shopify_data = {
            "shop_name": "test-shop",
            "access_token": "test-access-token"
        }

        response = client.post(
            "/api/shopify/credentials",
            json=shopify_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_delete_shopify_settings(self, client, auth_headers):
        """Test deleting Shopify settings."""
        # First create settings
        SettingsDatabase.set_setting('shopify_shop_name', 'test-shop')

        response = client.delete("/api/shopify/credentials", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True


@pytest.mark.unit
class TestProductsRouter:
    """Test products API endpoints."""

    def test_get_products_empty(self, client, auth_headers):
        """Test getting products when none exist."""
        response = client.get("/api/products", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert 'products' in data
        assert data['products'] == []
        assert data['total_count'] == 0

    def test_get_products_with_data(self, client, auth_headers):
        """Test getting products with data."""
        from app.database import ProductDatabase
        from datetime import date

        # Create test product
        ProductDatabase.upsert_product(
            "product-123",
            "Test Product",
            "campaign-1",
            "Test Campaign"
        )

        # Add metrics
        ProductDatabase.upsert_product_metric(
            "product-123",
            "campaign-1",
            str(date.today()),
            "clicks",
            50.0,
            "count"
        )

        response = client.get("/api/products", headers=auth_headers)

        assert response.status_code == 200
        products = response.json()
        assert len(products) >= 1

    def test_get_products_unauthorized(self, client):
        """Test getting products without auth."""
        response = client.get("/api/products")

        assert response.status_code == 401

    def test_get_product_metrics(self, client, auth_headers):
        """Test getting time series for specific product."""
        from app.database import ProductDatabase
        from datetime import date, timedelta

        # Create product with time series
        ProductDatabase.upsert_product("product-123", "Test", "campaign-1")

        for i in range(5):
            day = date.today() - timedelta(days=i)
            ProductDatabase.upsert_product_metric(
                "product-123",
                "campaign-1",
                str(day),
                "spend",
                float(i * 10),
                "USD"
            )

        response = client.get(
            "/api/products/product-123/campaign-1/metrics/spend?days=7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['product_id'] == "product-123"
        assert data['campaign_id'] == "campaign-1"
        assert 'time_series' in data
        # time_series should have metric data
        if data['time_series']:
            assert data['time_series']['metric_name'] == "spend"
            assert len(data['time_series']['data_points']) == 5
