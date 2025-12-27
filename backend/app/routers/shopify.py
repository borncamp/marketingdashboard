"""
Shopify API endpoints for receiving revenue and order data.
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import ShopifyDatabase, SettingsDatabase
from app.config import settings
from app.auth import verify_credentials
from datetime import date as DateType

router = APIRouter(prefix="/api/shopify", tags=["shopify"])


class DailyMetrics(BaseModel):
    """Daily aggregated metrics from Shopify."""
    date: DateType = Field(..., description="Date of the metrics")
    revenue: float = Field(default=0, description="Total revenue (excluding shipping)")
    shipping_revenue: float = Field(default=0, description="Shipping charges collected")
    shipping_cost: float = Field(default=0, description="Actual shipping costs paid")
    order_count: int = Field(default=0, description="Number of orders")


class ShopifySyncRequest(BaseModel):
    """Request to sync Shopify data."""
    daily_metrics: List[DailyMetrics] = Field(..., description="List of daily aggregated metrics")
    source: str = Field(default="shopify_script", description="Data source identifier")


@router.post("/push")
async def push_shopify_data(
    sync_data: ShopifySyncRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Optional API key for authentication")
):
    """
    Receive Shopify order data pushed from external scripts.

    This endpoint accepts daily aggregated revenue and shipping data from Shopify
    and stores it in the local database for analytics.

    Args:
        sync_data: Daily metrics data to sync
        x_api_key: Optional API key for basic authentication

    Returns:
        Success status and counts of processed records
    """
    # Validate API key if configured
    if settings.sync_api_key:
        if not x_api_key or x_api_key != settings.sync_api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key"
            )

    try:
        # Convert Pydantic models to dict for database
        data_list = [
            {
                "date": str(metric.date),
                "revenue": metric.revenue,
                "shipping_revenue": metric.shipping_revenue,
                "shipping_cost": metric.shipping_cost,
                "order_count": metric.order_count
            }
            for metric in sync_data.daily_metrics
        ]

        # Bulk upsert to database
        result = ShopifyDatabase.bulk_upsert_from_orders(data_list)

        return {
            "success": True,
            "message": "Shopify data synced successfully",
            "records_processed": result['records_processed'],
            "source": sync_data.source
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Shopify data: {str(e)}"
        )


@router.get("/metrics")
async def get_shopify_metrics(days: int = 7):
    """
    Get aggregated Shopify metrics for the last N days.

    Args:
        days: Number of days to aggregate (default: 7)

    Returns:
        Aggregated revenue, shipping, and order metrics
    """
    try:
        summary = ShopifyDatabase.get_metrics_summary(days)

        return {
            "period_days": days,
            "total_revenue": summary['total_revenue'],
            "total_shipping_revenue": summary['total_shipping_revenue'],
            "total_shipping_cost": summary['total_shipping_cost'],
            "total_orders": summary['total_orders'],
            "net_shipping_profit": summary['total_shipping_revenue'] - summary['total_shipping_cost']
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Shopify metrics: {str(e)}"
        )


@router.get("/metrics/{metric_name}")
async def get_shopify_time_series(metric_name: str, days: int = 30):
    """
    Get time series data for a specific Shopify metric.

    Args:
        metric_name: Metric name (revenue, shipping_revenue, shipping_cost, orders)
        days: Number of days of historical data (default: 30)

    Returns:
        Time series data for the requested metric
    """
    valid_metrics = ['revenue', 'shipping_revenue', 'shipping_cost', 'orders']

    if metric_name not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric name. Must be one of: {', '.join(valid_metrics)}"
        )

    try:
        data_points = ShopifyDatabase.get_time_series(metric_name, days)

        return {
            "metric_name": metric_name,
            "data_points": data_points
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Shopify time series: {str(e)}"
        )


class ShopifyCredentials(BaseModel):
    """Shopify API credentials."""
    shop_name: str = Field(..., description="Shopify shop name (without .myshopify.com)")
    access_token: str = Field(..., description="Shopify Admin API access token")


@router.post("/credentials")
async def save_shopify_credentials(
    credentials: ShopifyCredentials,
    username: str = Depends(verify_credentials)
):
    """
    Save Shopify credentials securely.
    Requires authentication.
    """
    try:
        # Store encrypted credentials in database
        SettingsDatabase.set_setting("shopify_shop_name", credentials.shop_name, encrypted=False)
        SettingsDatabase.set_setting("shopify_access_token", credentials.access_token, encrypted=True)

        return {
            "success": True,
            "message": "Shopify credentials saved successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save Shopify credentials: {str(e)}"
        )


@router.get("/credentials")
async def get_shopify_credentials(
    username: str = Depends(verify_credentials)
):
    """
    Get saved Shopify credentials (token will be masked).
    Requires authentication.
    """
    try:
        shop_name = SettingsDatabase.get_setting("shopify_shop_name")
        access_token = SettingsDatabase.get_setting("shopify_access_token")

        if not shop_name or not access_token:
            return {
                "configured": False,
                "shop_name": None
            }

        return {
            "configured": True,
            "shop_name": shop_name,
            "access_token_masked": "shpat_" + ("•" * 20)  # Mask the token
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Shopify credentials: {str(e)}"
        )


@router.delete("/credentials")
async def delete_shopify_credentials(
    username: str = Depends(verify_credentials)
):
    """
    Delete saved Shopify credentials.
    Requires authentication.
    """
    try:
        SettingsDatabase.delete_setting("shopify_shop_name")
        SettingsDatabase.delete_setting("shopify_access_token")

        return {
            "success": True,
            "message": "Shopify credentials deleted successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Shopify credentials: {str(e)}"
        )
