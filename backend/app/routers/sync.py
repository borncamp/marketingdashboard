"""
Sync API endpoints for receiving data from Google Ads Scripts.
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import CampaignDatabase, ProductDatabase
from app.config import settings
from datetime import date as DateType

router = APIRouter(prefix="/api/sync", tags=["sync"])


class MetricData(BaseModel):
    """Single metric data point."""
    date: DateType = Field(..., description="Date of the metric")
    name: str = Field(..., description="Metric name (e.g., 'spend', 'clicks', 'ctr')")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Unit (e.g., 'USD', 'count', '%')")


class CampaignData(BaseModel):
    """Campaign data with metrics."""
    id: str = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    status: str = Field(..., description="Campaign status (ENABLED, PAUSED, REMOVED)")
    platform: str = Field(default="google_ads", description="Platform identifier")
    metrics: List[MetricData] = Field(default_factory=list, description="List of metric data points")


class SyncRequest(BaseModel):
    """Request to sync campaign data."""
    campaigns: List[CampaignData] = Field(..., description="List of campaigns with metrics")
    source: str = Field(default="google_ads_script", description="Data source identifier")


@router.post("/push")
async def push_campaign_data(
    sync_data: SyncRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Optional API key for authentication")
):
    """
    Receive campaign data pushed from Google Ads Script.

    This endpoint accepts campaign data from external sources (like Google Ads Scripts)
    and stores it in the local database.

    Args:
        sync_data: Campaign data to sync
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
        data_dict = {
            "campaigns": [
                {
                    "id": campaign.id,
                    "name": campaign.name,
                    "status": campaign.status,
                    "platform": campaign.platform,
                    "metrics": [
                        {
                            "date": str(metric.date),
                            "name": metric.name,
                            "value": metric.value,
                            "unit": metric.unit
                        }
                        for metric in campaign.metrics
                    ]
                }
                for campaign in sync_data.campaigns
            ]
        }

        # Bulk upsert to database
        result = CampaignDatabase.bulk_upsert_from_script(data_dict)

        return {
            "success": True,
            "message": "Data synced successfully",
            "campaigns_processed": result['campaigns_processed'],
            "metrics_processed": result['metrics_processed'],
            "source": sync_data.source
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data: {str(e)}"
        )


@router.get("/status")
async def get_sync_status():
    """
    Get the status of the last data sync.

    Returns:
        Information about the last successful sync
    """
    last_sync = CampaignDatabase.get_last_sync()

    if not last_sync:
        return {
            "has_data": False,
            "message": "No sync history found. Waiting for first data push."
        }

    return {
        "has_data": True,
        "last_sync_at": last_sync['synced_at'],
        "campaigns_count": last_sync['campaigns_count'],
        "metrics_count": last_sync['metrics_count'],
        "status": last_sync['status']
    }


class ProductData(BaseModel):
    """Shopping product data with metrics."""
    product_id: str = Field(..., description="Product ID from Google Merchant Center")
    product_title: str = Field(..., description="Product title/name")
    campaign_id: Optional[str] = Field(None, description="Campaign ID this product belongs to")
    campaign_name: Optional[str] = Field(None, description="Campaign name this product belongs to")
    metrics: List[MetricData] = Field(default_factory=list, description="List of metric data points")


class ProductSyncRequest(BaseModel):
    """Request to sync product data."""
    products: List[ProductData] = Field(..., description="List of products with metrics")
    source: str = Field(default="google_ads_script", description="Data source identifier")


@router.post("/push-products")
async def push_product_data(
    sync_data: ProductSyncRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Optional API key for authentication")
):
    """
    Receive Shopping product data pushed from Google Ads Script.

    This endpoint accepts product performance data from Google Shopping campaigns
    and stores it in the local database.

    Args:
        sync_data: Product data to sync
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
        data_dict = {
            "products": [
                {
                    "product_id": product.product_id,
                    "product_title": product.product_title,
                    "campaign_id": product.campaign_id,
                    "campaign_name": product.campaign_name,
                    "metrics": [
                        {
                            "date": str(metric.date),
                            "name": metric.name,
                            "value": metric.value,
                            "unit": metric.unit
                        }
                        for metric in product.metrics
                    ]
                }
                for product in sync_data.products
            ]
        }

        # Bulk upsert to database
        result = ProductDatabase.bulk_upsert_from_script(data_dict["products"])

        return {
            "success": True,
            "message": "Product data synced successfully",
            "products_processed": result['products_processed'],
            "metrics_processed": result['metrics_processed'],
            "source": sync_data.source
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync product data: {str(e)}"
        )
