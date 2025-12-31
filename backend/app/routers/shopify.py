"""
Shopify API endpoints for receiving revenue and order data.
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import ShopifyDatabase, SettingsDatabase, ShippingDatabase
from app.config import settings
from app.auth import verify_credentials
from app.routers.shipping import calculate_order_shipping_cost
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


# ============================================================================
# Order Management Endpoints
# ============================================================================

@router.get("/orders")
async def get_orders(
    days: int = 30,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    username: str = Depends(verify_credentials)
):
    """
    Get list of Shopify orders with optional filters.

    Args:
        days: Number of days to look back (default: 30)
        status: Filter by financial status (optional)
        limit: Maximum number of orders to return (default: 100)
        offset: Number of orders to skip (default: 0)

    Returns:
        List of orders with metadata
    """
    try:
        orders = ShippingDatabase.get_orders(
            days=days,
            status=status,
            limit=limit,
            offset=offset
        )

        return {
            "orders": orders,
            "total": len(orders),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch orders: {str(e)}"
        )


@router.get("/orders/{order_id}")
async def get_order_detail(
    order_id: str,
    username: str = Depends(verify_credentials)
):
    """
    Get detailed information for a single order including line items.

    Args:
        order_id: Shopify order ID

    Returns:
        Order details with line items
    """
    try:
        order = ShippingDatabase.get_order_detail(order_id)

        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Order {order_id} not found"
            )

        return order

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch order detail: {str(e)}"
        )


@router.get("/daily-metrics")
async def get_daily_metrics(days: int = 30):
    """
    Get daily time series metrics for Shopify data.

    Args:
        days: Number of days to fetch (default: 30)

    Returns:
        Daily metrics with date, revenue, orders, shipping_revenue
    """
    try:
        # Get daily aggregated data
        revenue_data = ShopifyDatabase.get_time_series('revenue', days)
        orders_data = ShopifyDatabase.get_time_series('orders', days)
        shipping_data = ShopifyDatabase.get_time_series('shipping_revenue', days)

        # Combine into single response
        daily_metrics = {}

        for point in revenue_data:
            date = point['date']
            if date not in daily_metrics:
                daily_metrics[date] = {'date': date, 'revenue': 0, 'orders': 0, 'shipping_revenue': 0}
            daily_metrics[date]['revenue'] = point['value']

        for point in orders_data:
            date = point['date']
            if date not in daily_metrics:
                daily_metrics[date] = {'date': date, 'revenue': 0, 'orders': 0, 'shipping_revenue': 0}
            daily_metrics[date]['orders'] = point['value']

        for point in shipping_data:
            date = point['date']
            if date not in daily_metrics:
                daily_metrics[date] = {'date': date, 'revenue': 0, 'orders': 0, 'shipping_revenue': 0}
            daily_metrics[date]['shipping_revenue'] = point['value']

        # Sort by date
        metrics_list = sorted(daily_metrics.values(), key=lambda x: x['date'])

        return {
            "metrics": metrics_list
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch daily metrics: {str(e)}"
        )


# ============================================================================
# Shipping Cost Calculation Endpoints
# ============================================================================

class CalculateShippingRequest(BaseModel):
    """Request to calculate shipping for specific orders."""
    order_ids: List[str] = Field(..., description="List of order IDs to calculate")


@router.post("/orders/calculate-shipping")
async def calculate_shipping_costs(
    request: CalculateShippingRequest,
    username: str = Depends(verify_credentials)
):
    """
    Calculate shipping costs for multiple orders using active shipping rules.

    Args:
        request: List of order IDs

    Returns:
        Results for each order
    """
    try:
        # Get active shipping profiles
        profiles = ShippingDatabase.get_shipping_profiles(active_only=True)

        if not profiles:
            raise HTTPException(
                status_code=400,
                detail="No active shipping profiles found. Please create shipping rules first."
            )

        results = []

        for order_id in request.order_ids:
            # Get order with items
            order = ShippingDatabase.get_order_detail(order_id)

            if not order:
                results.append({
                    "order_id": order_id,
                    "success": False,
                    "error": "Order not found"
                })
                continue

            # Calculate shipping cost
            calculation = calculate_order_shipping_cost(
                order=order,
                items=order['items'],
                profiles=profiles
            )

            # Save calculation to database
            ShippingDatabase.save_shipping_calculation(
                order_id=order_id,
                profile_id=calculation['breakdown'][0]['profile_id'] if calculation['breakdown'] else None,
                calculated_cost=calculation['total_cost'],
                details=calculation
            )

            results.append({
                "order_id": order_id,
                "success": True,
                "calculated_cost": calculation['total_cost'],
                "breakdown": calculation['breakdown']
            })

        return {
            "success": True,
            "results": results,
            "orders_processed": len(results)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate shipping costs: {str(e)}"
        )


@router.post("/orders/{order_id}/calculate-shipping")
async def calculate_single_order_shipping(
    order_id: str,
    username: str = Depends(verify_credentials)
):
    """
    Calculate shipping cost for a single order.

    Args:
        order_id: Shopify order ID

    Returns:
        Calculation result with breakdown
    """
    try:
        # Get active shipping profiles
        profiles = ShippingDatabase.get_shipping_profiles(active_only=True)

        if not profiles:
            raise HTTPException(
                status_code=400,
                detail="No active shipping profiles found. Please create shipping rules first."
            )

        # Get order with items
        order = ShippingDatabase.get_order_detail(order_id)

        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Order {order_id} not found"
            )

        # Calculate shipping cost
        calculation = calculate_order_shipping_cost(
            order=order,
            items=order['items'],
            profiles=profiles
        )

        # Save calculation to database
        ShippingDatabase.save_shipping_calculation(
            order_id=order_id,
            profile_id=calculation['breakdown'][0]['profile_id'] if calculation['breakdown'] else None,
            calculated_cost=calculation['total_cost'],
            details=calculation
        )

        return {
            "success": True,
            "order_id": order_id,
            "order_number": order['order_number'],
            "calculated_cost": calculation['total_cost'],
            "shipping_charged": order['shipping_charged'],
            "difference": order['shipping_charged'] - calculation['total_cost'],
            "breakdown": calculation['breakdown'],
            "matched_items": calculation['matched_items']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate shipping cost: {str(e)}"
        )
