"""
Meta Image Upload Service
Handles uploading images to Meta Marketing API and caching hashes.
"""
import httpx
import hashlib
import logging
from typing import Optional, Dict
from app.database import SettingsDatabase

logger = logging.getLogger(__name__)


class MetaImageUploadService:
    """Service for uploading images to Meta and managing image hashes."""

    BASE_URL = "https://graph.facebook.com/v18.0"

    @staticmethod
    def get_image_url_hash(image_url: str) -> str:
        """Generate a hash of the image URL for caching."""
        return hashlib.sha256(image_url.encode()).hexdigest()

    @staticmethod
    async def upload_image_to_meta(
        image_url: str,
        access_token: str,
        ad_account_id: str
    ) -> Optional[str]:
        """
        Upload an image to Meta and return the image hash.

        Args:
            image_url: URL of the image to upload
            access_token: Meta API access token
            ad_account_id: Meta ad account ID (format: act_123456)

        Returns:
            Image hash from Meta, or None if upload failed
        """
        try:
            # Download the image first
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Downloading image from {image_url}")
                img_response = await client.get(image_url)

                if img_response.status_code != 200:
                    logger.error(f"Failed to download image: HTTP {img_response.status_code}")
                    return None

                image_bytes = img_response.content

                # Prepare the upload to Meta
                upload_url = f"{MetaImageUploadService.BASE_URL}/{ad_account_id}/adimages"

                files = {
                    'filename': ('image.jpg', image_bytes, 'image/jpeg')
                }

                data = {
                    'access_token': access_token
                }

                logger.info(f"Uploading image to Meta for account {ad_account_id}")
                meta_response = await client.post(upload_url, files=files, data=data)

                if meta_response.status_code != 200:
                    logger.error(f"Meta API error: {meta_response.status_code} - {meta_response.text}")
                    return None

                result = meta_response.json()

                # Extract image hash from response
                # Response format: {"images": {"image.jpg": {"hash": "abc123..."}}}
                if 'images' in result:
                    for img_data in result['images'].values():
                        if 'hash' in img_data:
                            image_hash = img_data['hash']
                            logger.info(f"Successfully uploaded image, hash: {image_hash}")
                            return image_hash

                logger.error(f"Unexpected Meta API response format: {result}")
                return None

        except httpx.TimeoutException:
            logger.error(f"Timeout downloading or uploading image: {image_url}")
            return None
        except Exception as e:
            logger.error(f"Error uploading image to Meta: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_cached_image_hash(image_url: str) -> Optional[str]:
        """
        Get cached image hash for a given image URL.

        Args:
            image_url: URL of the image

        Returns:
            Cached image hash or None if not found
        """
        url_hash = MetaImageUploadService.get_image_url_hash(image_url)
        cache_key = f"meta_image_hash:{url_hash}"
        return SettingsDatabase.get_setting(cache_key)

    @staticmethod
    def cache_image_hash(image_url: str, image_hash: str):
        """
        Cache an image hash for a given image URL.

        Args:
            image_url: URL of the image
            image_hash: Meta image hash to cache
        """
        url_hash = MetaImageUploadService.get_image_url_hash(image_url)
        cache_key = f"meta_image_hash:{url_hash}"
        SettingsDatabase.set_setting(cache_key, image_hash)
        logger.info(f"Cached image hash for {image_url[:50]}...")

    @staticmethod
    async def get_or_upload_image(
        image_url: str,
        access_token: str,
        ad_account_id: str
    ) -> Optional[str]:
        """
        Get cached image hash or upload image to Meta if not cached.

        Args:
            image_url: URL of the image
            access_token: Meta API access token
            ad_account_id: Meta ad account ID

        Returns:
            Image hash (from cache or newly uploaded)
        """
        # Check cache first
        cached_hash = MetaImageUploadService.get_cached_image_hash(image_url)
        if cached_hash:
            logger.info(f"Using cached image hash for {image_url[:50]}...")
            return cached_hash

        # Upload to Meta
        image_hash = await MetaImageUploadService.upload_image_to_meta(
            image_url, access_token, ad_account_id
        )

        # Cache the result
        if image_hash:
            MetaImageUploadService.cache_image_hash(image_url, image_hash)

        return image_hash
