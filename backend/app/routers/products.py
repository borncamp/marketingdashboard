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


@router.get("/debug/metrics")
async def debug_metrics(credentials=Depends(verify_credentials)):
    """Debug endpoint to check what metrics are in the database."""
    from app.database import get_db_connection

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get metric summary
            cursor.execute("""
                SELECT metric_name, COUNT(*) as count,
                       MIN(value) as min_val, MAX(value) as max_val,
                       AVG(value) as avg_val, unit
                FROM product_metrics
                GROUP BY metric_name, unit
                ORDER BY metric_name
            """)

            metrics_summary = []
            for row in cursor.fetchall():
                metrics_summary.append({
                    "metric_name": row[0],
                    "count": row[1],
                    "min": row[2],
                    "max": row[3],
                    "avg": row[4],
                    "unit": row[5]
                })

            # Get sample CPC data
            cursor.execute("""
                SELECT product_id, campaign_id, date, value, unit
                FROM product_metrics
                WHERE metric_name = 'cpc'
                ORDER BY date DESC
                LIMIT 20
            """)

            cpc_samples = []
            for row in cursor.fetchall():
                cpc_samples.append({
                    "product_id": row[0],
                    "campaign_id": row[1],
                    "date": row[2],
                    "value": row[3],
                    "unit": row[4]
                })

            return {
                "success": True,
                "metrics_summary": metrics_summary,
                "cpc_samples": cpc_samples
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to debug metrics: {str(e)}"
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
