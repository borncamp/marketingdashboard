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


class MetaAppCredentials(BaseModel):
    """Meta App credentials for token exchange."""
    app_id: str
    app_secret: str


class MetaCredentialsResponse(BaseModel):
    """Response for credentials status."""
    configured: bool
    ad_account_id: Optional[str] = None
    account_name: Optional[str] = None
    currency: Optional[str] = None
    token_type: Optional[str] = None
    token_expires_in_days: Optional[int] = None
    token_expired: bool = False
    app_configured: bool = False
    app_id: Optional[str] = None


@router.post("/credentials")
async def save_meta_credentials(
    credentials: MetaCredentials,
    username: str = Depends(verify_credentials)
):
    """
    Save Meta API credentials securely in the database.
    Automatically exchanges short-lived tokens for long-lived tokens (60 days).

    Args:
        credentials: Meta access token and ad account ID
        username: Authenticated user (from HTTP Basic Auth)

    Returns:
        Success status with token info
    """
    try:
        access_token = credentials.access_token
        token_type = "short-lived"
        expires_in_days = "1-2 hours"

        # Try to exchange for long-lived token if it's a short-lived user token
        # This requires meta_app_id and meta_app_secret to be stored in database
        try:
            app_id = SettingsDatabase.get_setting("meta_app_id")
            app_secret = SettingsDatabase.get_setting("meta_app_secret")

            if app_id and app_secret:
                # Exchange short-lived token for long-lived token
                exchange_url = "https://graph.facebook.com/v18.0/oauth/access_token"
                exchange_params = {
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": credentials.access_token
                }

                exchange_response = requests.get(exchange_url, params=exchange_params, timeout=10)

                print(f"[META TOKEN EXCHANGE] Attempt with app_id={app_id[:10]}...")
                print(f"[META TOKEN EXCHANGE] Response status: {exchange_response.status_code}")

                if exchange_response.ok:
                    exchange_data = exchange_response.json()
                    print(f"[META TOKEN EXCHANGE] Response data: {exchange_data}")
                    access_token = exchange_data.get("access_token", credentials.access_token)
                    expires_in = exchange_data.get("expires_in", 0)

                    if expires_in > 0:
                        token_type = "long-lived"
                        expires_in_days = f"{expires_in // 86400} days"

                        # Store expiry timestamp
                        expiry_timestamp = datetime.now() + timedelta(seconds=expires_in)
                        SettingsDatabase.set_setting(
                            key="meta_token_expiry",
                            value=expiry_timestamp.isoformat(),
                            encrypted=False
                        )
                        print(f"[META TOKEN EXCHANGE] SUCCESS! Token extended to {expires_in_days}")
                    else:
                        print(f"[META TOKEN EXCHANGE] No expires_in in response")
                else:
                    error_data = exchange_response.json() if exchange_response.content else {}
                    print(f"[META TOKEN EXCHANGE] FAILED: {exchange_response.status_code} - {error_data}")
        except Exception as e:
            # If token exchange fails, continue with the original token
            print(f"[META TOKEN EXCHANGE] Exception: {e}")

        # Store access token encrypted
        SettingsDatabase.set_setting(
            key="meta_access_token",
            value=access_token,
            encrypted=True
        )

        # Store ad account ID (not sensitive, no encryption needed)
        SettingsDatabase.set_setting(
            key="meta_ad_account_id",
            value=credentials.ad_account_id,
            encrypted=False
        )

        # Store token type for reference
        SettingsDatabase.set_setting(
            key="meta_token_type",
            value=token_type,
            encrypted=False
        )

        return {
            "success": True,
            "message": f"Meta credentials saved successfully ({token_type} token, expires in ~{expires_in_days})",
            "token_type": token_type,
            "expires_in": expires_in_days
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
        token_type = SettingsDatabase.get_setting("meta_token_type")
        token_expiry_str = SettingsDatabase.get_setting("meta_token_expiry")

        # Calculate days until expiry
        token_expires_in_days = None
        token_expired = False

        if token_expiry_str:
            try:
                from dateutil import parser
                expiry_date = parser.parse(token_expiry_str)
                now = datetime.now(expiry_date.tzinfo) if expiry_date.tzinfo else datetime.now()
                days_remaining = (expiry_date - now).days

                token_expires_in_days = days_remaining
                token_expired = days_remaining < 0
            except Exception as e:
                print(f"Failed to parse token expiry: {e}")

        # Check if app credentials are configured
        app_id = SettingsDatabase.get_setting("meta_app_id")
        app_secret = SettingsDatabase.get_setting("meta_app_secret")
        app_configured = bool(app_id and app_secret)

        return MetaCredentialsResponse(
            configured=True,
            ad_account_id=ad_account_id,
            account_name=account_name,
            currency=currency,
            token_type=token_type,
            token_expires_in_days=token_expires_in_days,
            token_expired=token_expired,
            app_configured=app_configured,
            app_id=app_id if app_configured else None
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Meta credentials: {str(e)}"
        )


@router.post("/app-credentials")
async def save_meta_app_credentials(
    credentials: MetaAppCredentials,
    username: str = Depends(verify_credentials)
):
    """
    Save Meta App credentials (App ID and Secret) for token exchange.
    These are stored in the database and used to exchange short-lived tokens for long-lived ones.

    Args:
        credentials: Meta App ID and Secret
        username: Authenticated user (from HTTP Basic Auth)

    Returns:
        Success status
    """
    try:
        # Store app ID (not encrypted, not sensitive)
        SettingsDatabase.set_setting(
            key="meta_app_id",
            value=credentials.app_id,
            encrypted=False
        )

        # Store app secret (encrypted)
        SettingsDatabase.set_setting(
            key="meta_app_secret",
            value=credentials.app_secret,
            encrypted=True
        )

        return {
            "success": True,
            "message": "Meta App credentials saved successfully. New tokens will be automatically extended to 60 days."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save Meta App credentials: {str(e)}"
        )


@router.get("/token-status")
async def get_token_status(
    username: str = Depends(verify_credentials)
):
    """
    Get detailed token status information for debugging.

    Returns:
        Token type, expiry date, and app configuration status
    """
    try:
        access_token = SettingsDatabase.get_setting("meta_access_token")
        if not access_token:
            return {
                "configured": False,
                "message": "No token configured"
            }

        token_type = SettingsDatabase.get_setting("meta_token_type") or "unknown"
        token_expiry_str = SettingsDatabase.get_setting("meta_token_expiry")
        app_id = SettingsDatabase.get_setting("meta_app_id")
        app_secret = SettingsDatabase.get_setting("meta_app_secret")

        expiry_info = None
        if token_expiry_str:
            try:
                from dateutil import parser
                expiry_date = parser.parse(token_expiry_str)
                now = datetime.now(expiry_date.tzinfo) if expiry_date.tzinfo else datetime.now()
                days_remaining = (expiry_date - now).days
                hours_remaining = ((expiry_date - now).total_seconds() / 3600) % 24

                expiry_info = {
                    "expiry_date": expiry_date.isoformat(),
                    "days_remaining": days_remaining,
                    "hours_remaining": round(hours_remaining, 1),
                    "expired": days_remaining < 0
                }
            except Exception as e:
                expiry_info = {"error": str(e)}

        return {
            "configured": True,
            "token_type": token_type,
            "app_credentials_configured": bool(app_id and app_secret),
            "expiry_info": expiry_info,
            "message": f"Token is {token_type}" + (f" and expires in {expiry_info['days_remaining']} days" if expiry_info and 'days_remaining' in expiry_info else "")
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get token status: {str(e)}"
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
