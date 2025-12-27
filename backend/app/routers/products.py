"""
Products API endpoints for Shopping product performance data.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.database import ProductDatabase
from app.auth import verify_credentials

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/")
async def get_all_products(
    days: int = 30,
    credentials=Depends(verify_credentials)
):
    """
    Get all Shopping products with aggregated metrics.

    Args:
        days: Number of days to aggregate metrics over (default: 30)

    Returns:
        List of products with their metrics
    """
    try:
        products = ProductDatabase.get_all_products(days=days)

        return {
            "success": True,
            "products": products,
            "total_count": len(products)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch products: {str(e)}"
        )


@router.get("/{product_id}/{campaign_id}/metrics/{metric_name}")
async def get_product_metric_time_series(
    product_id: str,
    campaign_id: str,
    metric_name: str,
    days: int = 30,
    credentials=Depends(verify_credentials)
):
    """
    Get time series data for a specific metric of a product in a campaign.

    Args:
        product_id: The product ID
        campaign_id: The campaign ID
        metric_name: Name of the metric (e.g., 'clicks', 'spend', 'impressions')
        days: Number of days of historical data (default: 30)

    Returns:
        Time series data for the specified metric
    """
    try:
        time_series = ProductDatabase.get_product_time_series(
            product_id=product_id,
            campaign_id=campaign_id,
            metric_name=metric_name,
            days=days
        )

        return {
            "success": True,
            "product_id": product_id,
            "campaign_id": campaign_id,
            "time_series": time_series
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch metric time series: {str(e)}"
        )
