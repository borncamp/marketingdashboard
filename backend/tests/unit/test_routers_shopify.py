"""
Unit tests for shopify router.
"""
import pytest
from datetime import date, timedelta
from app.database import ShopifyDatabase, ShippingDatabase


@pytest.mark.unit
class TestShopifyRouter:
    """Test Shopify API endpoints."""

    def test_push_shopify_data_success(self, client):
        """Test pushing Shopify daily metrics successfully."""
        sync_data = {
            "daily_metrics": [
                {
                    "date": str(date.today()),
                    "revenue": 150.0,
                    "shipping_revenue": 20.0,
                    "shipping_cost": 10.0,
                    "order_count": 5
                }
            ],
            "source": "shopify_script"
        }

        response = client.post("/api/shopify/push", json=sync_data)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['records_processed'] == 1

    def test_push_shopify_data_multiple_days(self, client):
        """Test pushing multiple days of data."""
        sync_data = {
            "daily_metrics": [
                {
                    "date": str(date.today() - timedelta(days=i)),
                    "revenue": float(i * 100),
                    "shipping_revenue": float(i * 10),
                    "shipping_cost": float(i * 5),
                    "order_count": i
                }
                for i in range(7)
            ]
        }

        response = client.post("/api/shopify/push", json=sync_data)

        assert response.status_code == 200
        data = response.json()
        assert data['records_processed'] == 7

    def test_push_shopify_data_with_api_key(self, client, monkeypatch):
        """Test pushing Shopify data with API key."""
        from app.config import settings
        monkeypatch.setattr(settings, 'sync_api_key', 'test-key')

        sync_data = {
            "daily_metrics": [
                {
                    "date": str(date.today()),
                    "revenue": 100.0,
                    "shipping_revenue": 10.0,
                    "shipping_cost": 5.0,
                    "order_count": 2
                }
            ]
        }

        response = client.post(
            "/api/shopify/push",
            json=sync_data,
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200

    def test_push_shopify_data_invalid_api_key(self, client, monkeypatch):
        """Test pushing data with invalid API key."""
        from app.config import settings
        monkeypatch.setattr(settings, 'sync_api_key', 'test-key')

        sync_data = {
            "daily_metrics": [
                {
                    "date": str(date.today()),
                    "revenue": 100.0,
                    "shipping_revenue": 10.0,
                    "shipping_cost": 5.0,
                    "order_count": 2
                }
            ]
        }

        response = client.post(
            "/api/shopify/push",
            json=sync_data,
            headers={"X-API-Key": "wrong-key"}
        )

        assert response.status_code == 401

    def test_get_shopify_metrics(self, client):
        """Test getting Shopify metrics summary."""
        from app.database import ShippingDatabase
        # Add some test data - create 2 orders per day for 7 days
        for i in range(7):
            day = date.today() - timedelta(days=i)
            for j in range(2):
                order = {
                    'id': f'order-{i}-{j}',
                    'order_number': i * 100 + j,
                    'order_date': str(day),
                    'customer_email': f'test{i}{j}@example.com',
                    'subtotal': 100.0,
                    'total_price': 110.0,
                    'shipping_charged': 10.0,
                    'shipping_cost_estimated': 5.0,
                    'currency': 'USD',
                    'financial_status': 'paid',
                    'fulfillment_status': 'fulfilled'
                }
                ShippingDatabase.upsert_order(order)

        response = client.get("/api/shopify/metrics?days=7")

        assert response.status_code == 200
        data = response.json()
        assert 'total_revenue' in data
        assert 'total_shipping_revenue' in data
        assert 'total_shipping_cost' in data
        assert 'total_orders' in data
        assert data['total_revenue'] == 1400.0  # 100 * 2 orders * 7 days
        assert data['total_shipping_revenue'] == 140.0  # 10 * 2 orders * 7 days
        assert data['total_orders'] == 14  # 2 orders * 7 days

    def test_get_shopify_metrics_custom_days(self, client):
        """Test getting metrics with custom day range."""
        from app.database import ShippingDatabase
        for i in range(30):
            day = date.today() - timedelta(days=i)
            order = {
                'id': f'order-{i}',
                'order_number': i,
                'order_date': str(day),
                'customer_email': f'test{i}@example.com',
                'subtotal': 50.0,
                'total_price': 55.0,
                'shipping_charged': 5.0,
                'shipping_cost_estimated': 2.0,
                'currency': 'USD',
                'financial_status': 'paid',
                'fulfillment_status': 'fulfilled'
            }
            ShippingDatabase.upsert_order(order)

        response = client.get("/api/shopify/metrics?days=14")

        assert response.status_code == 200
        data = response.json()
        assert data['total_revenue'] == 700.0  # 50 * 14 days
        assert data['total_orders'] == 14

    def test_get_shopify_time_series(self, client):
        """Test getting time series data."""
        from app.database import ShippingDatabase
        for i in range(5):
            day = date.today() - timedelta(days=i)
            order = {
                'id': f'order-{i}',
                'order_number': i,
                'order_date': str(day),
                'customer_email': f'test{i}@example.com',
                'subtotal': float(i * 20),
                'total_price': float(i * 20),
                'shipping_charged': float(i * 2),
                'shipping_cost_estimated': float(i),
                'currency': 'USD',
                'financial_status': 'paid',
                'fulfillment_status': 'fulfilled'
            }
            ShippingDatabase.upsert_order(order)

        response = client.get("/api/shopify/metrics/revenue?days=7")

        assert response.status_code == 200
        data = response.json()
        assert 'metric_name' in data
        assert 'data_points' in data
        assert data['metric_name'] == 'revenue'
        assert len(data['data_points']) == 5

    def test_get_shopify_orders(self, client, auth_headers, sample_order):
        """Test getting list of orders."""
        ShippingDatabase.upsert_order(sample_order)

        response = client.get("/api/shopify/orders?days=30", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert 'orders' in data
        assert len(data['orders']) >= 1

    def test_get_shopify_orders_unauthorized(self, client):
        """Test getting orders without auth."""
        response = client.get("/api/shopify/orders")

        assert response.status_code == 401

    def test_get_shopify_order_detail(self, client, auth_headers, sample_order, sample_order_items):
        """Test getting single order detail."""
        ShippingDatabase.upsert_order(sample_order)
        ShippingDatabase.insert_order_items(sample_order['id'], sample_order_items)

        response = client.get(f"/api/shopify/orders/{sample_order['id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == sample_order['id']
        assert 'items' in data
        assert len(data['items']) == len(sample_order_items)

    def test_get_shopify_order_detail_not_found(self, client, auth_headers):
        """Test getting non-existent order."""
        response = client.get("/api/shopify/orders/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    def test_calculate_order_shipping(self, client, auth_headers, sample_order, sample_order_items, sample_shipping_profile):
        """Test calculating shipping cost for an order."""
        # Create order with items
        ShippingDatabase.upsert_order(sample_order)
        ShippingDatabase.insert_order_items(sample_order['id'], sample_order_items)

        # Create shipping profile
        ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        response = client.post(
            f"/api/shopify/orders/{sample_order['id']}/calculate-shipping",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'order_id' in data
        assert 'calculated_cost' in data
        assert 'breakdown' in data

    def test_calculate_all_orders_shipping(self, client, auth_headers, sample_order, sample_order_items, sample_shipping_profile):
        """Test bulk calculating shipping for all orders."""
        # Create multiple orders
        order_ids = []
        for i in range(3):
            order = sample_order.copy()
            order['id'] = f"order-{i}"
            order['order_number'] = 1000 + i
            order_ids.append(order['id'])
            ShippingDatabase.upsert_order(order)
            ShippingDatabase.insert_order_items(order['id'], sample_order_items)

        # Create shipping profile
        ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        response = client.post(
            "/api/shopify/orders/calculate-shipping",
            json={"order_ids": order_ids},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'orders_processed' in data
        assert data['orders_processed'] >= 1


@pytest.mark.unit
class TestShippingProfileRouter:
    """Test shipping profile management endpoints."""

    def test_get_shipping_profiles_empty(self, client, auth_headers):
        """Test getting profiles when none exist."""
        response = client.get("/api/shipping/profiles", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_get_shipping_profiles_with_data(self, client, auth_headers, sample_shipping_profile):
        """Test getting profiles with data."""
        ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        response = client.get("/api/shipping/profiles", headers=auth_headers)

        assert response.status_code == 200
        profiles = response.json()
        assert len(profiles) >= 1
        assert profiles[0]['name'] == sample_shipping_profile['name']

    def test_get_shipping_profiles_active_only(self, client, auth_headers):
        """Test getting only active profiles."""
        # Create active profile
        active_profile = {
            "id": "active-1",
            "name": "Active Rule",
            "priority": 10,
            "is_active": True,
            "is_default": False,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 10.0}
        }
        ShippingDatabase.upsert_shipping_profile(active_profile)

        # Create inactive profile
        inactive_profile = active_profile.copy()
        inactive_profile['id'] = "inactive-1"
        inactive_profile['name'] = "Inactive Rule"
        inactive_profile['is_active'] = False
        ShippingDatabase.upsert_shipping_profile(inactive_profile)

        response = client.get("/api/shipping/profiles?active_only=true", headers=auth_headers)

        assert response.status_code == 200
        profiles = response.json()
        assert all(p['is_active'] for p in profiles)

    def test_create_shipping_profile(self, client, auth_headers):
        """Test creating a new shipping profile."""
        profile_data = {
            "name": "New Profile",
            "description": "Test description",
            "priority": 20,
            "is_active": True,
            "match_conditions": {
                "field": "product_title",
                "operator": "contains",
                "value": "special"
            },
            "cost_rules": {
                "type": "fixed",
                "base_cost": 15.0
            }
        }

        response = client.post(
            "/api/shipping/profiles",
            json=profile_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'profile_id' in data

    def test_update_shipping_profile(self, client, auth_headers, sample_shipping_profile):
        """Test updating an existing profile."""
        profile_id = ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        update_data = {
            "name": "Updated Name",
            "priority": 50
        }

        response = client.put(
            f"/api/shipping/profiles/{profile_id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_update_shipping_profile_not_found(self, client, auth_headers):
        """Test updating non-existent profile."""
        response = client.put(
            "/api/shipping/profiles/nonexistent",
            json={"name": "Updated"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_delete_shipping_profile(self, client, auth_headers, sample_shipping_profile):
        """Test deleting a shipping profile."""
        profile_id = ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        response = client.delete(
            f"/api/shipping/profiles/{profile_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_test_profile_match(self, client, auth_headers):
        """Test the profile testing endpoint."""
        test_request = {
            "profile": {
                "name": "Test Rule",
                "priority": 10,
                "is_active": True,
                "match_conditions": {
                    "field": "product_title",
                    "operator": "contains",
                    "value": "test"
                },
                "cost_rules": {
                    "type": "fixed",
                    "base_cost": 12.0
                }
            },
            "test_data": {
                "product_title": "Test Product",
                "order_subtotal": 100.0
            }
        }

        response = client.post(
            "/api/shipping/profiles/test",
            json=test_request,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'matched' in data
        assert 'calculated_cost' in data
        assert data['matched'] is True
        assert data['calculated_cost'] == 12.0

    def test_test_profile_no_match(self, client, auth_headers):
        """Test profile testing with no match."""
        test_request = {
            "profile": {
                "name": "Test Rule",
                "priority": 10,
                "is_active": True,
                "match_conditions": {
                    "field": "product_title",
                    "operator": "contains",
                    "value": "special"
                },
                "cost_rules": {
                    "type": "fixed",
                    "base_cost": 12.0
                }
            },
            "test_data": {
                "product_title": "Regular Product",
                "order_subtotal": 100.0
            }
        }

        response = client.post(
            "/api/shipping/profiles/test",
            json=test_request,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['matched'] is False
        assert data['calculated_cost'] is None

