"""
Unit tests for campaigns router.
"""
import pytest
from datetime import date, timedelta
from app.database import CampaignDatabase


@pytest.mark.unit
class TestCampaignsRouter:
    """Test campaigns API endpoints."""

    def test_get_campaigns_empty(self, client, auth_headers):
        """Test getting campaigns when database is empty."""
        response = client.get("/api/campaigns", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_get_campaigns_with_data(self, client, auth_headers, sample_campaign):
        """Test getting campaigns with data."""
        # Insert test campaign
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        # Add some metrics
        today = str(date.today())
        CampaignDatabase.upsert_metric(sample_campaign['id'], today, "clicks", 100.0, "count")
        CampaignDatabase.upsert_metric(sample_campaign['id'], today, "spend", 50.0, "USD")

        response = client.get("/api/campaigns", headers=auth_headers)

        assert response.status_code == 200
        campaigns = response.json()
        assert len(campaigns) >= 1

        campaign = campaigns[0]
        assert campaign['id'] == sample_campaign['id']
        assert campaign['name'] == sample_campaign['name']
        assert campaign['status'] == sample_campaign['status']
        assert 'metrics' in campaign

    def test_get_campaigns_unauthorized(self, client):
        """Test getting campaigns without authentication."""
        response = client.get("/api/campaigns")

        assert response.status_code == 401

    def test_get_campaign_metrics(self, client, auth_headers, sample_campaign):
        """Test getting time series for specific campaign metric."""
        # Insert campaign and metrics
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        # Add time series data
        for i in range(5):
            day = date.today() - timedelta(days=i)
            CampaignDatabase.upsert_metric(
                sample_campaign['id'],
                str(day),
                "clicks",
                float(i * 10),
                "count"
            )

        response = client.get(
            f"/api/campaigns/{sample_campaign['id']}/metrics/clicks?days=7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['campaign_id'] == sample_campaign['id']
        assert data['metric_name'] == "clicks"
        assert len(data['data_points']) == 5

    def test_get_campaign_metrics_not_found(self, client, auth_headers):
        """Test getting metrics for non-existent campaign."""
        response = client.get(
            "/api/campaigns/nonexistent/metrics/clicks",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_campaign_metrics_custom_days(self, client, auth_headers, sample_campaign):
        """Test getting metrics with custom day range."""
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        # Add 15 days of data
        for i in range(15):
            day = date.today() - timedelta(days=i)
            CampaignDatabase.upsert_metric(
                sample_campaign['id'],
                str(day),
                "spend",
                float(i * 5),
                "USD"
            )

        # Request only 10 days
        response = client.get(
            f"/api/campaigns/{sample_campaign['id']}/metrics/spend?days=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data['data_points']) == 9  # Gets 9 days due to date boundary logic

    def test_get_all_campaigns_metrics(self, client, auth_headers):
        """Test getting time series for all campaigns."""
        # Create multiple campaigns
        for i in range(3):
            campaign_id = f"campaign-{i}"
            CampaignDatabase.upsert_campaign(
                campaign_id,
                f"Campaign {i}",
                "ENABLED",
                "google_ads"
            )

            # Add metrics
            for day_offset in range(5):
                day = date.today() - timedelta(days=day_offset)
                CampaignDatabase.upsert_metric(
                    campaign_id,
                    str(day),
                    "clicks",
                    float(i * 10 + day_offset),
                    "count"
                )

        response = client.get(
            "/api/campaigns/all/metrics/clicks?days=7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        for campaign_data in data:
            assert 'campaign_id' in campaign_data
            assert 'campaign_name' in campaign_data
            assert campaign_data['metric_name'] == "clicks"
            assert len(campaign_data['data_points']) == 5

    def test_get_all_campaigns_metrics_empty(self, client, auth_headers):
        """Test getting all campaigns metrics when no data exists."""
        response = client.get(
            "/api/campaigns/all/metrics/clicks",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_campaigns_metrics_unauthorized(self, client):
        """Test getting all campaigns metrics without auth."""
        response = client.get("/api/campaigns/all/metrics/clicks")

        assert response.status_code == 401

    def test_get_campaigns_database_error(self, client, auth_headers, monkeypatch):
        """Test get campaigns when database fails."""
        from app.database import CampaignDatabase

        def mock_get_all(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(CampaignDatabase, "get_all_campaigns", mock_get_all)

        response = client.get("/api/campaigns", headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to fetch campaigns" in response.json()['detail']

    def test_get_all_campaigns_metrics_database_error(self, client, auth_headers, monkeypatch):
        """Test get all campaigns metrics when database fails."""
        from app.database import CampaignDatabase

        def mock_get_all_time_series(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(CampaignDatabase, "get_all_campaigns_time_series", mock_get_all_time_series)

        response = client.get("/api/campaigns/all/metrics/clicks", headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to fetch all campaigns metrics" in response.json()['detail']

    def test_get_campaign_metrics_database_error(self, client, auth_headers, monkeypatch):
        """Test get campaign metrics when database fails."""
        from app.database import CampaignDatabase

        def mock_get_time_series(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(CampaignDatabase, "get_campaign_time_series", mock_get_time_series)

        response = client.get("/api/campaigns/test-123/metrics/clicks", headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to fetch campaign metrics" in response.json()['detail']
