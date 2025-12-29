"""
Script configuration endpoint - provides runtime config for Google Ads scripts.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/script-config", tags=["script-config"])


@router.get("")
async def get_script_config():
    """
    Get configuration for Google Ads Script.
    
    This endpoint is called by the Google Ads script at runtime to get
    the latest data collection settings without needing to update the script.
    
    Returns:
        Configuration object with script settings
    """
    return {
        "version": "2.2",
        "last_updated": "2025-12-28",

        # Data collection settings
        "days_of_history": 30,  # For campaign metrics
        "product_days_of_history": 7,  # For product data - shorter window to show only active products

        # Campaign filters
        "campaign_filters": {
            "status": "ENABLED",  # Only pull from ENABLED campaigns
            "require_impressions": True  # Only include products with impressions > 0
        },

        # Product fields to collect
        "product_fields": [
            "segments.product_item_id",
            "segments.product_title",
            "campaign.id",
            "campaign.name",
            "ad_group.id",  # REQUIRED for edit CPC links
            "segments.date"
        ],

        # Metrics to collect
        "metrics": [
            "cost_micros",
            "clicks",
            "impressions",
            "ctr",
            "average_cpc",
            "conversions",
            "conversions_value"
        ],

        # Metric metadata for dynamic parsing
        "metric_metadata": {
            "average_cpc": {
                "conversion": "micros_to_usd",  # Divide by 1,000,000
                "display_name": "cpc",
                "unit": "USD"
            }
        },

        # Query settings
        "query_settings": {
            "include_today": True,  # Whether to fetch today's data separately
            "order_by": "segments.product_item_id, segments.date ASC"
        },

        # API endpoints
        "endpoints": {
            "push_campaigns": "/api/sync/push",
            "push_products": "/api/sync/push-products"
        }
    }
