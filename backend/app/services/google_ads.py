from datetime import datetime, timedelta
from typing import List, Optional
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from app.config import settings as env_settings
from app.models import Campaign, CampaignStatus, Metric, TimeSeriesData, DataPoint
from app.services.base import AdPlatformAdapter


class GoogleAdsAdapter(AdPlatformAdapter):
    """Google Ads API adapter implementation."""

    def __init__(self, from_saved_settings: bool = True):
        """
        Initialize Google Ads client with credentials.

        Args:
            from_saved_settings: Try to load from saved settings first, fallback to env

        Raises:
            ValueError: If no credentials are available
        """
        credentials = None
        customer_id = None

        # Try to load from saved settings first if requested
        if from_saved_settings:
            try:
                from app.services.settings_manager import settings_manager
                saved_settings = settings_manager.load_google_ads_settings()

                if saved_settings:
                    credentials = {
                        "developer_token": saved_settings.developer_token,
                        "client_id": saved_settings.client_id,
                        "client_secret": saved_settings.client_secret,
                        "refresh_token": saved_settings.refresh_token,
                        "use_proto_plus": True,
                    }

                    if saved_settings.login_customer_id:
                        credentials["login_customer_id"] = saved_settings.login_customer_id

                    customer_id = saved_settings.customer_id
            except Exception:
                pass  # Fall through to env settings

        # Fall back to environment settings
        if not credentials:
            try:
                credentials = {
                    "developer_token": env_settings.google_ads_developer_token,
                    "client_id": env_settings.google_ads_client_id,
                    "client_secret": env_settings.google_ads_client_secret,
                    "refresh_token": env_settings.google_ads_refresh_token,
                    "use_proto_plus": True,
                }

                if env_settings.google_ads_login_customer_id:
                    credentials["login_customer_id"] = env_settings.google_ads_login_customer_id

                customer_id = env_settings.google_ads_customer_id
            except Exception as e:
                raise ValueError(
                    "No Google Ads credentials found. Please configure via the onboarding flow or .env file"
                ) from e

        self.client = GoogleAdsClient.load_from_dict(credentials)
        self.customer_id = customer_id

    def get_platform_name(self) -> str:
        """Return the platform identifier."""
        return "google_ads"

    async def get_campaigns(self) -> List[Campaign]:
        """
        Retrieve all campaigns with current metrics.

        Returns:
            List[Campaign]: List of campaigns with status and current metrics
        """
        ga_service = self.client.get_service("GoogleAdsService")

        # Calculate date range for last 7 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)  # 6 days ago + today = 7 days

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                segments.date,
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions,
                metrics.conversions
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            AND segments.date BETWEEN '{start_date}' AND '{end_date}'
        """

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)

            campaigns_dict = {}
            row_count = 0
            for row in response:
                row_count += 1
                campaign_id = str(row.campaign.id)

                if campaign_id not in campaigns_dict:
                    campaigns_dict[campaign_id] = {
                        "id": campaign_id,
                        "name": row.campaign.name,
                        "status": self._map_campaign_status(row.campaign.status.name),
                        "cost_micros": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "conversions": 0,
                    }

                campaigns_dict[campaign_id]["cost_micros"] += row.metrics.cost_micros
                campaigns_dict[campaign_id]["clicks"] += row.metrics.clicks
                campaigns_dict[campaign_id]["impressions"] += row.metrics.impressions
                campaigns_dict[campaign_id]["conversions"] += row.metrics.conversions

            print(f"DEBUG: Processed {row_count} rows for {len(campaigns_dict)} campaigns")

            campaigns = []
            for campaign_data in campaigns_dict.values():
                spend = campaign_data["cost_micros"] / 1_000_000
                impressions = campaign_data["impressions"]
                clicks = campaign_data["clicks"]
                ctr = (clicks / impressions * 100) if impressions > 0 else 0

                metrics = [
                    Metric(name="spend", value=spend, unit="USD"),
                    Metric(name="ctr", value=round(ctr, 2), unit="%"),
                    Metric(name="conversions", value=campaign_data["conversions"], unit="count"),
                ]

                campaigns.append(
                    Campaign(
                        id=campaign_data["id"],
                        name=campaign_data["name"],
                        status=campaign_data["status"],
                        platform=self.get_platform_name(),
                        metrics=metrics,
                    )
                )

            return campaigns

        except GoogleAdsException as ex:
            print(f"Google Ads API error: {ex}")
            raise

    async def get_campaign_metrics(
        self,
        campaign_id: str,
        metric_name: str,
        days: int = 7
    ) -> TimeSeriesData:
        """
        Retrieve time series data for a specific campaign metric.

        Args:
            campaign_id: Campaign ID
            metric_name: Metric name ('spend', 'ctr', 'conversions')
            days: Number of days of historical data

        Returns:
            TimeSeriesData: Time series data for the metric
        """
        ga_service = self.client.get_service("GoogleAdsService")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                segments.date,
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions,
                metrics.conversions
            FROM campaign
            WHERE campaign.id = {campaign_id}
            AND segments.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY segments.date ASC
        """

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)

            campaign_name = ""
            data_points = []

            for row in response:
                if not campaign_name:
                    campaign_name = row.campaign.name

                value = self._extract_metric_value(row, metric_name)
                data_points.append(
                    DataPoint(
                        date=datetime.strptime(row.segments.date, "%Y-%m-%d").date(),
                        value=value,
                    )
                )

            unit = self._get_metric_unit(metric_name)

            return TimeSeriesData(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                metric_name=metric_name,
                unit=unit,
                data_points=data_points,
            )

        except GoogleAdsException as ex:
            print(f"Google Ads API error: {ex}")
            raise

    def _extract_metric_value(self, row, metric_name: str) -> float:
        """Extract metric value from Google Ads API row."""
        if metric_name == "spend":
            return row.metrics.cost_micros / 1_000_000
        elif metric_name == "ctr":
            impressions = row.metrics.impressions
            clicks = row.metrics.clicks
            return round((clicks / impressions * 100), 2) if impressions > 0 else 0
        elif metric_name == "conversions":
            return row.metrics.conversions
        else:
            return 0

    def _get_metric_unit(self, metric_name: str) -> str:
        """Get the unit for a given metric."""
        units = {
            "spend": "USD",
            "ctr": "%",
            "conversions": "count",
        }
        return units.get(metric_name, "")

    def _map_campaign_status(self, status_name: str) -> CampaignStatus:
        """Map Google Ads campaign status to our enum."""
        status_mapping = {
            "ENABLED": CampaignStatus.ENABLED,
            "PAUSED": CampaignStatus.PAUSED,
            "REMOVED": CampaignStatus.REMOVED,
        }
        return status_mapping.get(status_name, CampaignStatus.UNKNOWN)
