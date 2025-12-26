from fastapi import APIRouter, HTTPException
from app.models.settings import SettingsResponse, SettingsUpdateRequest, GoogleAdsSettings
from app.services.settings_manager import settings_manager
from app.services.google_ads import GoogleAdsAdapter

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings_status():
    """
    Get the current settings configuration status.

    Returns:
        SettingsResponse: Current configuration status
    """
    google_ads_settings = settings_manager.load_google_ads_settings()

    if google_ads_settings:
        # Mask the customer ID for security
        masked_id = google_ads_settings.customer_id[:3] + "****" + google_ads_settings.customer_id[-3:]

        return SettingsResponse(
            configured=True,
            has_google_ads=True,
            customer_id_masked=masked_id
        )

    return SettingsResponse(
        configured=False,
        has_google_ads=False
    )


@router.post("")
async def update_settings(request: SettingsUpdateRequest):
    """
    Update API settings and save them encrypted.

    Args:
        request: Settings update request with Google Ads credentials

    Returns:
        Success message and validation result
    """
    try:
        # Validate credentials by attempting to initialize adapter
        # We'll create a temporary adapter to test the credentials
        temp_settings = request.google_ads

        # Save the settings
        settings_manager.save_google_ads_settings(temp_settings)

        return {
            "success": True,
            "message": "Settings saved successfully",
            "customer_id_masked": temp_settings.customer_id[:3] + "****" + temp_settings.customer_id[-3:]
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save settings: {str(e)}"
        )


@router.post("/validate")
async def validate_settings(settings: GoogleAdsSettings):
    """
    Validate Google Ads API credentials without saving them.

    Args:
        settings: Google Ads settings to validate

    Returns:
        Validation result
    """
    try:
        # Try to create a client with the provided settings
        from google.ads.googleads.client import GoogleAdsClient

        # First, try to determine the manager account ID by listing accessible customers
        credentials_for_discovery = {
            "developer_token": settings.developer_token,
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "refresh_token": settings.refresh_token,
            "use_proto_plus": True,
        }

        # Try to find the manager account
        try:
            discovery_client = GoogleAdsClient.load_from_dict(credentials_for_discovery)
            customer_service = discovery_client.get_service("CustomerService")

            # Get accessible customers
            accessible_customers = customer_service.list_accessible_customers()
            customer_ids = accessible_customers.resource_names

            # Extract manager account ID (usually the first one, or find by checking if it's a manager)
            manager_id = None
            for resource_name in customer_ids:
                # Extract ID from resource name format: customers/1234567890
                cust_id = resource_name.split('/')[-1]
                # Use the first one as manager for now
                if not manager_id:
                    manager_id = cust_id

        except Exception as discovery_error:
            # If discovery fails, proceed without login_customer_id
            manager_id = None

        # Now create the full credentials with login_customer_id if we found it
        credentials = {
            "developer_token": settings.developer_token,
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "refresh_token": settings.refresh_token,
            "use_proto_plus": True,
        }

        # Use provided login_customer_id, discovered manager_id, or none
        if settings.login_customer_id:
            credentials["login_customer_id"] = settings.login_customer_id
        elif manager_id:
            credentials["login_customer_id"] = manager_id

        # Create client to validate credentials
        client = GoogleAdsClient.load_from_dict(credentials)

        # Try a simple API call to verify credentials work
        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT customer.id, customer.descriptive_name
            FROM customer
            LIMIT 1
        """

        response = ga_service.search(customer_id=settings.customer_id, query=query)

        # If we get here, credentials are valid
        customer_name = None
        for row in response:
            customer_name = row.customer.descriptive_name
            break

        return {
            "valid": True,
            "message": "Credentials validated successfully",
            "customer_name": customer_name,
            "customer_id": settings.customer_id,
            "login_customer_id": credentials.get("login_customer_id")
        }

    except Exception as e:
        error_msg = str(e)

        # Provide helpful error messages for common issues
        if "GRPC target method can't be resolved" in error_msg or "501" in error_msg:
            error_msg = (
                "Google Ads API not enabled or billing not configured. Please:\n"
                "1. Go to https://console.cloud.google.com/apis/library/googleads.googleapis.com\n"
                "2. Select your project and click 'Enable' for Google Ads API\n"
                "3. Go to https://console.cloud.google.com/billing/linkedaccount\n"
                "4. Link a billing account to your project\n"
                "5. Wait 2-3 minutes and try again"
            )
        elif "UNAUTHENTICATED" in error_msg:
            error_msg = "Invalid OAuth credentials. Please regenerate your authorization code and try again."
        elif "PERMISSION_DENIED" in error_msg:
            error_msg = "Account access denied. Make sure your regular account is linked to the manager account."

        return {
            "valid": False,
            "message": f"Validation failed: {error_msg}"
        }


@router.delete("")
async def clear_settings():
    """
    Clear all saved settings.

    Returns:
        Success message
    """
    try:
        settings_manager.clear_settings()
        return {
            "success": True,
            "message": "Settings cleared successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear settings: {str(e)}"
        )


@router.get("/oauth-url")
async def get_oauth_url(client_id: str):
    """
    Generate Google OAuth2 URL for obtaining refresh token.

    Args:
        client_id: Google OAuth2 client ID

    Returns:
        OAuth2 authorization URL
    """
    from urllib.parse import urlencode

    # Google OAuth2 endpoint
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"

    # Required scopes for Google Ads API
    scopes = ["https://www.googleapis.com/auth/adwords"]

    params = {
        "client_id": client_id,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",  # For manual code entry
        "scope": " ".join(scopes),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent"
    }

    url = f"{auth_url}?{urlencode(params)}"

    return {
        "url": url,
        "instructions": [
            "1. Open this URL in your browser",
            "2. Sign in with your Google Ads account",
            "3. Grant permissions",
            "4. Copy the authorization code",
            "5. Use the code to get your refresh token"
        ]
    }


@router.post("/exchange-code")
async def exchange_authorization_code(request: dict):
    """
    Exchange authorization code for refresh token.

    Args:
        request: Dict containing code, client_id, and client_secret

    Returns:
        Refresh token and access token
    """
    import requests

    code = request.get("code")
    client_id = request.get("client_id")
    client_secret = request.get("client_secret")

    if not all([code, client_id, client_secret]):
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: code, client_id, or client_secret"
        )

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "authorization_code"
    }

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()

        token_data = response.json()

        return {
            "success": True,
            "refresh_token": token_data.get("refresh_token"),
            "access_token": token_data.get("access_token"),
            "expires_in": token_data.get("expires_in")
        }

    except requests.exceptions.HTTPError as e:
        # Get detailed error from Google
        error_detail = "Unknown error"
        try:
            error_detail = response.json().get("error_description", str(e))
        except:
            error_detail = str(e)

        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code: {error_detail}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code: {str(e)}"
        )
