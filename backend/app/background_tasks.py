"""
Background tasks for automatic data syncing.
"""
import asyncio
import logging
from datetime import datetime, timedelta
import httpx
from app.database import SettingsDatabase, ShopifyDatabase

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


# Global instance
shopify_sync_task = ShopifySyncTask(interval_hours=1)
