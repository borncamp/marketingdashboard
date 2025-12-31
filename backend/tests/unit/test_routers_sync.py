"""
Unit tests for sync router.
"""
import pytest
from datetime import date


@pytest.mark.unit
class TestSyncRouter:
    """Test sync API endpoints."""

    def test_push_campaign_data_success(self, client):
        """Test pushing campaign data successfully."""
        sync_data = {
            "campaigns": [
                {
                    "id": "test-campaign-1",
                    "name": "Test Campaign",
                    "status": "ENABLED",
                    "platform": "google_ads",
                    "metrics": [
                        {
                            "date": str(date.today()),
                            "name": "clicks",
                            "value": 100,
                            "unit": "count"
                        },
                        {
                            "date": str(date.today()),
                            "name": "spend",
                            "value": 50.0,
                            "unit": "USD"
                        }
                    ]
                }
            ],
            "source": "google_ads_script"
        }

        response = client.post("/api/sync/push", json=sync_data)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['campaigns_processed'] == 1
        assert data['metrics_processed'] == 2

    def test_push_campaign_data_multiple_campaigns(self, client):
        """Test pushing multiple campaigns."""
        sync_data = {
            "campaigns": [
                {
                    "id": f"campaign-{i}",
                    "name": f"Campaign {i}",
                    "status": "ENABLED",
                    "metrics": [
                        {
                            "date": str(date.today()),
                            "name": "clicks",
                            "value": i * 10,
                            "unit": "count"
                        }
                    ]
                }
                for i in range(5)
            ]
        }

        response = client.post("/api/sync/push", json=sync_data)

        assert response.status_code == 200
        data = response.json()
        assert data['campaigns_processed'] == 5
        assert data['metrics_processed'] == 5

    def test_push_campaign_data_with_api_key(self, client, monkeypatch):
        """Test pushing data with API key authentication."""
        # Set API key requirement
        from app.config import settings
        monkeypatch.setattr(settings, 'sync_api_key', 'test-secret-key')

        sync_data = {
            "campaigns": [
                {
                    "id": "test-campaign",
                    "name": "Test",
                    "status": "ENABLED",
                    "metrics": []
                }
            ]
        }

        # Test with valid API key
        response = client.post(
            "/api/sync/push",
            json=sync_data,
            headers={"X-API-Key": "test-secret-key"}
        )

        assert response.status_code == 200

    def test_push_campaign_data_invalid_api_key(self, client, monkeypatch):
        """Test pushing data with invalid API key."""
        from app.config import settings
        monkeypatch.setattr(settings, 'sync_api_key', 'test-secret-key')

        sync_data = {
            "campaigns": [
                {
                    "id": "test-campaign",
                    "name": "Test",
                    "status": "ENABLED",
                    "metrics": []
                }
            ]
        }

        # Test with wrong API key
        response = client.post(
            "/api/sync/push",
            json=sync_data,
            headers={"X-API-Key": "wrong-key"}
        )

        assert response.status_code == 401

    def test_push_campaign_data_missing_api_key(self, client, monkeypatch):
        """Test pushing data without API key when required."""
        from app.config import settings
        monkeypatch.setattr(settings, 'sync_api_key', 'test-secret-key')

        sync_data = {
            "campaigns": [
                {
                    "id": "test-campaign",
                    "name": "Test",
                    "status": "ENABLED",
                    "metrics": []
                }
            ]
        }

        response = client.post("/api/sync/push", json=sync_data)

        assert response.status_code == 401

    def test_get_sync_status_no_data(self, client):
        """Test getting sync status when no sync has occurred."""
        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data['has_data'] is False

    def test_get_sync_status_with_data(self, client):
        """Test getting sync status after successful sync."""
        # First sync some data
        sync_data = {
            "campaigns": [
                {
                    "id": "test-campaign",
                    "name": "Test",
                    "status": "ENABLED",
                    "metrics": [
                        {
                            "date": str(date.today()),
                            "name": "clicks",
                            "value": 50,
                            "unit": "count"
                        }
                    ]
                }
            ]
        }

        client.post("/api/sync/push", json=sync_data)

        # Check status
        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data['has_data'] is True
        assert data['campaigns_count'] == 1
        assert data['metrics_count'] == 1
        assert data['status'] == 'success'

    def test_push_product_data_success(self, client):
        """Test pushing product data successfully."""
        sync_data = {
            "products": [
                {
                    "product_id": "product-123",
                    "product_title": "Test Product",
                    "campaign_id": "campaign-1",
                    "campaign_name": "Test Campaign",
                    "metrics": [
                        {
                            "date": str(date.today()),
                            "name": "clicks",
                            "value": 20,
                            "unit": "count"
                        }
                    ]
                }
            ],
            "source": "google_ads_script"
        }

        response = client.post("/api/sync/push-products", json=sync_data)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['products_processed'] == 1
        assert data['metrics_processed'] == 1

    def test_push_product_data_with_api_key(self, client, monkeypatch):
        """Test pushing product data with API key."""
        from app.config import settings
        monkeypatch.setattr(settings, 'sync_api_key', 'test-key')

        sync_data = {
            "products": [
                {
                    "product_id": "product-123",
                    "product_title": "Test",
                    "campaign_id": "campaign-1",
                    "metrics": []
                }
            ]
        }

        response = client.post(
            "/api/sync/push-products",
            json=sync_data,
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200

    def test_push_product_data_invalid_api_key(self, client, monkeypatch):
        """Test pushing product data with invalid API key."""
        from app.config import settings
        monkeypatch.setattr(settings, 'sync_api_key', 'test-key')

        sync_data = {
            "products": [
                {
                    "product_id": "product-123",
                    "product_title": "Test",
                    "campaign_id": "campaign-1",
                    "metrics": []
                }
            ]
        }

        response = client.post(
            "/api/sync/push-products",
            json=sync_data,
            headers={"X-API-Key": "wrong-key"}
        )

        assert response.status_code == 401

    def test_push_campaign_data_average_cpc_conversion(self, client):
        """Test that average_cpc is converted to cpc."""
        sync_data = {
            "campaigns": [
                {
                    "id": "test-campaign",
                    "name": "Test",
                    "status": "ENABLED",
                    "metrics": [
                        {
                            "date": str(date.today()),
                            "name": "average_cpc",
                            "value": 1500000,  # In micros
                            "unit": "count"
                        }
                    ]
                }
            ]
        }

        response = client.post("/api/sync/push", json=sync_data)

        assert response.status_code == 200

        # Verify it was stored as 'cpc' not 'average_cpc'
        from app.database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT metric_name, value, unit FROM campaign_metrics WHERE campaign_id = 'test-campaign'"
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == 'cpc'  # Should be 'cpc' not 'average_cpc'
            assert row[1] == 1.5  # Should be converted from micros
            assert row[2] == 'USD'  # Should be USD not count
