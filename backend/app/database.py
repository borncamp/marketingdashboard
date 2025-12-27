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

        # Shopping products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_products (
                product_id TEXT PRIMARY KEY,
                product_title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Product metrics table (time series data for Shopping products)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                date DATE NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES shopping_products(product_id) ON DELETE CASCADE,
                UNIQUE(product_id, date, metric_name)
            )
        """)

        # Create indexes for product metrics performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_metrics_product_date
            ON product_metrics(product_id, date DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_metrics_metric_name
            ON product_metrics(metric_name)
        """)

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
                    AND date >= date('now', '-7 days')
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

            # Get metric data points
            cursor.execute("""
                SELECT
                    date,
                    value,
                    unit
                FROM campaign_metrics
                WHERE campaign_id = ? AND metric_name = ?
                    AND date >= date('now', ?)
                ORDER BY date ASC
            """, (campaign_id, metric_name, f'-{days} days'))

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
                        AND date >= date('now', ?)
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

                # Upsert metrics
                for metric in campaign.get('metrics', []):
                    CampaignDatabase.upsert_metric(
                        campaign_id=campaign['id'],
                        date_value=metric['date'],
                        metric_name=metric['name'],
                        value=float(metric['value']),
                        unit=metric['unit']
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
            cursor.execute("""
                SELECT
                    SUM(revenue) as total_revenue,
                    SUM(shipping_revenue) as total_shipping_revenue,
                    SUM(shipping_cost) as total_shipping_cost,
                    SUM(order_count) as total_orders
                FROM shopify_daily_metrics
                WHERE date >= date('now', ?)
            """, (f'-{days} days',))

            row = cursor.fetchone()
            if not row:
                return {
                    "total_revenue": 0,
                    "total_shipping_revenue": 0,
                    "total_shipping_cost": 0,
                    "total_orders": 0
                }

            return dict(row)

    @staticmethod
    def get_time_series(metric_name: str, days: int = 30) -> List[dict]:
        """Get time series data for a specific Shopify metric."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Map metric name to column
            metric_column_map = {
                'revenue': 'revenue',
                'shipping_revenue': 'shipping_revenue',
                'shipping_cost': 'shipping_cost',
                'orders': 'order_count'
            }

            column = metric_column_map.get(metric_name, 'revenue')

            cursor.execute(f"""
                SELECT
                    date,
                    {column} as value
                FROM shopify_daily_metrics
                WHERE date >= date('now', ?)
                ORDER BY date ASC
            """, (f'-{days} days',))

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


class SettingsDatabase:
    """Database operations for application settings."""

    @staticmethod
    def set_setting(key: str, value: str, encrypted: bool = False):
        """Set or update a setting value."""
        from cryptography.fernet import Fernet
        from app.config import settings as app_settings

        stored_value = value
        if encrypted and app_settings.encryption_key:
            # Encrypt the value before storing
            cipher = Fernet(app_settings.encryption_key.encode())
            stored_value = cipher.encrypt(value.encode()).decode()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, encrypted, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    encrypted = excluded.encrypted,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, stored_value, encrypted))

    @staticmethod
    def get_setting(key: str, default: str = None) -> Optional[str]:
        """Get a setting value."""
        from cryptography.fernet import Fernet
        from app.config import settings as app_settings

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value, encrypted
                FROM settings
                WHERE key = ?
            """, (key,))

            row = cursor.fetchone()
            if not row:
                return default

            value = row['value']
            encrypted = row['encrypted']

            if encrypted and app_settings.encryption_key:
                # Decrypt the value
                try:
                    cipher = Fernet(app_settings.encryption_key.encode())
                    value = cipher.decrypt(value.encode()).decode()
                except Exception as e:
                    print(f"Failed to decrypt setting {key}: {e}")
                    return default

            return value

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
    def upsert_product(product_id: str, product_title: str):
        """Insert or update a product."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shopping_products (product_id, product_title, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(product_id) DO UPDATE SET
                    product_title = excluded.product_title,
                    updated_at = CURRENT_TIMESTAMP
            """, (product_id, product_title))

    @staticmethod
    def upsert_product_metric(product_id: str, date_value: str, metric_name: str, value: float, unit: str):
        """Insert or update a product metric data point."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO product_metrics (product_id, date, metric_name, value, unit)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(product_id, date, metric_name) DO UPDATE SET
                    value = excluded.value,
                    unit = excluded.unit,
                    created_at = CURRENT_TIMESTAMP
            """, (product_id, date_value, metric_name, value, unit))

    @staticmethod
    def get_all_products(days: int = 30) -> List[dict]:
        """Get all products with their aggregated metrics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    p.product_id,
                    p.product_title,
                    p.updated_at
                FROM shopping_products p
                ORDER BY p.product_title
            """)
            products = []
            for row in cursor.fetchall():
                product = dict(row)

                # Get aggregated metrics for this product
                product['metrics'] = ProductDatabase.get_aggregated_metrics(product['product_id'], days)
                products.append(product)

            return products

    @staticmethod
    def get_aggregated_metrics(product_id: str, days: int = 30) -> List[dict]:
        """Get aggregated metrics for a product over the last N days."""
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
                    AND date >= date('now', ? || ' days')
                GROUP BY metric_name, unit
                ORDER BY metric_name
            """, (product_id, -days))

            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_product_time_series(product_id: str, metric_name: str, days: int = 30) -> dict:
        """Get time series data for a specific metric of a product."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    date,
                    value,
                    unit
                FROM product_metrics
                WHERE product_id = ?
                    AND metric_name = ?
                    AND date >= date('now', ? || ' days')
                ORDER BY date ASC
            """, (product_id, metric_name, -days))

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

                # Upsert product
                ProductDatabase.upsert_product(product_id, product_title)
                products_processed += 1

                # Upsert metrics
                for metric in product.get('metrics', []):
                    ProductDatabase.upsert_product_metric(
                        product_id=product_id,
                        date_value=metric['date'],
                        metric_name=metric['name'],
                        value=metric['value'],
                        unit=metric['unit']
                    )
                    metrics_processed += 1

        return {
            "products_processed": products_processed,
            "metrics_processed": metrics_processed
        }


# Initialize database on module import
init_database()
