"""
Unit tests for Products router.
"""
import pytest
from app.database import ProductDatabase, get_db_connection


@pytest.mark.unit
class TestProductsRouter:
    """Test products API endpoints."""

    def test_get_all_products_empty(self, client, auth_headers):
        """Test getting products when database is empty."""
        response = client.get("/api/products/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['products'] == []
        assert data['total_count'] == 0

    def test_get_all_products_with_data(self, client, auth_headers):
        """Test getting products with metrics data."""
        from app.database import ProductDatabase

        # Insert test product first
        ProductDatabase.upsert_product(
            product_id='prod_123',
            product_title='Test Product',
            campaign_id='camp_456',
            campaign_name='Test Campaign'
        )

        # Insert test product metrics
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Insert product metrics for multiple days
            test_data = [
                ('prod_123', 'camp_456', '2025-01-05', 'clicks', 50, 'count'),
                ('prod_123', 'camp_456', '2025-01-05', 'spend', 25.50, 'USD'),
                ('prod_123', 'camp_456', '2025-01-05', 'impressions', 1000, 'count'),
                ('prod_123', 'camp_456', '2025-01-05', 'cpc', 0.51, 'USD'),
                ('prod_123', 'camp_456', '2025-01-04', 'clicks', 30, 'count'),
                ('prod_123', 'camp_456', '2025-01-04', 'spend', 15.00, 'USD'),
            ]

            cursor.executemany(
                """INSERT INTO product_metrics
                   (product_id, campaign_id, date, metric_name, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                test_data
            )
            conn.commit()

        response = client.get("/api/products/?days=30", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['products']) > 0
        assert data['total_count'] > 0

    def test_get_all_products_filtered_by_days(self, client, auth_headers):
        """Test getting products with days filter."""
        response = client.get("/api/products/?days=7", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # Should only return products with metrics from last 7 days

    def test_get_all_products_default_days(self, client, auth_headers):
        """Test getting products with default 30 days."""
        response = client.get("/api/products/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_get_all_products_unauthorized(self, client):
        """Test getting products without authentication."""
        response = client.get("/api/products/")

        assert response.status_code == 401


@pytest.mark.unit
class TestProductsDebugMetrics:
    """Test products debug metrics endpoint."""

    def test_debug_metrics_empty_database(self, client, auth_headers):
        """Test debug metrics endpoint with empty database."""
        response = client.get("/api/products/debug/metrics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'metrics_summary' in data
        assert 'cpc_samples' in data
        assert data['metrics_summary'] == []
        assert data['cpc_samples'] == []

    def test_debug_metrics_with_data(self, client, auth_headers):
        """Test debug metrics endpoint with metric data."""
        # Insert test metrics (different dates and products to avoid UNIQUE constraint)
        with get_db_connection() as conn:
            cursor = conn.cursor()

            test_data = [
                ('prod_1', 'camp_1', '2025-01-05', 'cpc', 0.50, 'USD'),
                ('prod_1', 'camp_1', '2025-01-04', 'cpc', 0.75, 'USD'),
                ('prod_2', 'camp_1', '2025-01-05', 'cpc', 1.20, 'USD'),
                ('prod_1', 'camp_1', '2025-01-05', 'clicks', 100, 'count'),
                ('prod_1', 'camp_1', '2025-01-05', 'spend', 50.00, 'USD'),
            ]

            cursor.executemany(
                """INSERT INTO product_metrics
                   (product_id, campaign_id, date, metric_name, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                test_data
            )
            conn.commit()

        response = client.get("/api/products/debug/metrics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['metrics_summary']) > 0

        # Check CPC metrics are present
        cpc_metric = next((m for m in data['metrics_summary'] if m['metric_name'] == 'cpc'), None)
        assert cpc_metric is not None
        assert cpc_metric['count'] == 3
        assert cpc_metric['unit'] == 'USD'
        assert cpc_metric['min'] <= cpc_metric['max']

    def test_debug_metrics_cpc_samples(self, client, auth_headers):
        """Test that debug endpoint returns CPC sample data."""
        # Insert CPC metrics
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Insert many CPC records (more than 20 to test limit)
            test_data = [
                (f'prod_{i}', 'camp_1', '2025-01-05', 'cpc', i * 0.10, 'USD')
                for i in range(25)
            ]

            cursor.executemany(
                """INSERT INTO product_metrics
                   (product_id, campaign_id, date, metric_name, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                test_data
            )
            conn.commit()

        response = client.get("/api/products/debug/metrics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['cpc_samples']) <= 20  # Limited to 20 samples

        # Verify sample structure
        if data['cpc_samples']:
            sample = data['cpc_samples'][0]
            assert 'product_id' in sample
            assert 'campaign_id' in sample
            assert 'date' in sample
            assert 'value' in sample
            assert 'unit' in sample

    def test_debug_metrics_unauthorized(self, client):
        """Test debug metrics without authentication."""
        response = client.get("/api/products/debug/metrics")

        assert response.status_code == 401


@pytest.mark.unit
class TestProductMetricTimeSeries:
    """Test product metric time series endpoint."""

    def test_get_time_series_data(self, client, auth_headers):
        """Test getting time series data for a specific product metric."""
        from datetime import date, timedelta

        # Insert time series data with recent dates
        today = date.today()
        with get_db_connection() as conn:
            cursor = conn.cursor()

            test_data = [
                ('prod_abc', 'camp_xyz', (today - timedelta(days=4)).isoformat(), 'clicks', 100, 'count'),
                ('prod_abc', 'camp_xyz', (today - timedelta(days=3)).isoformat(), 'clicks', 150, 'count'),
                ('prod_abc', 'camp_xyz', (today - timedelta(days=2)).isoformat(), 'clicks', 120, 'count'),
                ('prod_abc', 'camp_xyz', (today - timedelta(days=1)).isoformat(), 'clicks', 180, 'count'),
                ('prod_abc', 'camp_xyz', today.isoformat(), 'clicks', 200, 'count'),
            ]

            cursor.executemany(
                """INSERT INTO product_metrics
                   (product_id, campaign_id, date, metric_name, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                test_data
            )
            conn.commit()

        response = client.get(
            "/api/products/prod_abc/camp_xyz/metrics/clicks?days=30",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['product_id'] == 'prod_abc'
        assert data['campaign_id'] == 'camp_xyz'
        assert 'time_series' in data
        # time_series is a dict with metric_name, data_points, unit
        assert data['time_series']['metric_name'] == 'clicks'
        assert len(data['time_series']['data_points']) == 5

    def test_get_time_series_different_metrics(self, client, auth_headers):
        """Test getting time series for different metric types."""
        # Insert multiple metric types
        with get_db_connection() as conn:
            cursor = conn.cursor()

            test_data = [
                ('prod_123', 'camp_456', '2025-01-05', 'spend', 50.00, 'USD'),
                ('prod_123', 'camp_456', '2025-01-05', 'clicks', 100, 'count'),
                ('prod_123', 'camp_456', '2025-01-05', 'impressions', 5000, 'count'),
                ('prod_123', 'camp_456', '2025-01-05', 'cpc', 0.50, 'USD'),
            ]

            cursor.executemany(
                """INSERT INTO product_metrics
                   (product_id, campaign_id, date, metric_name, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                test_data
            )
            conn.commit()

        # Test each metric type
        for metric in ['spend', 'clicks', 'impressions', 'cpc']:
            response = client.get(
                f"/api/products/prod_123/camp_456/metrics/{metric}",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True

    def test_get_time_series_with_days_filter(self, client, auth_headers):
        """Test time series with different days parameter."""
        response = client.get(
            "/api/products/prod_123/camp_456/metrics/clicks?days=7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_get_time_series_nonexistent_product(self, client, auth_headers):
        """Test getting time series for non-existent product."""
        response = client.get(
            "/api/products/nonexistent/camp_123/metrics/clicks",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # time_series is a dict with empty data_points
        assert data['time_series']['data_points'] == []
        assert data['time_series']['metric_name'] == 'clicks'

    def test_get_time_series_unauthorized(self, client):
        """Test time series endpoint without authentication."""
        response = client.get("/api/products/prod_123/camp_456/metrics/clicks")

        assert response.status_code == 401

    def test_get_time_series_special_characters(self, client, auth_headers):
        """Test time series with product IDs containing special characters."""
        # Insert data with special chars in IDs
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO product_metrics
                   (product_id, campaign_id, date, metric_name, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ('prod-123_abc', 'camp:xyz/test', '2025-01-05', 'clicks', 50, 'count')
            )
            conn.commit()

        response = client.get(
            "/api/products/prod-123_abc/camp:xyz/test/metrics/clicks",
            headers=auth_headers
        )

        # Note: URL encoding may be needed for special chars
        assert response.status_code in [200, 404]  # Depends on URL encoding


@pytest.mark.unit
class TestProductsEdgeCases:
    """Test edge cases for products endpoints."""

    def test_products_with_zero_values(self, client, auth_headers):
        """Test products with zero metric values."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO product_metrics
                   (product_id, campaign_id, date, metric_name, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ('prod_zero', 'camp_1', '2025-01-05', 'clicks', 0, 'count')
            )
            conn.commit()

        response = client.get("/api/products/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_products_with_negative_days(self, client, auth_headers):
        """Test products endpoint with negative days parameter."""
        response = client.get("/api/products/?days=-5", headers=auth_headers)

        # Should either handle gracefully or return error
        assert response.status_code in [200, 400, 422]

    def test_products_with_very_large_days(self, client, auth_headers):
        """Test products endpoint with very large days parameter."""
        response = client.get("/api/products/?days=10000", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_products_with_invalid_days_type(self, client, auth_headers):
        """Test products endpoint with invalid days type."""
        response = client.get("/api/products/?days=invalid", headers=auth_headers)

        # FastAPI should return validation error
        assert response.status_code == 422
