from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application configuration using Pydantic Settings.
    Environment variables are loaded from .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Google Ads API Configuration (optional - can use onboarding flow instead)
    google_ads_developer_token: Optional[str] = None
    google_ads_client_id: Optional[str] = None
    google_ads_client_secret: Optional[str] = None
    google_ads_refresh_token: Optional[str] = None
    google_ads_customer_id: Optional[str] = None
    google_ads_login_customer_id: Optional[str] = None

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Security - Optional API key for sync endpoint
    sync_api_key: Optional[str] = None

    # Background Tasks
    shopify_sync_interval_minutes: int = 10  # How often to sync Shopify data (default: 10 minutes)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.api_cors_origins.split(",")]


# Global settings instance
def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()


settings = get_settings()
