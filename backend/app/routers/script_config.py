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
        "version": "2.1",
        "last_updated": "2025-12-27",

        # Data collection settings
        "days_of_history": 30,  # For campaign metrics
        "product_days_of_history": 7,  # For product data - shorter window to show only active products

        # Campaign filters
        "campaign_filters": {
            "status": "ENABLED",  # Only pull from ENABLED campaigns
            "require_impressions": True  # Only include products with impressions > 0
        },

        # Metrics to collect
        "metrics": [
            "cost_micros",
            "clicks",
            "impressions",
            "ctr",
            "conversions",
            "conversions_value"
        ],

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
