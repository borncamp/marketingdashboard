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


# Initialize database on module import
init_database()
