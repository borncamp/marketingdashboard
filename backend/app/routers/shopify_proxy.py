"""
Shopify proxy endpoints to avoid CORS issues.
Fetches data from Shopify on behalf of the browser.
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
import httpx
from datetime import datetime, timedelta

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
