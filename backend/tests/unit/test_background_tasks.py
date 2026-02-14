"""
Unit tests for background sync tasks.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import httpx
from app.background_tasks import ShopifySyncTask, MetaSyncTask, ShippingCalculationTask
from app.database import SettingsDatabase, ShopifyDatabase, ShippingDatabase, CampaignDatabase


@pytest.mark.unit
class TestShopifySyncTask:
    """Test Shopify automatic sync background task."""

    @pytest.fixture
    def shopify_sync_task(self):
        """Create a Shopify sync task for testing."""
        return ShopifySyncTask(interval_minutes=10)

    @pytest.fixture
    def mock_shopify_orders(self):
        """Sample Shopify orders response."""
        return {
            "orders": [
                {
                    "id": 6597871993140,
                    "order_number": 1001,
                    "created_at": "2026-01-05T10:00:00Z",
                    "email": "customer1@example.com",
                    "subtotal_price": "100.00",
                    "total_price": "115.00",
                    "total_discounts": "0.00",
                    "currency": "USD",
                    "financial_status": "paid",
                    "fulfillment_status": "fulfilled",
                    "shipping_lines": [
                        {"price": "10.00"}
                    ],
                    "line_items": [
                        {
                            "product_id": 123456,
                            "variant_id": 789012,
                            "title": "Test Product 1",
                            "variant_title": "Small",
                            "quantity": 2,
                            "price": "50.00"
                        }
                    ]
                },
                {
                    "id": 6597871993141,
                    "order_number": 1002,
                    "created_at": "2026-01-05T11:00:00Z",
                    "email": "customer2@example.com",
                    "subtotal_price": "200.00",
                    "total_price": "225.00",
                    "total_discounts": "10.00",
                    "currency": "USD",
                    "financial_status": "paid",
                    "fulfillment_status": "pending",
                    "shipping_lines": [
                        {"price": "15.00"}
                    ],
                    "line_items": [
                        {
                            "product_id": 123457,
                            "variant_id": 789013,
                            "title": "Test Product 2",
                            "variant_title": "Large",
                            "quantity": 1,
                            "price": "200.00"
                        }
                    ]
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_sync_shopify_data_success(self, test_db, shopify_sync_task, mock_shopify_orders):
        """Test successful Shopify data sync."""
        # Setup credentials
        SettingsDatabase.set_setting("shopify_shop_name", "test-shop")
        SettingsDatabase.set_setting("shopify_access_token", "test-token")

        # Mock HTTP client
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_shopify_orders

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            # Execute sync
            await shopify_sync_task.sync_shopify_data()

            # Verify daily metrics were stored
            metrics = ShopifyDatabase.get_time_series('revenue', days=7)
            assert len(metrics) > 0

            # Verify individual orders were stored
            orders = ShippingDatabase.get_orders(days=7)
            assert len(orders) == 2
            assert orders[0]['order_number'] in [1001, 1002]

    @pytest.mark.asyncio
    async def test_sync_shopify_data_no_credentials(self, test_db, shopify_sync_task):
        """Test sync when credentials are not configured."""
        # Don't set any credentials
        await shopify_sync_task.sync_shopify_data()

        # Verify no data was stored
        metrics = ShopifyDatabase.get_time_series('revenue', days=7)
        assert len(metrics) == 0

    @pytest.mark.asyncio
    async def test_sync_shopify_data_api_error(self, test_db, shopify_sync_task):
        """Test sync when Shopify API returns an error."""
        # Setup credentials
        SettingsDatabase.set_setting("shopify_shop_name", "test-shop")
        SettingsDatabase.set_setting("shopify_access_token", "test-token")

        # Mock HTTP client with error response
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            # Execute sync
            await shopify_sync_task.sync_shopify_data()

            # Verify no data was stored
            orders = ShippingDatabase.get_orders(days=7)
            assert len(orders) == 0

    @pytest.mark.asyncio
    async def test_sync_shopify_data_timeout(self, test_db, shopify_sync_task):
        """Test sync when request times out."""
        # Setup credentials
        SettingsDatabase.set_setting("shopify_shop_name", "test-shop")
        SettingsDatabase.set_setting("shopify_access_token", "test-token")

        # Mock HTTP client with timeout
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value = mock_context

            # Execute sync (should not raise exception)
            await shopify_sync_task.sync_shopify_data()

            # Verify no data was stored
            orders = ShippingDatabase.get_orders(days=7)
            assert len(orders) == 0

    def test_aggregate_orders_by_date(self, shopify_sync_task, mock_shopify_orders):
        """Test aggregating orders by date."""
        orders = mock_shopify_orders['orders']
        daily_metrics = shopify_sync_task._aggregate_orders_by_date(orders)

        # Should have 1 day of data (both orders on same day)
        assert len(daily_metrics) == 1

        # Verify aggregated values
        day_data = daily_metrics[0]
        assert day_data['date'] == '2026-01-05'
        assert day_data['order_count'] == 2
        # Revenue: (100 - 0) + (200 - 10) = 290
        assert day_data['revenue'] == 290.0
        # Shipping revenue: 10 + 15 = 25
        assert day_data['shipping_revenue'] == 25.0
        # Shipping cost: 25 * 1.05 = 26.25
        assert day_data['shipping_cost'] == 26.25

    def test_extract_order_details(self, shopify_sync_task, mock_shopify_orders):
        """Test extracting individual order details."""
        orders = mock_shopify_orders['orders']
        orders_data = shopify_sync_task._extract_order_details(orders)

        assert len(orders_data) == 2

        # Verify first order
        order1 = orders_data[0]
        assert order1['id'] == '6597871993140'
        assert order1['order_number'] == 1001
        assert order1['order_date'] == '2026-01-05'
        assert order1['customer_email'] == 'customer1@example.com'
        assert order1['subtotal'] == 100.0
        assert order1['total_price'] == 115.0
        assert order1['shipping_charged'] == 10.0
        assert order1['financial_status'] == 'paid'
        assert len(order1['items']) == 1

        # Verify line item
        item = order1['items'][0]
        assert item['product_id'] == '123456'
        assert item['variant_id'] == '789012'
        assert item['product_title'] == 'Test Product 1'
        assert item['quantity'] == 2
        assert item['price'] == 50.0
        assert item['total'] == 100.0

    def test_extract_order_details_multiple_items(self, shopify_sync_task):
        """Test extracting orders with multiple line items."""
        orders = [
            {
                "id": 123,
                "order_number": 1003,
                "created_at": "2026-01-05T12:00:00Z",
                "email": "customer@example.com",
                "subtotal_price": "150.00",
                "total_price": "165.00",
                "total_discounts": "0.00",
                "currency": "USD",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "shipping_lines": [{"price": "5.00"}],
                "line_items": [
                    {
                        "product_id": 111,
                        "variant_id": 222,
                        "title": "Product A",
                        "variant_title": "Small",
                        "quantity": 1,
                        "price": "50.00"
                    },
                    {
                        "product_id": 333,
                        "variant_id": 444,
                        "title": "Product B",
                        "variant_title": "Medium",
                        "quantity": 2,
                        "price": "50.00"
                    }
                ]
            }
        ]

        orders_data = shopify_sync_task._extract_order_details(orders)

        assert len(orders_data) == 1
        assert len(orders_data[0]['items']) == 2

        # Verify both items
        items = orders_data[0]['items']
        assert items[0]['product_title'] == 'Product A'
        assert items[0]['quantity'] == 1
        assert items[1]['product_title'] == 'Product B'
        assert items[1]['quantity'] == 2

    @pytest.mark.asyncio
    async def test_run_task_loop(self, shopify_sync_task):
        """Test the periodic task loop."""
        # Mock the sync method to track calls
        sync_count = 0

        async def mock_sync():
            nonlocal sync_count
            sync_count += 1
            if sync_count >= 2:
                shopify_sync_task.is_running = False

        shopify_sync_task.sync_shopify_data = mock_sync
        shopify_sync_task.interval_minutes = 0.01  # Very short interval for testing

        # Run for a short time
        await asyncio.wait_for(shopify_sync_task.run(), timeout=5.0)

        # Verify sync was called multiple times
        assert sync_count >= 2

    @pytest.mark.asyncio
    async def test_start_task(self, shopify_sync_task):
        """Test starting the background task."""
        shopify_sync_task.start()

        assert shopify_sync_task.task is not None
        assert not shopify_sync_task.task.done()

        # Cleanup
        await shopify_sync_task.stop()

    @pytest.mark.asyncio
    async def test_stop_task(self, shopify_sync_task):
        """Test stopping the background task."""
        shopify_sync_task.start()
        await asyncio.sleep(0.1)

        await shopify_sync_task.stop()

        assert shopify_sync_task.is_running is False


@pytest.mark.unit
class TestMetaSyncTask:
    """Test Meta Ads automatic sync background task."""

    @pytest.fixture
    def meta_sync_task(self):
        """Create a Meta sync task for testing."""
        return MetaSyncTask(interval_minutes=10)

    @pytest.fixture
    def mock_meta_campaigns(self):
        """Sample Meta campaigns response."""
        return {
            "data": [
                {
                    "id": "23374457007",
                    "name": "Test Campaign 1",
                    "status": "ACTIVE",
                    "objective": "OUTCOME_TRAFFIC",
                    "insights": {
                        "data": [
                            {
                                "date_start": "2026-01-05",
                                "spend": "50.00",
                                "impressions": "1000",
                                "clicks": "50",
                                "reach": "800",
                                "actions": [
                                    {
                                        "action_type": "purchase",
                                        "value": "5"
                                    }
                                ],
                                "action_values": [
                                    {
                                        "action_type": "purchase",
                                        "value": "250.00"
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_sync_meta_data_success(self, test_db, meta_sync_task, mock_meta_campaigns):
        """Test successful Meta data sync."""
        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "test-token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123456")

        # Mock requests.get
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = mock_meta_campaigns
            mock_get.return_value = mock_response

            # Execute sync
            await meta_sync_task.sync_meta_data()

            # Verify campaign was stored
            campaigns = CampaignDatabase.get_all_campaigns()
            assert len(campaigns) > 0
            assert campaigns[0]['id'] == '23374457007'
            assert campaigns[0]['name'] == 'Test Campaign 1'

    @pytest.mark.asyncio
    async def test_sync_meta_data_no_credentials(self, test_db, meta_sync_task):
        """Test sync when credentials are not configured."""
        # Don't set any credentials
        await meta_sync_task.sync_meta_data()

        # Verify no data was stored
        campaigns = CampaignDatabase.get_all_campaigns()
        assert len(campaigns) == 0

    @pytest.mark.asyncio
    async def test_sync_meta_data_api_error(self, test_db, meta_sync_task):
        """Test sync when Meta API returns an error."""
        # Setup credentials
        SettingsDatabase.set_setting("meta_access_token", "test-token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123456")

        # Mock requests.get with error
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.ok = False
            mock_response.json.return_value = {
                "error": {"message": "Invalid token"}
            }
            mock_get.return_value = mock_response

            # Execute sync
            await meta_sync_task.sync_meta_data()

            # Verify no campaigns were stored
            campaigns = CampaignDatabase.get_all_campaigns()
            assert len(campaigns) == 0


@pytest.mark.unit
class TestShippingCalculationTask:
    """Test automatic shipping calculation background task."""

    @pytest.fixture
    def shipping_calc_task(self):
        """Create a shipping calculation task for testing."""
        return ShippingCalculationTask(interval_minutes=10)

    @pytest.fixture
    def sample_uncalculated_orders(self, test_db):
        """Create sample orders without shipping calculations."""
        from datetime import date
        orders = []
        for i in range(3):
            order = {
                'id': f'order-{i}',
                'order_number': 1000 + i,
                'order_date': str(date.today()),
                'customer_email': f'customer{i}@example.com',
                'subtotal': 100.0,
                'total_price': 115.0,
                'shipping_charged': 12.0,
                'currency': 'USD',
                'financial_status': 'paid',
                'fulfillment_status': 'fulfilled'
            }
            ShippingDatabase.upsert_order(order)

            # Add line items
            items = [{
                'product_id': '999',
                'variant_id': '888',
                'product_title': 'Test Product',
                'variant_title': 'Small',
                'quantity': 1,
                'price': 100.0,
                'total': 100.0
            }]
            ShippingDatabase.insert_order_items(order['id'], items)
            orders.append(order)

        return orders

    @pytest.fixture
    def sample_shipping_profile_for_calc(self, test_db):
        """Create a sample shipping profile."""
        profile = {
            "id": "profile-calc-1",
            "name": "Test Shipping Rule",
            "priority": 10,
            "is_active": True,
            "is_default": False,
            "match_conditions": {
                "field": "product_title",
                "operator": "contains",
                "value": "Test"
            },
            "cost_rules": {
                "type": "fixed",
                "base_cost": 10.0
            }
        }
        ShippingDatabase.upsert_shipping_profile(profile)
        return profile

    @pytest.mark.asyncio
    async def test_calculate_shipping_costs_success(
        self,
        test_db,
        shipping_calc_task,
        sample_uncalculated_orders,
        sample_shipping_profile_for_calc
    ):
        """Test successful shipping calculation."""
        # Execute calculation
        await shipping_calc_task.calculate_shipping_costs()

        # Verify calculations were saved
        for order in sample_uncalculated_orders:
            order_detail = ShippingDatabase.get_order_detail(order['id'])
            assert order_detail is not None
            # Should have calculated cost now
            assert 'shipping_cost_estimated' in order_detail or 'calculated_cost' in order_detail

    @pytest.mark.asyncio
    async def test_calculate_shipping_costs_no_uncalculated(self, test_db, shipping_calc_task):
        """Test calculation when there are no uncalculated orders."""
        # Execute calculation (should complete without error)
        await shipping_calc_task.calculate_shipping_costs()

    @pytest.mark.asyncio
    async def test_calculate_shipping_costs_no_profiles(
        self,
        test_db,
        shipping_calc_task,
        sample_uncalculated_orders
    ):
        """Test calculation when no shipping profiles exist."""
        # Execute calculation (should skip)
        await shipping_calc_task.calculate_shipping_costs()

        # Orders should still exist but without calculations
        for order in sample_uncalculated_orders:
            order_detail = ShippingDatabase.get_order_detail(order['id'])
            assert order_detail is not None


@pytest.mark.unit
class TestBackgroundTaskIntegration:
    """Integration tests for background tasks working together."""

    @pytest.mark.asyncio
    async def test_shopify_sync_feeds_shipping_calc(self, test_db):
        """Test that Shopify sync creates orders that shipping calc can process."""
        # Setup
        shopify_sync = ShopifySyncTask(interval_minutes=10)
        shipping_calc = ShippingCalculationTask(interval_minutes=10)

        # Configure Shopify credentials
        SettingsDatabase.set_setting("shopify_shop_name", "test-shop")
        SettingsDatabase.set_setting("shopify_access_token", "test-token")

        # Create shipping profile
        profile = {
            "id": "profile-int-1",
            "name": "Integration Test Rule",
            "priority": 10,
            "is_active": True,
            "is_default": False,
            "match_conditions": {
                "field": "product_title",
                "operator": "contains",
                "value": "Test"
            },
            "cost_rules": {
                "type": "fixed",
                "base_cost": 8.0
            }
        }
        ShippingDatabase.upsert_shipping_profile(profile)

        # Mock Shopify API response
        mock_orders = {
            "orders": [
                {
                    "id": 999999,
                    "order_number": 2001,
                    "created_at": "2026-01-05T10:00:00Z",
                    "email": "integration@example.com",
                    "subtotal_price": "100.00",
                    "total_price": "115.00",
                    "total_discounts": "0.00",
                    "currency": "USD",
                    "financial_status": "paid",
                    "fulfillment_status": "fulfilled",
                    "shipping_lines": [{"price": "10.00"}],
                    "line_items": [
                        {
                            "product_id": 111,
                            "variant_id": 222,
                            "title": "Test Product",
                            "variant_title": "Small",
                            "quantity": 1,
                            "price": "100.00"
                        }
                    ]
                }
            ]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_orders

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            # Run Shopify sync
            await shopify_sync.sync_shopify_data()

        # Verify order was created
        orders = ShippingDatabase.get_orders(days=7)
        assert len(orders) >= 1

        # Run shipping calculation
        await shipping_calc.calculate_shipping_costs()

        # Verify calculation was applied
        order_detail = ShippingDatabase.get_order_detail('999999')
        assert order_detail is not None
