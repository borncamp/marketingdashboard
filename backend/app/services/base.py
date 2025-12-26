from abc import ABC, abstractmethod
from typing import List
from app.models import Campaign, TimeSeriesData


class AdPlatformAdapter(ABC):
    """
    Abstract base class for ad platform integrations.

    This adapter pattern allows for easy integration of multiple ad platforms
    (Google Ads, Meta Ads, Reddit Ads) with a consistent interface.
    """

    @abstractmethod
    async def get_campaigns(self) -> List[Campaign]:
        """
        Retrieve all campaigns from the ad platform.

        Returns:
            List[Campaign]: List of campaigns with current status and metrics
        """
        pass

    @abstractmethod
    async def get_campaign_metrics(
        self,
        campaign_id: str,
        metric_name: str,
        days: int = 7
    ) -> TimeSeriesData:
        """
        Retrieve time series data for a specific campaign metric.

        Args:
            campaign_id: Unique identifier for the campaign
            metric_name: Name of the metric to retrieve (e.g., 'spend', 'ctr', 'conversions')
            days: Number of days of historical data to retrieve (default: 7)

        Returns:
            TimeSeriesData: Time series data for the requested metric
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Get the name of the ad platform.

        Returns:
            str: Platform identifier (e.g., 'google_ads', 'meta_ads', 'reddit_ads')
        """
        pass
