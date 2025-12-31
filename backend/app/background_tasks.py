"""
Background tasks for automatic data syncing.
"""
import asyncio
import logging
from datetime import datetime, timedelta
import httpx
import requests
from app.database import SettingsDatabase, ShopifyDatabase, CampaignDatabase

logger = logging.getLogger(__name__)


class ShopifySyncTask:
    """Background task to automatically sync Shopify data."""

    def __init__(self, interval_hours: int = 1):
        """
        Initialize Shopify sync task.

        Args:
            interval_hours: How often to sync in hours (default: 1 hour)
        """
        self.interval_hours = interval_hours
        self.is_running = False
        self.task = None

    async def sync_shopify_data(self):
        """Sync Shopify data using stored credentials."""
        try:
            # Load credentials from database
            shop_name = SettingsDatabase.get_setting("shopify_shop_name")
            access_token = SettingsDatabase.get_setting("shopify_access_token")

            if not shop_name or not access_token:
                logger.info("Shopify credentials not configured. Skipping sync.")
                return

            logger.info(f"Starting Shopify sync for shop: {shop_name}")

            # Fetch orders from Shopify for the last 30 days
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()

            url = f"https://{shop_name}.myshopify.com/admin/api/2024-01/orders.json"

            params = {
                "status": "any",
                "created_at_min": start_date.isoformat(),
                "created_at_max": end_date.isoformat(),
                "limit": 250,
            }

            headers = {
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)

            if response.status_code == 401:
                logger.error("Invalid Shopify access token. Please check credentials.")
                return

            if response.status_code != 200:
                logger.error(f"Shopify API error: {response.status_code} - {response.text}")
                return

            data = response.json()
            orders = data.get("orders", [])

            # Aggregate orders by date
            daily_metrics = self._aggregate_orders_by_date(orders)

            # Push to database
            result = ShopifyDatabase.bulk_upsert_from_orders(daily_metrics)

            logger.info(f"✓ Shopify sync completed: {len(orders)} orders processed, {result['records_processed']} records updated")

        except httpx.TimeoutException:
            logger.error("Shopify API request timed out")
        except Exception as e:
            logger.error(f"Failed to sync Shopify data: {str(e)}")

    def _aggregate_orders_by_date(self, orders: list) -> list:
        """Aggregate Shopify orders by date."""
        daily_metrics = {}

        for order in orders:
            order_date = order['created_at'].split('T')[0]

            if order_date not in daily_metrics:
                daily_metrics[order_date] = {
                    "date": order_date,
                    "revenue": 0,
                    "shipping_revenue": 0,
                    "shipping_cost": 0,
                    "order_count": 0,
                }

            # Revenue = subtotal - discounts
            subtotal = float(order.get('subtotal_price', 0))
            discounts = float(order.get('total_discounts', 0))
            revenue = subtotal - discounts

            # Shipping Revenue = what customer paid for shipping
            shipping_revenue = sum(
                float(line.get('price', 0))
                for line in order.get('shipping_lines', [])
            )

            # Shipping Cost = shipping sold * 1.05 (assume 5% markup on cost)
            shipping_cost = shipping_revenue * 1.05

            daily_metrics[order_date]['revenue'] += revenue
            daily_metrics[order_date]['shipping_revenue'] += shipping_revenue
            daily_metrics[order_date]['shipping_cost'] += shipping_cost
            daily_metrics[order_date]['order_count'] += 1

        return list(daily_metrics.values())

    async def run(self):
        """Run the sync task periodically."""
        self.is_running = True
        logger.info(f"Shopify sync task started (interval: {self.interval_hours}h)")

        while self.is_running:
            try:
                await self.sync_shopify_data()
            except Exception as e:
                logger.error(f"Error in Shopify sync task: {e}")

            # Wait for the next interval
            await asyncio.sleep(self.interval_hours * 3600)

    def start(self):
        """Start the background task."""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())
            logger.info("Shopify sync background task scheduled")

    async def stop(self):
        """Stop the background task."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Shopify sync background task stopped")


class MetaSyncTask:
    """Background task to automatically sync Meta Ads data."""

    def __init__(self, interval_minutes: int = 10):
        """
        Initialize Meta sync task.

        Args:
            interval_minutes: How often to sync in minutes (default: 10 minutes)
        """
        self.interval_minutes = interval_minutes
        self.is_running = False
        self.task = None

    async def sync_meta_data(self):
        """Sync Meta Ads data using stored credentials."""
        try:
            # Load credentials from database
            access_token = SettingsDatabase.get_setting("meta_access_token")
            ad_account_id = SettingsDatabase.get_setting("meta_ad_account_id")

            if not access_token or not ad_account_id:
                logger.info("Meta credentials not configured. Skipping sync.")
                return

            logger.info(f"Starting Meta sync for ad account: {ad_account_id}")

            # Calculate date range (last 30 days)
            days = 30
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_start = start_date.strftime('%Y-%m-%d')
            date_end = end_date.strftime('%Y-%m-%d')

            api_version = "v18.0"
            url = f"https://graph.facebook.com/{api_version}/{ad_account_id}/campaigns"

            # Request campaigns with insights
            params = {
                "access_token": access_token,
                "fields": f"id,name,status,objective,daily_budget,lifetime_budget,insights.time_range({{'since':'{date_start}','until':'{date_end}'}}).time_increment(1){{spend,impressions,clicks,ctr,cpm,cpp,reach,frequency,actions,action_values,cost_per_action_type}}",
                "limit": 100
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 401:
                logger.error("Invalid Meta access token. Please check credentials.")
                return

            if not response.ok:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Meta API error: {error_message}")
                return

            data = response.json()
            campaigns = data.get('data', [])

            # Store campaigns and metrics in database
            campaigns_count = 0
            metrics_count = 0

            for campaign in campaigns:
                # Upsert campaign
                CampaignDatabase.upsert_campaign(
                    campaign_id=campaign['id'],
                    name=campaign['name'],
                    status=campaign['status'],
                    platform='meta'
                )
                campaigns_count += 1

                # Get daily insights data
                campaign_id = campaign['id']
                insights = campaign.get('insights', {}).get('data', [])

                for insight in insights:
                    date_value = insight.get('date_start')
                    if not date_value:
                        continue

                    # Store each metric
                    metrics_to_store = [
                        ('spend', float(insight.get('spend', 0)), 'USD'),
                        ('impressions', int(insight.get('impressions', 0)), 'count'),
                        ('clicks', int(insight.get('clicks', 0)), 'count'),
                        ('reach', int(insight.get('reach', 0)), 'count'),
                    ]

                    # Calculate CTR
                    impressions = int(insight.get('impressions', 0))
                    clicks = int(insight.get('clicks', 0))
                    ctr = (clicks / impressions * 100) if impressions > 0 else 0
                    metrics_to_store.append(('ctr', ctr, '%'))

                    # Store conversions and conversion_value
                    actions = insight.get('actions', [])
                    conversions = 0
                    for action in actions:
                        if action.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                            conversions += float(action.get('value', 0))
                    metrics_to_store.append(('conversions', conversions, 'count'))

                    action_values = insight.get('action_values', [])
                    conversion_value = 0
                    for action_value in action_values:
                        if action_value.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                            conversion_value += float(action_value.get('value', 0))
                    metrics_to_store.append(('conversion_value', conversion_value, 'USD'))

                    for metric_name, value, unit in metrics_to_store:
                        CampaignDatabase.upsert_metric(
                            campaign_id=campaign_id,
                            date_value=date_value,
                            metric_name=metric_name,
                            value=value,
                            unit=unit
                        )
                        metrics_count += 1

            # Log successful sync
            CampaignDatabase.log_sync(campaigns_count, metrics_count, "success")

            logger.info(f"✓ Meta sync completed: {campaigns_count} campaigns, {metrics_count} metrics updated")

        except requests.exceptions.Timeout:
            logger.error("Meta API request timed out")
        except Exception as e:
            logger.error(f"Failed to sync Meta data: {str(e)}")

    async def run(self):
        """Run the sync task periodically."""
        self.is_running = True
        logger.info(f"Meta sync task started (interval: {self.interval_minutes} minutes)")

        while self.is_running:
            try:
                await self.sync_meta_data()
            except Exception as e:
                logger.error(f"Error in Meta sync task: {e}")

            # Wait for the next interval
            await asyncio.sleep(self.interval_minutes * 60)

    def start(self):
        """Start the background task."""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())
            logger.info("Meta sync background task scheduled")

    async def stop(self):
        """Stop the background task."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Meta sync background task stopped")


class ShippingCalculationTask:
    """Background task to automatically calculate shipping costs for uncalculated orders."""

    def __init__(self, interval_minutes: int = 10):
        """
        Initialize shipping calculation task.

        Args:
            interval_minutes: How often to calculate in minutes (default: 10 minutes)
        """
        self.interval_minutes = interval_minutes
        self.is_running = False
        self.task = None

    async def calculate_shipping_costs(self):
        """Calculate shipping costs for orders that don't have estimates yet."""
        try:
            # Get uncalculated orders
            from app.database import ShippingDatabase
            uncalculated_order_ids = ShippingDatabase.get_uncalculated_orders(limit=100)

            if not uncalculated_order_ids:
                logger.info("No uncalculated orders found. Skipping shipping calculation.")
                return

            logger.info(f"Starting shipping calculation for {len(uncalculated_order_ids)} orders")

            # Get active shipping profiles
            profiles = ShippingDatabase.get_shipping_profiles(active_only=True)

            if not profiles:
                logger.info("No active shipping profiles configured. Skipping calculation.")
                return

            # Calculate each order
            calculated_count = 0
            for order_id in uncalculated_order_ids:
                try:
                    # Get order details
                    order = ShippingDatabase.get_order_detail(order_id)
                    if not order:
                        continue

                    # Import calculation function from shipping router
                    from app.routers.shipping import calculate_order_shipping_cost

                    # Calculate shipping cost
                    result = calculate_order_shipping_cost(
                        order=order,
                        items=order.get('items', []),
                        profiles=profiles
                    )

                    # Save calculation
                    matched_profile_id = None
                    if result.get('breakdown'):
                        matched_profile_id = result['breakdown'][0].get('profile_id')

                    ShippingDatabase.save_shipping_calculation(
                        order_id=order_id,
                        profile_id=matched_profile_id,
                        calculated_cost=result['total_cost'],
                        details=result
                    )

                    calculated_count += 1

                except Exception as e:
                    logger.error(f"Failed to calculate shipping for order {order_id}: {str(e)}")
                    continue

            logger.info(f"✓ Shipping calculation completed: {calculated_count} orders processed")

        except Exception as e:
            logger.error(f"Failed to calculate shipping costs: {str(e)}")

    async def run(self):
        """Run the calculation task periodically."""
        self.is_running = True
        logger.info(f"Shipping calculation task started (interval: {self.interval_minutes} minutes)")

        while self.is_running:
            try:
                await self.calculate_shipping_costs()
            except Exception as e:
                logger.error(f"Error in shipping calculation task: {e}")

            # Wait for the next interval
            await asyncio.sleep(self.interval_minutes * 60)

    def start(self):
        """Start the background task."""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())
            logger.info("Shipping calculation background task scheduled")

    async def stop(self):
        """Stop the background task."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Shipping calculation background task stopped")


# Global instances
shopify_sync_task = ShopifySyncTask(interval_hours=1)
meta_sync_task = MetaSyncTask(interval_minutes=10)
shipping_calculation_task = ShippingCalculationTask(interval_minutes=10)
