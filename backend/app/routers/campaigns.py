from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models.campaign import Campaign, TimeSeriesData, Metric, DataPoint, CampaignStatus
from app.database import CampaignDatabase

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("")
async def get_campaigns():
    """
    Get all campaigns from local database.

    Data is populated by Google Ads Script via /api/sync/push endpoint.

    Returns:
        List of all campaigns with their current metrics
    """
    try:
        campaigns_data = CampaignDatabase.get_all_campaigns()

        # Convert to Campaign model format
        campaigns = []
        for campaign_data in campaigns_data:
            # Convert metrics to Metric model
            metrics = [
                Metric(
                    name=m['name'],
                    value=float(m['value']),
                    unit=m.get('unit', '')
                )
                for m in campaign_data.get('metrics', [])
            ]

            campaign = Campaign(
                id=campaign_data['id'],
                name=campaign_data['name'],
                status=CampaignStatus(campaign_data['status']),
                platform=campaign_data.get('platform', 'google_ads'),
                metrics=metrics
            )
            campaigns.append(campaign)

        return campaigns

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch campaigns: {str(e)}")


@router.get("/all/metrics/{metric_name}")
async def get_all_campaigns_metrics(
    metric_name: str,
    days: int = Query(default=30, ge=1, le=90, description="Number of days of historical data")
):
    """
    Get time series data for all campaigns for a specific metric.

    Args:
        metric_name: Metric name (spend, clicks, ctr, conversions, impressions)
        days: Number of days of historical data (1-90)

    Returns:
        List of time series data for all campaigns
    """
    try:
        time_series_list = CampaignDatabase.get_all_campaigns_time_series(metric_name, days)

        # Convert to TimeSeriesData model format
        results = []
        for time_series in time_series_list:
            data_points = [
                DataPoint(
                    date=dp['date'],
                    value=float(dp['value'])
                )
                for dp in time_series.get('data_points', [])
            ]

            result = TimeSeriesData(
                campaign_id=time_series['campaign_id'],
                campaign_name=time_series['campaign_name'],
                metric_name=time_series['metric_name'],
                unit=time_series.get('unit', ''),
                data_points=data_points
            )
            results.append(result)

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch all campaigns metrics: {str(e)}"
        )


@router.get("/{campaign_id}/metrics/{metric_name}")
async def get_campaign_metrics(
    campaign_id: str,
    metric_name: str,
    days: int = Query(default=30, ge=1, le=90, description="Number of days of historical data")
):
    """
    Get time series data for a specific campaign metric from local database.

    Args:
        campaign_id: Campaign ID
        metric_name: Metric name (spend, clicks, ctr, conversions, impressions)
        days: Number of days of historical data (1-90)

    Returns:
        Time series data for the requested metric
    """
    try:
        time_series = CampaignDatabase.get_campaign_time_series(campaign_id, metric_name, days)

        if not time_series:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign {campaign_id} not found"
            )

        # Convert to TimeSeriesData model format
        data_points = [
            DataPoint(
                date=dp['date'],
                value=float(dp['value'])
            )
            for dp in time_series.get('data_points', [])
        ]

        result = TimeSeriesData(
            campaign_id=time_series['campaign_id'],
            campaign_name=time_series['campaign_name'],
            metric_name=time_series['metric_name'],
            unit=time_series.get('unit', ''),
            data_points=data_points
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch campaign metrics: {str(e)}"
        )
