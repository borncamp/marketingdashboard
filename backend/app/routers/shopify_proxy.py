"""
Shopify proxy endpoints to avoid CORS issues.
Fetches data from Shopify on behalf of the browser.
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from pydantic import BaseModel
import httpx
from datetime import datetime, timedelta
from app.database import SettingsDatabase, ShopifyDatabase, ShippingDatabase
from app.auth import verify_credentials

router = APIRouter(prefix="/api/shopify-proxy", tags=["shopify-proxy"])


class ShopifyCredentials(BaseModel):
    """Shopify credentials from the browser."""
    shop_name: str
    access_token: str
    days: int = 30


@router.post("/fetch-orders")
async def fetch_orders(credentials: ShopifyCredentials):
    """
    Fetch orders from Shopify on behalf of the browser.
    This avoids CORS issues since the backend can call Shopify directly.
    """
    try:
        start_date = datetime.now() - timedelta(days=credentials.days)
        end_date = datetime.now()

        url = f"https://{credentials.shop_name}.myshopify.com/admin/api/2024-01/orders.json"

        params = {
            "status": "any",
            "created_at_min": start_date.isoformat(),
            "created_at_max": end_date.isoformat(),
            "limit": 250,
        }

        headers = {
            "X-Shopify-Access-Token": credentials.access_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Invalid Shopify access token. Please check your credentials."
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Shopify API error: {response.text}"
            )

        data = response.json()
        return {
            "success": True,
            "orders": data.get("orders", [])
        }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request to Shopify timed out. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch orders from Shopify: {str(e)}"
        )


class SyncRequest(BaseModel):
    """Request to sync from backend-stored credentials."""
    days: int = 30


@router.post("/sync-from-backend")
async def sync_from_backend(
    request: SyncRequest,
    username: str = Depends(verify_credentials)
):
    """
    Fetch and sync Shopify data using credentials stored in backend.
    Requires authentication.
    """
    try:
        # Load credentials from database
        shop_name = SettingsDatabase.get_setting("shopify_shop_name")
        access_token = SettingsDatabase.get_setting("shopify_access_token")

        if not shop_name or not access_token:
            raise HTTPException(
                status_code=400,
                detail="Shopify credentials not configured. Please save credentials first."
            )

        # Fetch orders from Shopify
        start_date = datetime.now() - timedelta(days=request.days)
        end_date = datetime.now()

        url = f"https://{shop_name}.myshopify.com/admin/api/2024-01/orders.json"

        params = {
            "status": "any",
            "created_at_min": start_date.isoformat(),
            "created_at_max": end_date.isoformat(),
            "limit": 250,
        }

        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Invalid Shopify access token. Please check your credentials."
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Shopify API error: {response.text}"
            )

        data = response.json()
        orders = data.get("orders", [])

        # Aggregate orders by date for daily metrics (existing functionality)
        daily_metrics = aggregate_orders_by_date(orders)

        # Push aggregated metrics to database
        result = ShopifyDatabase.bulk_upsert_from_orders(daily_metrics)

        # NEW: Also store individual orders and line items for shipping calculations
        orders_data = extract_order_details(orders)
        orders_result = ShippingDatabase.bulk_upsert_orders(orders_data)

        return {
            "success": True,
            "message": f"Successfully synced {len(orders)} orders",
            "records_processed": result['records_processed'],
            "orders_stored": orders_result.get('orders_processed', 0)
        }

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request to Shopify timed out. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync from Shopify: {str(e)}"
        )


def aggregate_orders_by_date(orders: list) -> list:
    """Aggregate Shopify orders by date."""
    daily_metrics = {}

    for order in orders:
        order_date = order['created_at'].split('T')[0]

        if order_date not in daily_metrics:
            daily_metrics[order_date] = {
                "date": order_date,
                "revenue": 0,
                "shipping_revenue": 0,
                "shipping_cost": 0,
                "order_count": 0,
            }

        # Revenue = subtotal - discounts
        subtotal = float(order.get('subtotal_price', 0))
        discounts = float(order.get('total_discounts', 0))
        revenue = subtotal - discounts

        # Shipping Revenue = what customer paid for shipping
        shipping_revenue = sum(
            float(line.get('price', 0))
            for line in order.get('shipping_lines', [])
        )

        # Shipping Cost = shipping sold * 1.05 (assume 5% markup on cost)
        shipping_cost = shipping_revenue * 1.05

        daily_metrics[order_date]['revenue'] += revenue
        daily_metrics[order_date]['shipping_revenue'] += shipping_revenue
        daily_metrics[order_date]['shipping_cost'] += shipping_cost
        daily_metrics[order_date]['order_count'] += 1

    return list(daily_metrics.values())


def extract_order_details(orders: list) -> list:
    """
    Extract individual order details and line items from Shopify orders.

    Args:
        orders: List of Shopify order objects

    Returns:
        List of order data dicts ready for database insertion
    """
    orders_data = []

    for order in orders:
        order_date = order['created_at'].split('T')[0]

        # Calculate revenue
        subtotal = float(order.get('subtotal_price', 0))
        discounts = float(order.get('total_discounts', 0))

        # Calculate shipping charged to customer
        shipping_charged = sum(
            float(line.get('price', 0))
            for line in order.get('shipping_lines', [])
        )

        # Extract line items
        items = []
        for line_item in order.get('line_items', []):
            items.append({
                'product_id': str(line_item.get('product_id', '')),
                'variant_id': str(line_item.get('variant_id', '')),
                'product_title': line_item.get('title', ''),
                'variant_title': line_item.get('variant_title'),
                'quantity': int(line_item.get('quantity', 1)),
                'price': float(line_item.get('price', 0)),
                'total': float(line_item.get('price', 0)) * int(line_item.get('quantity', 1))
            })

        # Build order data
        order_data = {
            'id': str(order['id']),
            'order_number': int(order.get('order_number', 0)),
            'order_date': order_date,
            'customer_email': order.get('email'),
            'subtotal': subtotal,
            'total_price': float(order.get('total_price', 0)),
            'shipping_charged': shipping_charged,
            'currency': order.get('currency', 'USD'),
            'financial_status': order.get('financial_status'),
            'fulfillment_status': order.get('fulfillment_status'),
            'items': items
        }

        orders_data.append(order_data)

    return orders_data
