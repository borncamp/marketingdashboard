from typing import Optional
from pydantic import BaseModel, Field


class GoogleAdsSettings(BaseModel):
    """Google Ads API settings."""
    developer_token: str = Field(..., description="Google Ads developer token")
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    refresh_token: str = Field(..., description="OAuth2 refresh token")
    customer_id: str = Field(..., description="Google Ads customer ID (without hyphens)")
    login_customer_id: Optional[str] = Field(None, description="Login customer ID for manager accounts")


class SettingsResponse(BaseModel):
    """Response model for settings status."""
    configured: bool = Field(..., description="Whether settings are configured")
    has_google_ads: bool = Field(False, description="Whether Google Ads is configured")
    customer_id_masked: Optional[str] = Field(None, description="Masked customer ID")


class SettingsUpdateRequest(BaseModel):
    """Request to update Google Ads settings."""
    google_ads: GoogleAdsSettings
