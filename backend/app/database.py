"""
Database module for storing campaign data locally.
Uses SQLite for lightweight, serverless storage.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional
import json

DATABASE_PATH = Path(__file__).parent.parent / "data" / "campaigns.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Campaigns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                platform TEXT DEFAULT 'google_ads',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Campaign metrics table (time series data)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaign_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                date DATE NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
                UNIQUE(campaign_id, date, metric_name)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_campaign_metrics_campaign_date
            ON campaign_metrics(campaign_id, date DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_campaign_metrics_metric_name
            ON campaign_metrics(metric_name)
        """)

        # Sync log table to track data updates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                campaigns_count INTEGER,
                metrics_count INTEGER,
                status TEXT,
                error_message TEXT
            )
        """)

        # Shopify daily metrics table (aggregated revenue and costs by date)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopify_daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                revenue REAL DEFAULT 0,
                shipping_revenue REAL DEFAULT 0,
                shipping_cost REAL DEFAULT 0,
                order_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for date lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shopify_daily_metrics_date
            ON shopify_daily_metrics(date DESC)
        """)

        # Shopify orders table (individual order records)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopify_orders (
                id TEXT PRIMARY KEY,
                order_number INTEGER NOT NULL,
                order_date DATE NOT NULL,
                customer_email TEXT,
                subtotal REAL NOT NULL,
                total_price REAL NOT NULL,
                shipping_charged REAL DEFAULT 0,
                shipping_cost_estimated REAL,
                currency TEXT DEFAULT 'USD',
                financial_status TEXT,
                fulfillment_status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shopify_orders_date
            ON shopify_orders(order_date DESC)
        """)

        # Shopify order items table (line items per order)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopify_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                product_id TEXT,
                variant_id TEXT,
                product_title TEXT NOT NULL,
                variant_title TEXT,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES shopify_orders(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shopify_order_items_order
            ON shopify_order_items(order_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shopify_order_items_title
            ON shopify_order_items(product_title)
        """)

        # Shipping profiles table (user-defined shipping rules)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shipping_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                match_conditions TEXT NOT NULL,
                cost_rules TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shipping_profiles_priority
            ON shipping_profiles(priority ASC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shipping_profiles_active
            ON shipping_profiles(is_active)
        """)

        # Order shipping calculations table (audit trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_shipping_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                profile_id TEXT,
                calculated_cost REAL NOT NULL,
                calculation_details TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES shopify_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (profile_id) REFERENCES shipping_profiles(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_shipping_calc_order
            ON order_shipping_calculations(order_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_shipping_calc_date
            ON order_shipping_calculations(applied_at DESC)
        """)

        # Settings table for storing configuration (like Shopify credentials)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                encrypted BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Shopping products table (one row per product-campaign combination)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_products (
                product_id TEXT NOT NULL,
                product_title TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                campaign_name TEXT,
                ad_group_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_id, campaign_id)
            )
        """)

        # Product metrics table (time series data for Shopping products per campaign)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                date DATE NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id, campaign_id) REFERENCES shopping_products(product_id, campaign_id) ON DELETE CASCADE,
                UNIQUE(product_id, campaign_id, date, metric_name)
            )
        """)

        # Create indexes for product metrics performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_metrics_product_campaign_date
            ON product_metrics(product_id, campaign_id, date DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_metrics_metric_name
            ON product_metrics(metric_name)
        """)

        # Migration: Add ad_group_id column to shopping_products if it doesn't exist
        try:
            cursor.execute("SELECT ad_group_id FROM shopping_products LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE shopping_products ADD COLUMN ad_group_id TEXT")
            print("✓ Migration: Added ad_group_id column to shopping_products table")

        # Migration: Convert average_cpc to cpc with proper unit and value conversion
        # This migration should only run once, so we check if any old average_cpc records exist

        # Check product metrics
        cursor.execute("SELECT COUNT(*) FROM product_metrics WHERE metric_name = 'average_cpc'")
        product_avg_cpc_count = cursor.fetchone()[0]

        if product_avg_cpc_count > 0:
            print(f"✓ Migration: Found {product_avg_cpc_count} average_cpc records in products, cleaning up...")
            cursor.execute("DELETE FROM product_metrics WHERE metric_name = 'average_cpc'")
            print(f"✓ Migration: Deleted product average_cpc records (will be re-inserted as 'cpc' on next data sync)")

        # Check campaign metrics
        cursor.execute("SELECT COUNT(*) FROM campaign_metrics WHERE metric_name = 'average_cpc'")
        campaign_avg_cpc_count = cursor.fetchone()[0]

        if campaign_avg_cpc_count > 0:
            print(f"✓ Migration: Found {campaign_avg_cpc_count} average_cpc records in campaigns, cleaning up...")
            cursor.execute("DELETE FROM campaign_metrics WHERE metric_name = 'average_cpc'")
            print(f"✓ Migration: Deleted campaign average_cpc records (will be re-inserted as 'cpc' on next data sync)")

        conn.commit()


class CampaignDatabase:
    """Database operations for campaign data."""

    @staticmethod
    def upsert_campaign(campaign_id: str, name: str, status: str, platform: str = "google_ads"):
        """Insert or update a campaign."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO campaigns (id, name, status, platform, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    platform = excluded.platform,
                    updated_at = CURRENT_TIMESTAMP
            """, (campaign_id, name, status, platform))

    @staticmethod
    def upsert_metric(campaign_id: str, date_value: str, metric_name: str, value: float, unit: str):
        """Insert or update a metric data point."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO campaign_metrics (campaign_id, date, metric_name, value, unit)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id, date, metric_name) DO UPDATE SET
                    value = excluded.value,
                    unit = excluded.unit,
                    created_at = CURRENT_TIMESTAMP
            """, (campaign_id, date_value, metric_name, value, unit))

    @staticmethod
    def get_all_campaigns() -> List[dict]:
        """Get all campaigns with their latest metrics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    c.id,
                    c.name,
                    c.status,
                    c.platform,
                    c.updated_at
                FROM campaigns c
                ORDER BY c.name
            """)
            campaigns = []
            for row in cursor.fetchall():
                campaign = dict(row)

                # Get latest metrics for this campaign
                campaign['metrics'] = CampaignDatabase.get_latest_metrics(campaign['id'])
                campaigns.append(campaign)

            return campaigns

    @staticmethod
    def get_latest_metrics(campaign_id: str) -> List[dict]:
        """Get aggregated metrics for the last 7 days for a campaign."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    metric_name as name,
                    CASE
                        WHEN metric_name = 'ctr' THEN AVG(value)
                        ELSE SUM(value)
                    END as value,
                    unit
                FROM campaign_metrics
                WHERE campaign_id = ?
                    AND date >= date('now', 'localtime', '-7 days')
                GROUP BY metric_name, unit
                ORDER BY metric_name
            """, (campaign_id,))

            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_campaign_time_series(campaign_id: str, metric_name: str, days: int = 30) -> dict:
        """Get time series data for a specific metric."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get campaign info
            cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
            campaign_row = cursor.fetchone()
            if not campaign_row:
                return None

            campaign = dict(campaign_row)

            # Get metric data points for last N days
            # Use '-(days-1) days' so we get exactly N days: today, yesterday, ..., N-1 days ago
            cursor.execute("""
                SELECT
                    date,
                    value,
                    unit
                FROM campaign_metrics
                WHERE campaign_id = ? AND metric_name = ?
                    AND date >= date('now', 'localtime', ?)
                ORDER BY date ASC
            """, (campaign_id, metric_name, f'-{days - 1} days'))

            data_points = [dict(row) for row in cursor.fetchall()]

            return {
                "campaign_id": campaign['id'],
                "campaign_name": campaign['name'],
                "metric_name": metric_name,
                "unit": data_points[0]['unit'] if data_points else "",
                "data_points": data_points
            }

    @staticmethod
    def get_all_campaigns_time_series(metric_name: str, days: int = 30) -> List[dict]:
        """Get time series data for all campaigns for a specific metric."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get all campaigns
            cursor.execute("SELECT id, name, status FROM campaigns WHERE status = 'ENABLED' ORDER BY name")
            campaigns = cursor.fetchall()

            result = []
            for campaign in campaigns:
                campaign_id = campaign['id']
                campaign_name = campaign['name']

                # Get metric data points for this campaign
                cursor.execute("""
                    SELECT
                        date,
                        value,
                        unit
                    FROM campaign_metrics
                    WHERE campaign_id = ? AND metric_name = ?
                        AND date >= date('now', 'localtime', ?)
                    ORDER BY date ASC
                """, (campaign_id, metric_name, f'-{days} days'))

                data_points = [dict(row) for row in cursor.fetchall()]

                if data_points:  # Only include campaigns with data
                    result.append({
                        "campaign_id": campaign_id,
                        "campaign_name": campaign_name,
                        "metric_name": metric_name,
                        "unit": data_points[0]['unit'] if data_points else "",
                        "data_points": data_points
                    })

            return result

    @staticmethod
    def get_all_metrics_time_series(campaign_id: str, days: int = 30) -> dict:
        """Get time series data for all metrics of a campaign."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get all unique metric names for this campaign
            cursor.execute("""
                SELECT DISTINCT metric_name
                FROM campaign_metrics
                WHERE campaign_id = ?
            """, (campaign_id,))

            metric_names = [row['metric_name'] for row in cursor.fetchall()]

            result = {}
            for metric_name in metric_names:
                result[metric_name] = CampaignDatabase.get_campaign_time_series(
                    campaign_id, metric_name, days
                )

            return result

    @staticmethod
    def log_sync(campaigns_count: int, metrics_count: int, status: str = "success", error: str = None):
        """Log a data sync event."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_log (campaigns_count, metrics_count, status, error_message)
                VALUES (?, ?, ?, ?)
            """, (campaigns_count, metrics_count, status, error))

    @staticmethod
    def get_last_sync() -> Optional[dict]:
        """Get information about the last successful sync."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM sync_log
                WHERE status = 'success'
                ORDER BY synced_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def bulk_upsert_from_script(data: dict):
        """
        Bulk upsert data received from Google Ads Script.

        Expected data format:
        {
            "campaigns": [
                {
                    "id": "123",
                    "name": "Campaign Name",
                    "status": "ENABLED",
                    "metrics": [
                        {"date": "2025-12-25", "name": "spend", "value": 100.50, "unit": "USD"},
                        {"date": "2025-12-25", "name": "clicks", "value": 50, "unit": "count"}
                    ]
                }
            ]
        }
        """
        campaigns_count = 0
        metrics_count = 0

        try:
            for campaign in data.get("campaigns", []):
                # Upsert campaign
                CampaignDatabase.upsert_campaign(
                    campaign_id=campaign['id'],
                    name=campaign['name'],
                    status=campaign['status'],
                    platform=campaign.get('platform', 'google_ads')
                )
                campaigns_count += 1

                # Group metrics by date for CPC backfilling
                metrics_by_date = {}
                for metric in campaign.get('metrics', []):
                    date_value = metric['date']
                    if date_value not in metrics_by_date:
                        metrics_by_date[date_value] = []
                    metrics_by_date[date_value].append(metric)

                # Process each date's metrics
                for date_value, date_metrics in metrics_by_date.items():
                    has_cpc = False
                    has_clicks = False
                    clicks_value = 0

                    # First pass: upsert all metrics and check for CPC/clicks
                    for metric in date_metrics:
                        metric_name = metric['name']
                        metric_value = float(metric['value'])
                        metric_unit = metric['unit']

                        if metric_name == 'average_cpc':
                            has_cpc = True
                            # Convert from micros (count) to USD
                            metric_name = 'cpc'
                            if metric_unit == 'count':  # Still in micros
                                metric_value = metric_value / 1000000
                                metric_unit = 'USD'
                        elif metric_name == 'clicks':
                            has_clicks = True
                            clicks_value = metric_value

                        CampaignDatabase.upsert_metric(
                            campaign_id=campaign['id'],
                            date_value=date_value,
                            metric_name=metric_name,
                            value=metric_value,
                            unit=metric_unit
                        )
                        metrics_count += 1

                    # If we have clicks=0 but no CPC, add CPC=0
                    if has_clicks and clicks_value == 0 and not has_cpc:
                        CampaignDatabase.upsert_metric(
                            campaign_id=campaign['id'],
                            date_value=date_value,
                            metric_name='cpc',
                            value=0.0,
                            unit='USD'
                        )
                        metrics_count += 1

            # Log successful sync
            CampaignDatabase.log_sync(campaigns_count, metrics_count, "success")

            return {
                "success": True,
                "campaigns_processed": campaigns_count,
                "metrics_processed": metrics_count
            }

        except Exception as e:
            # Log failed sync
            CampaignDatabase.log_sync(campaigns_count, metrics_count, "error", str(e))
            raise


class ShopifyDatabase:
    """Database operations for Shopify revenue data."""

    @staticmethod
    def upsert_daily_metrics(date_value: str, revenue: float, shipping_revenue: float,
                            shipping_cost: float, order_count: int):
        """Insert or update Shopify metrics for a specific date."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shopify_daily_metrics
                (date, revenue, shipping_revenue, shipping_cost, order_count, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    revenue = excluded.revenue,
                    shipping_revenue = excluded.shipping_revenue,
                    shipping_cost = excluded.shipping_cost,
                    order_count = excluded.order_count,
                    updated_at = CURRENT_TIMESTAMP
            """, (date_value, revenue, shipping_revenue, shipping_cost, order_count))

    @staticmethod
    def get_metrics_summary(days: int = 7) -> dict:
        """Get aggregated Shopify metrics for the last N days."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Query individual orders directly - no need for pre-aggregated table
            # Use '-(days-1) days' so we get exactly N days: today, yesterday, ..., N-1 days ago
            cursor.execute("""
                SELECT
                    SUM(subtotal) as total_revenue,
                    SUM(shipping_charged) as total_shipping_revenue,
                    SUM(shipping_cost_estimated) as total_shipping_cost_estimated,
                    COUNT(*) as total_orders
                FROM shopify_orders
                WHERE order_date >= date('now', 'localtime', ?)
            """, (f'-{days - 1} days',))

            row = cursor.fetchone()
            if not row or row['total_revenue'] is None:
                return {
                    "total_revenue": 0,
                    "total_shipping_revenue": 0,
                    "total_shipping_cost": 0,
                    "total_orders": 0
                }

            return {
                "total_revenue": row['total_revenue'] or 0,
                "total_shipping_revenue": row['total_shipping_revenue'] or 0,
                "total_shipping_cost": row['total_shipping_cost_estimated'] or 0,
                "total_orders": row['total_orders'] or 0
            }

    @staticmethod
    def get_time_series(metric_name: str, days: int = 30) -> List[dict]:
        """Get time series data for a specific Shopify metric by aggregating orders."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Use '-(days-1) days' so we get exactly N days: today, yesterday, ..., N-1 days ago
            days_param = f'-{days - 1} days'

            # Map metric name to aggregation query
            if metric_name == 'revenue':
                query = """
                    SELECT order_date as date, SUM(subtotal) as value
                    FROM shopify_orders
                    WHERE order_date >= date('now', 'localtime', ?)
                    GROUP BY order_date
                    ORDER BY date ASC
                """
            elif metric_name == 'shipping_revenue':
                query = """
                    SELECT order_date as date, SUM(shipping_charged) as value
                    FROM shopify_orders
                    WHERE order_date >= date('now', 'localtime', ?)
                    GROUP BY order_date
                    ORDER BY date ASC
                """
            elif metric_name == 'shipping_cost':
                query = """
                    SELECT order_date as date, SUM(shipping_cost_estimated) as value
                    FROM shopify_orders
                    WHERE order_date >= date('now', 'localtime', ?) AND shipping_cost_estimated IS NOT NULL
                    GROUP BY order_date
                    ORDER BY date ASC
                """
            elif metric_name == 'orders':
                query = """
                    SELECT order_date as date, COUNT(*) as value
                    FROM shopify_orders
                    WHERE order_date >= date('now', 'localtime', ?)
                    GROUP BY order_date
                    ORDER BY date ASC
                """
            else:
                query = """
                    SELECT order_date as date, SUM(subtotal) as value
                    FROM shopify_orders
                    WHERE order_date >= date('now', 'localtime', ?)
                    GROUP BY order_date
                    ORDER BY date ASC
                """

            cursor.execute(query, (days_param,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def bulk_upsert_from_orders(orders_data: List[dict]):
        """
        Bulk upsert Shopify order data.

        Expected format:
        [
            {
                "date": "2025-12-25",
                "revenue": 150.00,
                "shipping_revenue": 10.00,
                "shipping_cost": 5.50,
                "order_count": 3
            }
        ]
        """
        records_count = 0

        try:
            for day_data in orders_data:
                ShopifyDatabase.upsert_daily_metrics(
                    date_value=day_data['date'],
                    revenue=float(day_data.get('revenue', 0)),
                    shipping_revenue=float(day_data.get('shipping_revenue', 0)),
                    shipping_cost=float(day_data.get('shipping_cost', 0)),
                    order_count=int(day_data.get('order_count', 0))
                )
                records_count += 1

            return {
                "success": True,
                "records_processed": records_count
            }

        except Exception as e:
            raise Exception(f"Failed to bulk upsert Shopify data: {str(e)}")


class ShippingDatabase:
    """Database operations for shipping rules and order-level data."""

    @staticmethod
    def upsert_order(order_data: dict):
        """Insert or update a Shopify order."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shopify_orders (
                    id, order_number, order_date, customer_email,
                    subtotal, total_price, shipping_charged,
                    currency, financial_status, fulfillment_status,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    order_number = excluded.order_number,
                    order_date = excluded.order_date,
                    customer_email = excluded.customer_email,
                    subtotal = excluded.subtotal,
                    total_price = excluded.total_price,
                    shipping_charged = excluded.shipping_charged,
                    currency = excluded.currency,
                    financial_status = excluded.financial_status,
                    fulfillment_status = excluded.fulfillment_status,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                order_data['id'],
                order_data['order_number'],
                order_data['order_date'],
                order_data.get('customer_email'),
                order_data['subtotal'],
                order_data['total_price'],
                order_data.get('shipping_charged', 0),
                order_data.get('currency', 'USD'),
                order_data.get('financial_status'),
                order_data.get('fulfillment_status')
            ))

    @staticmethod
    def insert_order_items(order_id: str, items: list):
        """Bulk insert line items for an order (replaces existing items)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete existing items for this order
            cursor.execute("DELETE FROM shopify_order_items WHERE order_id = ?", (order_id,))

            # Insert new items
            for item in items:
                cursor.execute("""
                    INSERT INTO shopify_order_items (
                        order_id, product_id, variant_id,
                        product_title, variant_title,
                        quantity, price, total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_id,
                    item.get('product_id'),
                    item.get('variant_id'),
                    item['product_title'],
                    item.get('variant_title'),
                    item['quantity'],
                    item['price'],
                    item['total']
                ))

    @staticmethod
    def get_orders(days: int = 30, status: str = None, limit: int = 100, offset: int = 0) -> list:
        """Get list of orders with optional filters."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    id, order_number, order_date, customer_email,
                    subtotal, total_price, shipping_charged, shipping_cost_estimated,
                    currency, financial_status, fulfillment_status
                FROM shopify_orders
                WHERE order_date >= date('now', 'localtime', '-' || ? || ' days')
            """
            params = [days]

            if status:
                query += " AND financial_status = ?"
                params.append(status)

            query += " ORDER BY order_date DESC, order_number DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                {
                    'id': row[0],
                    'order_number': row[1],
                    'order_date': row[2],
                    'customer_email': row[3],
                    'subtotal': row[4],
                    'total_price': row[5],
                    'shipping_charged': row[6],
                    'shipping_cost_estimated': row[7],
                    'currency': row[8],
                    'financial_status': row[9],
                    'fulfillment_status': row[10]
                }
                for row in rows
            ]

    @staticmethod
    def get_order_detail(order_id: str) -> dict:
        """Get single order with all line items."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get order
            cursor.execute("""
                SELECT
                    id, order_number, order_date, customer_email,
                    subtotal, total_price, shipping_charged, shipping_cost_estimated,
                    currency, financial_status, fulfillment_status
                FROM shopify_orders
                WHERE id = ?
            """, (order_id,))

            row = cursor.fetchone()
            if not row:
                return None

            order = {
                'id': row[0],
                'order_number': row[1],
                'order_date': row[2],
                'customer_email': row[3],
                'subtotal': row[4],
                'total_price': row[5],
                'shipping_charged': row[6],
                'shipping_cost_estimated': row[7],
                'currency': row[8],
                'financial_status': row[9],
                'fulfillment_status': row[10],
                'items': []
            }

            # Get line items
            cursor.execute("""
                SELECT
                    product_id, variant_id, product_title, variant_title,
                    quantity, price, total
                FROM shopify_order_items
                WHERE order_id = ?
            """, (order_id,))

            items = cursor.fetchall()
            order['items'] = [
                {
                    'product_id': item[0],
                    'variant_id': item[1],
                    'product_title': item[2],
                    'variant_title': item[3],
                    'quantity': item[4],
                    'price': item[5],
                    'total': item[6]
                }
                for item in items
            ]

            return order

    @staticmethod
    def upsert_shipping_profile(profile_data: dict):
        """Insert or update a shipping rule profile."""
        import uuid
        import json

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Generate UUID if not provided
            profile_id = profile_data.get('id', str(uuid.uuid4()))

            # If setting as default, unset other defaults
            if profile_data.get('is_default', False):
                cursor.execute("UPDATE shipping_profiles SET is_default = 0")

            cursor.execute("""
                INSERT INTO shipping_profiles (
                    id, name, description, priority, is_active, is_default,
                    match_conditions, cost_rules, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    priority = excluded.priority,
                    is_active = excluded.is_active,
                    is_default = excluded.is_default,
                    match_conditions = excluded.match_conditions,
                    cost_rules = excluded.cost_rules,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                profile_id,
                profile_data['name'],
                profile_data.get('description'),
                profile_data['priority'],
                profile_data.get('is_active', True),
                profile_data.get('is_default', False),
                json.dumps(profile_data['match_conditions']),
                json.dumps(profile_data['cost_rules'])
            ))

            return profile_id

    @staticmethod
    def get_shipping_profiles(active_only: bool = False) -> list:
        """Get all shipping profiles ordered by priority."""
        import json

        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT id, name, description, priority, is_active, is_default, match_conditions, cost_rules, created_at, updated_at FROM shipping_profiles"

            if active_only:
                query += " WHERE is_active = 1"

            query += " ORDER BY priority ASC, created_at ASC"

            cursor.execute(query)
            rows = cursor.fetchall()

            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'priority': row[3],
                    'is_active': bool(row[4]),
                    'is_default': bool(row[5]),
                    'match_conditions': json.loads(row[6]),
                    'cost_rules': json.loads(row[7]),
                    'created_at': row[8],
                    'updated_at': row[9]
                }
                for row in rows
            ]

    @staticmethod
    def delete_shipping_profile(profile_id: str):
        """Delete a shipping profile."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shipping_profiles WHERE id = ?", (profile_id,))

    @staticmethod
    def save_shipping_calculation(order_id: str, profile_id: str, calculated_cost: float, details: dict):
        """Save a shipping cost calculation result."""
        import json

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Save calculation record
            cursor.execute("""
                INSERT INTO order_shipping_calculations (
                    order_id, profile_id, calculated_cost, calculation_details
                )
                VALUES (?, ?, ?, ?)
            """, (
                order_id,
                profile_id,
                calculated_cost,
                json.dumps(details)
            ))

            # Update order with estimated cost
            cursor.execute("""
                UPDATE shopify_orders
                SET shipping_cost_estimated = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (calculated_cost, order_id))

    @staticmethod
    def get_shipping_calculations(order_id: str = None, days: int = 30) -> list:
        """Get shipping calculation history."""
        import json

        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    c.id, c.order_id, c.profile_id, p.name as profile_name,
                    c.calculated_cost, c.calculation_details, c.applied_at
                FROM order_shipping_calculations c
                LEFT JOIN shipping_profiles p ON c.profile_id = p.id
                WHERE c.applied_at >= date('now', 'localtime', '-' || ? || ' days')
            """
            params = [days]

            if order_id:
                query += " AND c.order_id = ?"
                params.append(order_id)

            query += " ORDER BY c.applied_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                {
                    'id': row[0],
                    'order_id': row[1],
                    'profile_id': row[2],
                    'profile_name': row[3],
                    'calculated_cost': row[4],
                    'calculation_details': json.loads(row[5]) if row[5] else {},
                    'applied_at': row[6]
                }
                for row in rows
            ]

    @staticmethod
    def get_uncalculated_orders(limit: int = 100) -> list:
        """Get orders that don't have shipping cost estimates yet."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id
                FROM shopify_orders
                WHERE shipping_cost_estimated IS NULL
                ORDER BY order_date DESC
                LIMIT ?
            """, (limit,))

            return [row['id'] for row in cursor.fetchall()]

    @staticmethod
    def bulk_upsert_orders(orders_data: list):
        """Bulk insert/update orders and their line items."""
        count = 0

        try:
            for order_data in orders_data:
                # Upsert order
                ShippingDatabase.upsert_order(order_data)

                # Insert line items if provided
                if 'items' in order_data:
                    ShippingDatabase.insert_order_items(order_data['id'], order_data['items'])

                count += 1

            return {
                'success': True,
                'orders_processed': count
            }

        except Exception as e:
            raise Exception(f"Failed to bulk upsert orders: {str(e)}")


class SettingsDatabase:
    """Database operations for application settings."""

    @staticmethod
    def set_setting(key: str, value: str, encrypted: bool = False):
        """Set or update a setting value (encryption parameter ignored - stored as plain text)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, encrypted, updated_at)
                VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    encrypted = 0,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value))

    @staticmethod
    def get_setting(key: str, default: str = None) -> Optional[str]:
        """Get a setting value (plain text, no decryption)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value
                FROM settings
                WHERE key = ?
            """, (key,))

            row = cursor.fetchone()
            if not row:
                return default

            return row['value']

    @staticmethod
    def delete_setting(key: str):
        """Delete a setting."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM settings WHERE key = ?", (key,))

    @staticmethod
    def get_all_settings() -> dict:
        """Get all settings (returns decrypted values)."""
        from cryptography.fernet import Fernet
        from app.config import settings as app_settings

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, encrypted FROM settings")

            result = {}
            for row in cursor.fetchall():
                key = row['key']
                value = row['value']
                encrypted = row['encrypted']

                if encrypted and app_settings.encryption_key:
                    try:
                        cipher = Fernet(app_settings.encryption_key.encode())
                        value = cipher.decrypt(value.encode()).decode()
                    except Exception:
                        value = None

                result[key] = value

            return result


class ProductDatabase:
    """Database operations for Shopping product data."""

    @staticmethod
    def upsert_product(product_id: str, product_title: str, campaign_id: str, campaign_name: str = None, ad_group_id: str = None):
        """Insert or update a product-campaign combination."""
        if not campaign_id:
            raise ValueError("campaign_id is required")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shopping_products (product_id, product_title, campaign_id, campaign_name, ad_group_id, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(product_id, campaign_id) DO UPDATE SET
                    product_title = excluded.product_title,
                    campaign_name = excluded.campaign_name,
                    ad_group_id = excluded.ad_group_id,
                    updated_at = CURRENT_TIMESTAMP
            """, (product_id, product_title, campaign_id, campaign_name, ad_group_id))

    @staticmethod
    def upsert_product_metric(product_id: str, campaign_id: str, date_value: str, metric_name: str, value: float, unit: str):
        """Insert or update a product metric data point for a specific campaign."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO product_metrics (product_id, campaign_id, date, metric_name, value, unit)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id, campaign_id, date, metric_name) DO UPDATE SET
                    value = excluded.value,
                    unit = excluded.unit,
                    created_at = CURRENT_TIMESTAMP
            """, (product_id, campaign_id, date_value, metric_name, value, unit))

    @staticmethod
    def get_all_products(days: int = 30) -> List[dict]:
        """Get all products with their aggregated metrics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    p.product_id,
                    p.product_title,
                    p.campaign_id,
                    p.campaign_name,
                    p.ad_group_id,
                    p.updated_at
                FROM shopping_products p
                ORDER BY p.product_title
            """)
            products = []
            for row in cursor.fetchall():
                product = dict(row)

                # Get aggregated metrics for this product-campaign combination
                product['metrics'] = ProductDatabase.get_aggregated_metrics(product['product_id'], product['campaign_id'], days)
                products.append(product)

            return products

    @staticmethod
    def get_aggregated_metrics(product_id: str, campaign_id: str, days: int = 30) -> List[dict]:
        """Get aggregated metrics for a product in a specific campaign over the last N days."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    metric_name as name,
                    CASE
                        WHEN metric_name = 'ctr' THEN AVG(value)
                        ELSE SUM(value)
                    END as value,
                    unit
                FROM product_metrics
                WHERE product_id = ?
                    AND campaign_id = ?
                    AND date >= date('now', 'localtime', ? || ' days')
                GROUP BY metric_name, unit
                ORDER BY metric_name
            """, (product_id, campaign_id, -days))

            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_product_time_series(product_id: str, campaign_id: str, metric_name: str, days: int = 30) -> dict:
        """Get time series data for a specific metric of a product in a specific campaign."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    date,
                    value,
                    unit
                FROM product_metrics
                WHERE product_id = ?
                    AND campaign_id = ?
                    AND metric_name = ?
                    AND date >= date('now', 'localtime', ? || ' days')
                ORDER BY date ASC
            """, (product_id, campaign_id, metric_name, -days))

            data_points = [dict(row) for row in cursor.fetchall()]

            if not data_points:
                return {
                    "metric_name": metric_name,
                    "data_points": [],
                    "unit": ""
                }

            return {
                "metric_name": metric_name,
                "data_points": data_points,
                "unit": data_points[0]['unit'] if data_points else ""
            }

    @staticmethod
    def bulk_upsert_from_script(products_data: List[dict]) -> dict:
        """
        Bulk insert/update products and metrics from Google Ads Script data.

        Args:
            products_data: List of product dictionaries with structure:
                {
                    "product_id": "...",
                    "product_title": "...",
                    "metrics": [
                        {"date": "2024-01-01", "name": "clicks", "value": 10, "unit": "count"},
                        ...
                    ]
                }

        Returns:
            dict: Summary of operation with counts
        """
        products_processed = 0
        metrics_processed = 0

        with get_db_connection() as conn:
            for product in products_data:
                product_id = product['product_id']
                product_title = product['product_title']
                campaign_id = product.get('campaign_id')
                campaign_name = product.get('campaign_name')
                ad_group_id = product.get('ad_group_id')

                # Upsert product
                ProductDatabase.upsert_product(product_id, product_title, campaign_id, campaign_name, ad_group_id)
                products_processed += 1

                # Upsert metrics
                for metric in product.get('metrics', []):
                    # Convert average_cpc to cpc with proper unit conversion
                    metric_name = metric['name']
                    metric_value = float(metric['value'])
                    metric_unit = metric['unit']

                    if metric_name == 'average_cpc':
                        # Convert from micros (count) to USD
                        metric_name = 'cpc'
                        if metric_unit == 'count':  # Still in micros
                            metric_value = metric_value / 1000000
                            metric_unit = 'USD'

                    ProductDatabase.upsert_product_metric(
                        product_id=product_id,
                        campaign_id=campaign_id,
                        date_value=metric['date'],
                        metric_name=metric_name,
                        value=metric_value,
                        unit=metric_unit
                    )
                    metrics_processed += 1

        return {
            "products_processed": products_processed,
            "metrics_processed": metrics_processed
        }


# Initialize database on module import
init_database()
