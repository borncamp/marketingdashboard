import os
import json
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from app.models.settings import GoogleAdsSettings


class SettingsManager:
    """
    Manages encrypted storage of API credentials.

    In production, consider using a proper secrets manager like:
    - AWS Secrets Manager
    - HashiCorp Vault
    - Azure Key Vault

    This implementation uses local encrypted file storage.
    """

    def __init__(self, storage_path: str = "/tmp/marketing-settings.enc"):
        self.storage_path = storage_path
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)

    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or generate new one."""
        key_env = os.getenv("SETTINGS_ENCRYPTION_KEY")
        if key_env:
            return key_env.encode()

        # Generate new key if not found
        key = Fernet.generate_key()
        print(f"WARNING: Generated new encryption key. Set SETTINGS_ENCRYPTION_KEY={key.decode()} in environment")
        return key

    def save_google_ads_settings(self, settings: GoogleAdsSettings) -> None:
        """Save Google Ads settings encrypted to disk."""
        data = {
            "google_ads": settings.model_dump()
        }

        json_data = json.dumps(data)
        encrypted_data = self.cipher.encrypt(json_data.encode())

        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'wb') as f:
            f.write(encrypted_data)

    def load_google_ads_settings(self) -> Optional[GoogleAdsSettings]:
        """Load Google Ads settings from encrypted storage."""
        if not os.path.exists(self.storage_path):
            return None

        try:
            with open(self.storage_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())

            if "google_ads" in data:
                return GoogleAdsSettings(**data["google_ads"])
        except Exception as e:
            print(f"Error loading settings: {e}")
            return None

        return None

    def is_configured(self) -> bool:
        """Check if settings are configured."""
        return self.load_google_ads_settings() is not None

    def clear_settings(self) -> None:
        """Clear all stored settings."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)


# Global settings manager instance
settings_manager = SettingsManager()
