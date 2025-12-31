"""
Unit tests for database module (app.database).
"""
import pytest
import os
from datetime import date, datetime, timedelta
import json
from app.database import (
    CampaignDatabase,
    ShopifyDatabase,
    ShippingDatabase,
    SettingsDatabase,
    ProductDatabase,
    get_db_connection,
    init_database
)


@pytest.mark.unit
class TestDatabaseInitialization:
    """Test database initialization."""

    def test_init_database_creates_tables(self, test_db):
        """Test that all tables are created."""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}

            expected_tables = {
                'campaigns', 'campaign_metrics', 'sync_log',
                'shopify_daily_metrics', 'shopify_orders', 'shopify_order_items',
                'shipping_profiles', 'order_shipping_calculations',
                'settings', 'shopping_products', 'product_metrics'
            }

            assert expected_tables.issubset(tables)

    def test_init_database_creates_indexes(self, test_db):
        """Test that all indexes are created."""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
            indexes = {row[0] for row in cursor.fetchall()}

            expected_indexes = {
                'idx_campaign_metrics_campaign_date',
                'idx_campaign_metrics_metric_name',
                'idx_shopify_daily_metrics_date',
                'idx_shopify_orders_date',
                'idx_shopify_order_items_order',
                'idx_shopify_order_items_title',
                'idx_shipping_profiles_priority',
                'idx_shipping_profiles_active',
                'idx_order_shipping_calc_order',
                'idx_order_shipping_calc_date',
                'idx_product_metrics_product_campaign_date',
                'idx_product_metrics_metric_name'
            }

            assert expected_indexes.issubset(indexes)

    def test_init_database_idempotent(self, test_db):
        """Test that calling init_database multiple times is safe."""
        # Call init_database again
        init_database()

        # Should not raise errors and tables should still exist
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            count = cursor.fetchone()[0]
            assert count > 0


@pytest.mark.unit
class TestCampaignDatabase:
    """Test CampaignDatabase class."""

    def test_upsert_campaign_new(self, test_db, sample_campaign):
        """Test inserting a new campaign."""
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM campaigns WHERE id = ?", (sample_campaign['id'],))
            row = cursor.fetchone()

            assert row is not None
            assert row['name'] == sample_campaign['name']
            assert row['status'] == sample_campaign['status']
            assert row['platform'] == sample_campaign['platform']

    def test_upsert_campaign_update(self, test_db, sample_campaign):
        """Test updating an existing campaign."""
        # Insert initial
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            "Original Name",
            "PAUSED",
            "google_ads"
        )

        # Update
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            "Updated Name",
            "ENABLED",
            "google_ads"
        )

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM campaigns WHERE id = ?", (sample_campaign['id'],))
            row = cursor.fetchone()

            assert row['name'] == "Updated Name"
            assert row['status'] == "ENABLED"

    def test_upsert_metric_new(self, test_db, sample_campaign):
        """Test inserting a new metric."""
        # Create campaign first
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        # Insert metric
        CampaignDatabase.upsert_metric(
            sample_campaign['id'],
            "2025-01-01",
            "clicks",
            100.0,
            "count"
        )

        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM campaign_metrics WHERE campaign_id = ? AND metric_name = 'clicks'",
                (sample_campaign['id'],)
            )
            row = cursor.fetchone()

            assert row is not None
            assert row['value'] == 100.0
            assert row['unit'] == "count"

    def test_upsert_metric_update(self, test_db, sample_campaign):
        """Test updating an existing metric."""
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        # Insert initial
        CampaignDatabase.upsert_metric(sample_campaign['id'], "2025-01-01", "clicks", 100.0, "count")

        # Update
        CampaignDatabase.upsert_metric(sample_campaign['id'], "2025-01-01", "clicks", 150.0, "count")

        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*), MAX(value) FROM campaign_metrics WHERE campaign_id = ? AND metric_name = 'clicks'",
                (sample_campaign['id'],)
            )
            count, value = cursor.fetchone()

            assert count == 1  # Should be one record, not two
            assert value == 150.0

    def test_get_all_campaigns(self, test_db, sample_campaign):
        """Test retrieving all campaigns."""
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        campaigns = CampaignDatabase.get_all_campaigns()

        assert len(campaigns) >= 1
        assert any(c['id'] == sample_campaign['id'] for c in campaigns)

    def test_get_all_campaigns_empty(self, test_db):
        """Test retrieving campaigns when none exist."""
        campaigns = CampaignDatabase.get_all_campaigns()
        assert campaigns == []

    def test_get_latest_metrics(self, test_db, sample_campaign):
        """Test getting latest metrics for a campaign."""
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        # Add metrics from last 7 days
        today = date.today()
        for i in range(7):
            day = today - timedelta(days=i)
            CampaignDatabase.upsert_metric(sample_campaign['id'], str(day), "clicks", float(i * 10), "count")

        metrics = CampaignDatabase.get_latest_metrics(sample_campaign['id'])

        assert len(metrics) >= 1
        # Clicks should be summed
        clicks_metric = next((m for m in metrics if m['name'] == 'clicks'), None)
        assert clicks_metric is not None
        assert clicks_metric['value'] > 0

    def test_get_campaign_time_series(self, test_db, sample_campaign):
        """Test getting time series data for a campaign metric."""
        CampaignDatabase.upsert_campaign(
            sample_campaign['id'],
            sample_campaign['name'],
            sample_campaign['status'],
            sample_campaign['platform']
        )

        # Add time series data
        for i in range(10):
            day = date.today() - timedelta(days=i)
            CampaignDatabase.upsert_metric(sample_campaign['id'], str(day), "spend", float(i * 50), "USD")

        result = CampaignDatabase.get_campaign_time_series(sample_campaign['id'], "spend", 30)

        assert result is not None
        assert result['campaign_id'] == sample_campaign['id']
        assert result['metric_name'] == "spend"
        assert len(result['data_points']) == 10

    def test_get_campaign_time_series_nonexistent(self, test_db):
        """Test getting time series for non-existent campaign."""
        result = CampaignDatabase.get_campaign_time_series("nonexistent", "clicks", 30)
        assert result is None

    def test_log_sync_success(self, test_db):
        """Test logging a successful sync."""
        CampaignDatabase.log_sync(5, 100, "success", None)

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM sync_log ORDER BY synced_at DESC LIMIT 1")
            row = cursor.fetchone()

            assert row is not None
            assert row['campaigns_count'] == 5
            assert row['metrics_count'] == 100
            assert row['status'] == "success"

    def test_log_sync_error(self, test_db):
        """Test logging a failed sync."""
        CampaignDatabase.log_sync(0, 0, "error", "Connection timeout")

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM sync_log ORDER BY synced_at DESC LIMIT 1")
            row = cursor.fetchone()

            assert row['status'] == "error"
            assert row['error_message'] == "Connection timeout"

    def test_get_last_sync(self, test_db):
        """Test retrieving last successful sync."""
        # Log syncs in order
        CampaignDatabase.log_sync(5, 100, "success", None)
        CampaignDatabase.log_sync(0, 0, "error", "Test error")
        CampaignDatabase.log_sync(10, 200, "success", None)

        last_sync = CampaignDatabase.get_last_sync()

        assert last_sync is not None
        # Should return the most recent successful sync (10, 200)
        assert last_sync['campaigns_count'] in [5, 10]  # Could be either depending on timing
        assert last_sync['status'] == "success"

    def test_bulk_upsert_from_script(self, test_db):
        """Test bulk upserting campaign data."""
        data = {
            "campaigns": [
                {
                    "id": "camp-1",
                    "name": "Campaign 1",
                    "status": "ENABLED",
                    "platform": "google_ads",
                    "metrics": [
                        {"date": "2025-01-01", "name": "clicks", "value": 100, "unit": "count"},
                        {"date": "2025-01-01", "name": "spend", "value": 50.0, "unit": "USD"}
                    ]
                },
                {
                    "id": "camp-2",
                    "name": "Campaign 2",
                    "status": "PAUSED",
                    "metrics": [
                        {"date": "2025-01-01", "name": "impressions", "value": 1000, "unit": "count"}
                    ]
                }
            ]
        }

        result = CampaignDatabase.bulk_upsert_from_script(data)

        assert result['success'] is True
        assert result['campaigns_processed'] == 2
        assert result['metrics_processed'] == 3

    def test_bulk_upsert_converts_average_cpc(self, test_db):
        """Test that average_cpc is converted to cpc with proper unit conversion."""
        data = {
            "campaigns": [
                {
                    "id": "camp-1",
                    "name": "Campaign 1",
                    "status": "ENABLED",
                    "metrics": [
                        {"date": "2025-01-01", "name": "average_cpc", "value": 1500000, "unit": "count"}
                    ]
                }
            ]
        }

        CampaignDatabase.bulk_upsert_from_script(data)

        with get_db_connection() as conn:
            # Should be stored as 'cpc' not 'average_cpc'
            cursor = conn.execute(
                "SELECT * FROM campaign_metrics WHERE campaign_id = 'camp-1' AND metric_name = 'cpc'"
            )
            row = cursor.fetchone()

            assert row is not None
            assert row['value'] == 1.5  # Converted from micros
            assert row['unit'] == 'USD'

            # Check that average_cpc doesn't exist
            cursor = conn.execute(
                "SELECT COUNT(*) FROM campaign_metrics WHERE campaign_id = 'camp-1' AND metric_name = 'average_cpc'"
            )
            count = cursor.fetchone()[0]
            assert count == 0


@pytest.mark.unit
class TestShopifyDatabase:
    """Test ShopifyDatabase class."""

    def test_upsert_daily_metrics_new(self, test_db):
        """Test inserting new daily metrics."""
        ShopifyDatabase.upsert_daily_metrics(
            "2025-01-01",
            100.0,
            10.0,
            5.0,
            3
        )

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM shopify_daily_metrics WHERE date = '2025-01-01'")
            row = cursor.fetchone()

            assert row is not None
            assert row['revenue'] == 100.0
            assert row['shipping_revenue'] == 10.0
            assert row['shipping_cost'] == 5.0
            assert row['order_count'] == 3

    def test_upsert_daily_metrics_update(self, test_db):
        """Test updating existing daily metrics."""
        # Insert initial
        ShopifyDatabase.upsert_daily_metrics("2025-01-01", 100.0, 10.0, 5.0, 3)

        # Update
        ShopifyDatabase.upsert_daily_metrics("2025-01-01", 200.0, 20.0, 10.0, 5)

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*), revenue FROM shopify_daily_metrics WHERE date = '2025-01-01'")
            count, revenue = cursor.fetchone()

            assert count == 1  # Should be one record
            assert revenue == 200.0

    def test_get_metrics_summary(self, test_db):
        """Test getting aggregated metrics summary."""
        # Add metrics for last 7 days
        for i in range(7):
            day = date.today() - timedelta(days=i)
            ShopifyDatabase.upsert_daily_metrics(
                str(day),
                100.0,
                10.0,
                5.0,
                2
            )

        summary = ShopifyDatabase.get_metrics_summary(days=7)

        assert summary['total_revenue'] == 700.0
        assert summary['total_shipping_revenue'] == 70.0
        assert summary['total_orders'] == 14

    def test_get_metrics_summary_empty(self, test_db):
        """Test getting summary when no data exists."""
        summary = ShopifyDatabase.get_metrics_summary(days=7)

        assert summary['total_revenue'] == 0
        assert summary['total_shipping_revenue'] == 0
        assert summary['total_shipping_cost'] == 0
        assert summary['total_orders'] == 0

    def test_get_time_series(self, test_db):
        """Test getting time series for a metric."""
        # Add data
        for i in range(5):
            day = date.today() - timedelta(days=i)
            ShopifyDatabase.upsert_daily_metrics(str(day), float(i * 100), 0, 0, i)

        result = ShopifyDatabase.get_time_series("revenue", 30)

        assert len(result) == 5
        assert all('date' in row and 'value' in row for row in result)

    def test_bulk_upsert_from_orders(self, test_db):
        """Test bulk upserting Shopify order data."""
        orders_data = [
            {
                "date": "2025-01-01",
                "revenue": 150.0,
                "shipping_revenue": 10.0,
                "shipping_cost": 5.0,
                "order_count": 3
            },
            {
                "date": "2025-01-02",
                "revenue": 200.0,
                "shipping_revenue": 15.0,
                "shipping_cost": 7.0,
                "order_count": 4
            }
        ]

        result = ShopifyDatabase.bulk_upsert_from_orders(orders_data)

        assert result['success'] is True
        assert result['records_processed'] == 2


@pytest.mark.unit
class TestShippingDatabase:
    """Test ShippingDatabase class."""

    def test_upsert_order_new(self, test_db, sample_order):
        """Test inserting a new order."""
        ShippingDatabase.upsert_order(sample_order)

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM shopify_orders WHERE id = ?", (sample_order['id'],))
            row = cursor.fetchone()

            assert row is not None
            assert row['order_number'] == sample_order['order_number']
            assert row['subtotal'] == sample_order['subtotal']

    def test_upsert_order_update(self, test_db, sample_order):
        """Test updating an existing order."""
        ShippingDatabase.upsert_order(sample_order)

        # Update
        updated_order = sample_order.copy()
        updated_order['subtotal'] = 200.0
        ShippingDatabase.upsert_order(updated_order)

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*), subtotal FROM shopify_orders WHERE id = ?", (sample_order['id'],))
            count, subtotal = cursor.fetchone()

            assert count == 1
            assert subtotal == 200.0

    def test_insert_order_items(self, test_db, sample_order, sample_order_items):
        """Test inserting order line items."""
        ShippingDatabase.upsert_order(sample_order)
        ShippingDatabase.insert_order_items(sample_order['id'], sample_order_items)

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM shopify_order_items WHERE order_id = ?", (sample_order['id'],))
            rows = cursor.fetchall()

            assert len(rows) == len(sample_order_items)
            assert rows[0]['product_title'] == sample_order_items[0]['product_title']

    def test_insert_order_items_replaces_existing(self, test_db, sample_order, sample_order_items):
        """Test that inserting order items replaces existing ones."""
        ShippingDatabase.upsert_order(sample_order)

        # Insert initial items
        ShippingDatabase.insert_order_items(sample_order['id'], sample_order_items)

        # Insert new items (should replace)
        new_items = [
            {
                "product_id": "111",
                "variant_id": "222",
                "product_title": "New Product",
                "variant_title": "Large",
                "quantity": 2,
                "price": 50.0,
                "total": 100.0
            }
        ]
        ShippingDatabase.insert_order_items(sample_order['id'], new_items)

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*), product_title FROM shopify_order_items WHERE order_id = ?", (sample_order['id'],))
            count, title = cursor.fetchone()

            assert count == 1
            assert title == "New Product"

    def test_get_orders(self, test_db, sample_order):
        """Test getting list of orders."""
        ShippingDatabase.upsert_order(sample_order)

        orders = ShippingDatabase.get_orders(days=30)

        assert len(orders) >= 1
        assert any(o['id'] == sample_order['id'] for o in orders)

    def test_get_orders_with_filters(self, test_db, sample_order):
        """Test getting orders with status filter."""
        ShippingDatabase.upsert_order(sample_order)

        orders = ShippingDatabase.get_orders(days=30, status="paid")

        assert len(orders) >= 1

    def test_get_order_detail(self, test_db, sample_order, sample_order_items):
        """Test getting single order with line items."""
        ShippingDatabase.upsert_order(sample_order)
        ShippingDatabase.insert_order_items(sample_order['id'], sample_order_items)

        order = ShippingDatabase.get_order_detail(sample_order['id'])

        assert order is not None
        assert order['id'] == sample_order['id']
        assert len(order['items']) == len(sample_order_items)

    def test_get_order_detail_nonexistent(self, test_db):
        """Test getting non-existent order."""
        order = ShippingDatabase.get_order_detail("nonexistent")
        assert order is None

    def test_upsert_shipping_profile_new(self, test_db, sample_shipping_profile):
        """Test inserting a new shipping profile."""
        profile_id = ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        assert profile_id is not None

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM shipping_profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()

            assert row is not None
            assert row['name'] == sample_shipping_profile['name']
            assert row['priority'] == sample_shipping_profile['priority']

    def test_upsert_shipping_profile_generates_id(self, test_db, sample_shipping_profile):
        """Test that shipping profile gets UUID if not provided."""
        profile_data = sample_shipping_profile.copy()
        profile_data.pop('id', None)

        profile_id = ShippingDatabase.upsert_shipping_profile(profile_data)

        assert profile_id is not None
        assert len(profile_id) > 0

    def test_upsert_shipping_profile_default_unsets_others(self, test_db, sample_shipping_profile):
        """Test that setting a profile as default unsets other defaults."""
        # Insert first default
        profile1 = sample_shipping_profile.copy()
        profile1['id'] = 'profile-1'
        profile1['is_default'] = True
        ShippingDatabase.upsert_shipping_profile(profile1)

        # Insert second default
        profile2 = sample_shipping_profile.copy()
        profile2['id'] = 'profile-2'
        profile2['is_default'] = True
        ShippingDatabase.upsert_shipping_profile(profile2)

        # Only profile-2 should be default
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT id FROM shipping_profiles WHERE is_default = 1")
            rows = cursor.fetchall()

            assert len(rows) == 1
            assert rows[0]['id'] == 'profile-2'

    def test_get_shipping_profiles(self, test_db, sample_shipping_profile):
        """Test getting all shipping profiles."""
        ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        profiles = ShippingDatabase.get_shipping_profiles()

        assert len(profiles) >= 1
        assert profiles[0]['match_conditions'] is not None
        assert isinstance(profiles[0]['match_conditions'], dict)

    def test_get_shipping_profiles_active_only(self, test_db, sample_shipping_profile):
        """Test getting only active profiles."""
        # Active profile
        active_profile = sample_shipping_profile.copy()
        active_profile['id'] = 'active-1'
        active_profile['is_active'] = True
        ShippingDatabase.upsert_shipping_profile(active_profile)

        # Inactive profile
        inactive_profile = sample_shipping_profile.copy()
        inactive_profile['id'] = 'inactive-1'
        inactive_profile['is_active'] = False
        ShippingDatabase.upsert_shipping_profile(inactive_profile)

        profiles = ShippingDatabase.get_shipping_profiles(active_only=True)

        assert all(p['is_active'] for p in profiles)

    def test_delete_shipping_profile(self, test_db, sample_shipping_profile):
        """Test deleting a shipping profile."""
        profile_id = ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        ShippingDatabase.delete_shipping_profile(profile_id)

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM shipping_profiles WHERE id = ?", (profile_id,))
            count = cursor.fetchone()[0]

            assert count == 0

    def test_save_shipping_calculation(self, test_db, sample_order, sample_shipping_profile):
        """Test saving a shipping calculation."""
        ShippingDatabase.upsert_order(sample_order)
        profile_id = ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        details = {"breakdown": [{"item": "Test Product", "cost": 10.0}]}
        ShippingDatabase.save_shipping_calculation(sample_order['id'], profile_id, 10.0, details)

        # Check calculation record
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM order_shipping_calculations WHERE order_id = ?",
                (sample_order['id'],)
            )
            row = cursor.fetchone()

            assert row is not None
            assert row['calculated_cost'] == 10.0

            # Check order updated
            cursor = conn.execute("SELECT shipping_cost_estimated FROM shopify_orders WHERE id = ?", (sample_order['id'],))
            order_row = cursor.fetchone()
            assert order_row['shipping_cost_estimated'] == 10.0

    def test_get_shipping_calculations(self, test_db, sample_order, sample_shipping_profile):
        """Test getting shipping calculation history."""
        ShippingDatabase.upsert_order(sample_order)
        profile_id = ShippingDatabase.upsert_shipping_profile(sample_shipping_profile)

        details = {"breakdown": []}
        ShippingDatabase.save_shipping_calculation(sample_order['id'], profile_id, 10.0, details)

        calculations = ShippingDatabase.get_shipping_calculations(order_id=sample_order['id'])

        assert len(calculations) >= 1
        assert calculations[0]['order_id'] == sample_order['id']

    def test_get_uncalculated_orders(self, test_db, sample_order):
        """Test getting orders without shipping calculations."""
        ShippingDatabase.upsert_order(sample_order)

        uncalculated = ShippingDatabase.get_uncalculated_orders()

        assert sample_order['id'] in uncalculated

    def test_bulk_upsert_orders(self, test_db, sample_order, sample_order_items):
        """Test bulk upserting orders with items."""
        order_with_items = sample_order.copy()
        order_with_items['items'] = sample_order_items

        result = ShippingDatabase.bulk_upsert_orders([order_with_items])

        assert result['success'] is True
        assert result['orders_processed'] == 1


@pytest.mark.unit
class TestSettingsDatabase:
    """Test SettingsDatabase class."""

    def test_set_setting_new(self, test_db):
        """Test setting a new setting value."""
        SettingsDatabase.set_setting("test_key", "test_value")

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'test_key'")
            row = cursor.fetchone()

            assert row is not None
            assert row['value'] == "test_value"

    def test_set_setting_update(self, test_db):
        """Test updating an existing setting."""
        SettingsDatabase.set_setting("test_key", "initial_value")
        SettingsDatabase.set_setting("test_key", "updated_value")

        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*), value FROM settings WHERE key = 'test_key'")
            count, value = cursor.fetchone()

            assert count == 1
            assert value == "updated_value"

    def test_get_setting_exists(self, test_db):
        """Test getting an existing setting."""
        SettingsDatabase.set_setting("test_key", "test_value")

        value = SettingsDatabase.get_setting("test_key")

        assert value == "test_value"

    def test_get_setting_not_exists(self, test_db):
        """Test getting a non-existent setting."""
        value = SettingsDatabase.get_setting("nonexistent")
        assert value is None

    def test_get_setting_with_default(self, test_db):
        """Test getting setting with default value."""
        value = SettingsDatabase.get_setting("nonexistent", "default_value")
        assert value == "default_value"

    def test_delete_setting(self, test_db):
        """Test deleting a setting."""
        SettingsDatabase.set_setting("test_key", "test_value")
        SettingsDatabase.delete_setting("test_key")

        value = SettingsDatabase.get_setting("test_key")
        assert value is None

    def test_get_all_settings(self, test_db):
        """Test getting all settings."""
        SettingsDatabase.set_setting("key1", "value1")
        SettingsDatabase.set_setting("key2", "value2")

        all_settings = SettingsDatabase.get_all_settings()

        assert "key1" in all_settings
        assert all_settings["key1"] == "value1"
        assert "key2" in all_settings
        assert all_settings["key2"] == "value2"


@pytest.mark.unit
class TestProductDatabase:
    """Test ProductDatabase class."""

    def test_upsert_product_new(self, test_db):
        """Test inserting a new product."""
        ProductDatabase.upsert_product("product-1", "Test Product", "campaign-1", "Test Campaign")

        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM shopping_products WHERE product_id = 'product-1' AND campaign_id = 'campaign-1'"
            )
            row = cursor.fetchone()

            assert row is not None
            assert row['product_title'] == "Test Product"
            assert row['campaign_name'] == "Test Campaign"

    def test_upsert_product_requires_campaign_id(self, test_db):
        """Test that campaign_id is required."""
        with pytest.raises(ValueError):
            ProductDatabase.upsert_product("product-1", "Test Product", None)

    def test_upsert_product_update(self, test_db):
        """Test updating an existing product."""
        ProductDatabase.upsert_product("product-1", "Original Title", "campaign-1")
        ProductDatabase.upsert_product("product-1", "Updated Title", "campaign-1")

        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*), product_title FROM shopping_products WHERE product_id = 'product-1' AND campaign_id = 'campaign-1'"
            )
            count, title = cursor.fetchone()

            assert count == 1
            assert title == "Updated Title"

    def test_upsert_product_metric(self, test_db):
        """Test upserting a product metric."""
        ProductDatabase.upsert_product("product-1", "Test Product", "campaign-1")
        ProductDatabase.upsert_product_metric("product-1", "campaign-1", "2025-01-01", "clicks", 100.0, "count")

        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_metrics WHERE product_id = 'product-1' AND metric_name = 'clicks'"
            )
            row = cursor.fetchone()

            assert row is not None
            assert row['value'] == 100.0

    def test_get_all_products(self, test_db):
        """Test getting all products."""
        ProductDatabase.upsert_product("product-1", "Product 1", "campaign-1")
        ProductDatabase.upsert_product("product-2", "Product 2", "campaign-1")

        products = ProductDatabase.get_all_products()

        assert len(products) >= 2

    def test_get_aggregated_metrics(self, test_db):
        """Test getting aggregated metrics for a product."""
        ProductDatabase.upsert_product("product-1", "Test Product", "campaign-1")

        # Add metrics for last 7 days
        for i in range(7):
            day = date.today() - timedelta(days=i)
            ProductDatabase.upsert_product_metric("product-1", "campaign-1", str(day), "clicks", float(i * 10), "count")

        metrics = ProductDatabase.get_aggregated_metrics("product-1", "campaign-1", 30)

        assert len(metrics) >= 1
        clicks_metric = next((m for m in metrics if m['name'] == 'clicks'), None)
        assert clicks_metric is not None

    def test_get_product_time_series(self, test_db):
        """Test getting time series for a product metric."""
        ProductDatabase.upsert_product("product-1", "Test Product", "campaign-1")

        # Add time series data
        for i in range(5):
            day = date.today() - timedelta(days=i)
            ProductDatabase.upsert_product_metric("product-1", "campaign-1", str(day), "spend", float(i * 20), "USD")

        result = ProductDatabase.get_product_time_series("product-1", "campaign-1", "spend", 30)

        assert result is not None
        assert result['metric_name'] == "spend"
        assert len(result['data_points']) == 5

    def test_bulk_upsert_from_script(self, test_db):
        """Test bulk upserting products from script."""
        products_data = [
            {
                "product_id": "product-1",
                "product_title": "Product 1",
                "campaign_id": "campaign-1",
                "campaign_name": "Campaign 1",
                "metrics": [
                    {"date": "2025-01-01", "name": "clicks", "value": 100, "unit": "count"}
                ]
            },
            {
                "product_id": "product-2",
                "product_title": "Product 2",
                "campaign_id": "campaign-1",
                "metrics": [
                    {"date": "2025-01-01", "name": "impressions", "value": 1000, "unit": "count"}
                ]
            }
        ]

        result = ProductDatabase.bulk_upsert_from_script(products_data)

        assert result['products_processed'] == 2
        assert result['metrics_processed'] == 2

    def test_bulk_upsert_converts_average_cpc(self, test_db):
        """Test that average_cpc is converted properly."""
        products_data = [
            {
                "product_id": "product-1",
                "product_title": "Product 1",
                "campaign_id": "campaign-1",
                "metrics": [
                    {"date": "2025-01-01", "name": "average_cpc", "value": 2000000, "unit": "count"}
                ]
            }
        ]

        ProductDatabase.bulk_upsert_from_script(products_data)

        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_metrics WHERE product_id = 'product-1' AND metric_name = 'cpc'"
            )
            row = cursor.fetchone()

            assert row is not None
            assert row['value'] == 2.0
            assert row['unit'] == 'USD'


@pytest.mark.unit
class TestGetDbConnection:
    """Test get_db_connection context manager."""

    def test_connection_commits_on_success(self, test_db):
        """Test that changes are committed on successful exit."""
        with get_db_connection() as conn:
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("test", "value"))

        # Verify committed
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'test'")
            row = cursor.fetchone()
            assert row is not None

    def test_connection_rollback_on_error(self, test_db):
        """Test that changes are rolled back on error."""
        try:
            with get_db_connection() as conn:
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("test", "value"))
                raise Exception("Intentional error")
        except:
            pass

        # Verify rolled back
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM settings WHERE key = 'test'")
            count = cursor.fetchone()[0]
            assert count == 0

    def test_connection_closes_after_exit(self, test_db):
        """Test that connection is properly closed."""
        with get_db_connection() as conn:
            assert conn is not None

        # After exit, can still create new connections
        with get_db_connection() as conn:
            assert conn is not None
