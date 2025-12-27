"""
Meta Ads API endpoints for managing credentials and fetching campaign data.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.database import SettingsDatabase
from app.auth import verify_credentials
from typing import Optional, List, Dict, Any
import requests
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/meta", tags=["meta"])


class MetaCredentials(BaseModel):
    """Meta API credentials."""
    access_token: str
    ad_account_id: str


class MetaCredentialsResponse(BaseModel):
    """Response for credentials status."""
    configured: bool
    ad_account_id: Optional[str] = None
    account_name: Optional[str] = None
    currency: Optional[str] = None


@router.post("/credentials")
async def save_meta_credentials(
    credentials: MetaCredentials,
    username: str = Depends(verify_credentials)
):
    """
    Save Meta API credentials securely in the database.

    Args:
        credentials: Meta access token and ad account ID
        username: Authenticated user (from HTTP Basic Auth)

    Returns:
        Success status
    """
    try:
        # Store access token encrypted
        SettingsDatabase.set_setting(
            key="meta_access_token",
            value=credentials.access_token,
            encrypted=True
        )

        # Store ad account ID (not sensitive, no encryption needed)
        SettingsDatabase.set_setting(
            key="meta_ad_account_id",
            value=credentials.ad_account_id,
            encrypted=False
        )

        return {
            "success": True,
            "message": "Meta credentials saved successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save Meta credentials: {str(e)}"
        )


@router.get("/credentials", response_model=MetaCredentialsResponse)
async def get_meta_credentials(
    username: str = Depends(verify_credentials)
):
    """
    Check if Meta credentials are configured and return account info if available.

    Args:
        username: Authenticated user (from HTTP Basic Auth)

    Returns:
        Configuration status and account details
    """
    try:
        access_token = SettingsDatabase.get_setting("meta_access_token")
        ad_account_id = SettingsDatabase.get_setting("meta_ad_account_id")

        if not access_token or not ad_account_id:
            return MetaCredentialsResponse(configured=False)

        # Try to fetch account name from cached settings
        account_name = SettingsDatabase.get_setting("meta_account_name")
        currency = SettingsDatabase.get_setting("meta_account_currency")

        return MetaCredentialsResponse(
            configured=True,
            ad_account_id=ad_account_id,
            account_name=account_name,
            currency=currency
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Meta credentials: {str(e)}"
        )


@router.post("/verify-connection")
async def verify_meta_connection(
    username: str = Depends(verify_credentials)
):
    """
    Test Meta API connection by fetching account details.

    Args:
        username: Authenticated user (from HTTP Basic Auth)

    Returns:
        Account details if connection successful
    """
    try:
        # Retrieve stored credentials
        access_token = SettingsDatabase.get_setting("meta_access_token")
        ad_account_id = SettingsDatabase.get_setting("meta_ad_account_id")

        if not access_token or not ad_account_id:
            raise HTTPException(
                status_code=400,
                detail="Meta credentials not configured. Please save credentials first."
            )

        # Make API call to Meta to verify connection
        # Format: https://graph.facebook.com/v18.0/{ad_account_id}
        api_version = "v18.0"
        url = f"https://graph.facebook.com/{api_version}/{ad_account_id}"

        params = {
            "access_token": access_token,
            "fields": "name,currency,account_status,timezone_name"
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Invalid access token. Please check your credentials."
            )

        if response.status_code == 400:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Invalid request')
            raise HTTPException(
                status_code=400,
                detail=f"Meta API error: {error_message}"
            )

        if not response.ok:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Meta API error: {response.text}"
            )

        account_data = response.json()

        # Cache account info for faster loading
        SettingsDatabase.set_setting("meta_account_name", account_data.get("name", "Unknown"), encrypted=False)
        SettingsDatabase.set_setting("meta_account_currency", account_data.get("currency", "USD"), encrypted=False)

        return {
            "success": True,
            "name": account_data.get("name"),
            "currency": account_data.get("currency"),
            "account_status": account_data.get("account_status"),
            "timezone": account_data.get("timezone_name")
        }

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Meta API request timed out. Please try again."
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Meta API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify Meta connection: {str(e)}"
        )


@router.get("/campaigns/{campaign_id}/adsets")
async def get_campaign_adsets(
    campaign_id: str,
    days: int = 30,
    username: str = Depends(verify_credentials)
):
    """
    Fetch ad sets for a specific campaign with metrics.

    Args:
        campaign_id: The Meta campaign ID
        days: Number of days to fetch (default: 30)
        username: Authenticated user (from HTTP Basic Auth)

    Returns:
        List of ad sets with metrics
    """
    try:
        # Retrieve stored credentials
        access_token = SettingsDatabase.get_setting("meta_access_token")
        ad_account_id = SettingsDatabase.get_setting("meta_ad_account_id")

        if not access_token or not ad_account_id:
            raise HTTPException(
                status_code=400,
                detail="Meta credentials not configured. Please configure in Settings."
            )

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_start = start_date.strftime('%Y-%m-%d')
        date_end = end_date.strftime('%Y-%m-%d')

        api_version = "v18.0"
        url = f"https://graph.facebook.com/{api_version}/{campaign_id}/adsets"

        params = {
            "access_token": access_token,
            "fields": f"id,name,status,optimization_goal,billing_event,insights.time_range({{'since':'{date_start}','until':'{date_end}'}}){{spend,impressions,clicks,ctr,reach,actions,action_values}}",
            "limit": 100
        }

        response = requests.get(url, params=params, timeout=30)

        if not response.ok:
            error_data = response.json() if response.content else {}
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Meta API error: {error_message}"
            )

        data = response.json()
        adsets = data.get('data', [])

        result = []
        for adset in adsets:
            insights = adset.get('insights', {}).get('data', [])

            # Aggregate metrics
            total_spend = 0
            total_impressions = 0
            total_clicks = 0
            total_reach = 0
            conversions = 0
            conversion_value = 0

            for insight in insights:
                total_spend += float(insight.get('spend', 0))
                total_impressions += int(insight.get('impressions', 0))
                total_clicks += int(insight.get('clicks', 0))
                total_reach += int(insight.get('reach', 0))

                actions = insight.get('actions', [])
                for action in actions:
                    if action.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                        conversions += float(action.get('value', 0))

                action_values = insight.get('action_values', [])
                for action_value in action_values:
                    if action_value.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                        conversion_value += float(action_value.get('value', 0))

            result.append({
                "id": adset.get('id'),
                "name": adset.get('name'),
                "status": adset.get('status'),
                "optimization_goal": adset.get('optimization_goal'),
                "billing_event": adset.get('billing_event'),
                "spend": round(total_spend, 2),
                "impressions": total_impressions,
                "clicks": total_clicks,
                "reach": total_reach,
                "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                "conversions": conversions,
                "conversion_value": round(conversion_value, 2),
                "roas": round((conversion_value / total_spend) if total_spend > 0 else 0, 2)
            })

        return {
            "success": True,
            "adsets": result,
            "total_adsets": len(result)
        }

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Meta API request timed out. Please try again."
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Meta API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ad sets: {str(e)}"
        )


@router.get("/campaigns")
async def get_meta_campaigns(
    days: int = 30,
    username: str = Depends(verify_credentials)
):
    """
    Fetch Meta ad campaigns and their metrics for the last N days.

    Args:
        days: Number of days to fetch (default: 30)
        username: Authenticated user (from HTTP Basic Auth)

    Returns:
        List of campaigns with metrics
    """
    try:
        # Retrieve stored credentials
        access_token = SettingsDatabase.get_setting("meta_access_token")
        ad_account_id = SettingsDatabase.get_setting("meta_ad_account_id")

        if not access_token or not ad_account_id:
            raise HTTPException(
                status_code=400,
                detail="Meta credentials not configured. Please configure in Settings."
            )

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Format dates for Meta API (YYYY-MM-DD)
        date_start = start_date.strftime('%Y-%m-%d')
        date_end = end_date.strftime('%Y-%m-%d')

        api_version = "v18.0"
        url = f"https://graph.facebook.com/{api_version}/{ad_account_id}/campaigns"

        # Request campaigns with insights for the specified date range
        params = {
            "access_token": access_token,
            "fields": f"id,name,status,objective,daily_budget,lifetime_budget,insights.time_range({{'since':'{date_start}','until':'{date_end}'}}).time_increment(1){{spend,impressions,clicks,ctr,cpm,cpp,reach,frequency,actions,action_values,cost_per_action_type}}",
            "limit": 100
        }

        response = requests.get(url, params=params, timeout=30)

        if not response.ok:
            error_data = response.json() if response.content else {}
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Meta API error: {error_message}"
            )

        data = response.json()
        campaigns = data.get('data', [])

        # Transform to simplified format
        result = []
        for campaign in campaigns:
            insights = campaign.get('insights', {}).get('data', [])

            # Aggregate metrics
            total_spend = 0
            total_impressions = 0
            total_clicks = 0
            total_reach = 0
            conversions = 0
            conversion_value = 0

            for insight in insights:
                total_spend += float(insight.get('spend', 0))
                total_impressions += int(insight.get('impressions', 0))
                total_clicks += int(insight.get('clicks', 0))
                total_reach += int(insight.get('reach', 0))

                # Sum up conversions from actions
                actions = insight.get('actions', [])
                for action in actions:
                    if action.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                        conversions += float(action.get('value', 0))

                # Sum up conversion values
                action_values = insight.get('action_values', [])
                for action_value in action_values:
                    if action_value.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                        conversion_value += float(action_value.get('value', 0))

            result.append({
                "id": campaign.get('id'),
                "name": campaign.get('name'),
                "status": campaign.get('status'),
                "objective": campaign.get('objective'),
                "spend": round(total_spend, 2),
                "impressions": total_impressions,
                "clicks": total_clicks,
                "reach": total_reach,
                "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                "conversions": conversions,
                "conversion_value": round(conversion_value, 2),
                "roas": round((conversion_value / total_spend) if total_spend > 0 else 0, 2)
            })

        return {
            "success": True,
            "campaigns": result,
            "total_campaigns": len(result)
        }

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Meta API request timed out. Please try again."
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Meta API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Meta campaigns: {str(e)}"
        )
