"""
Unit tests for Meta bulk generator router.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import io
import csv


@pytest.mark.unit
class TestStripUtmParams:
    """Test UTM parameter stripping function."""

    def test_strip_utm_params_basic(self):
        """Test stripping basic UTM parameters."""
        from app.routers.meta_bulk_generator import strip_utm_params

        url = "https://example.com/product?utm_source=google&utm_medium=cpc&utm_campaign=spring"
        result = strip_utm_params(url)

        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "utm_campaign" not in result
        assert "example.com/product" in result

    def test_strip_utm_params_mixed_params(self):
        """Test stripping UTM params while keeping other params."""
        from app.routers.meta_bulk_generator import strip_utm_params

        url = "https://example.com/product?id=123&utm_source=facebook&color=red&utm_campaign=test"
        result = strip_utm_params(url)

        assert "id=123" in result
        assert "color=red" in result
        assert "utm_source" not in result
        assert "utm_campaign" not in result

    def test_strip_utm_params_no_utm(self):
        """Test URL without UTM parameters."""
        from app.routers.meta_bulk_generator import strip_utm_params

        url = "https://example.com/product?id=123&color=red"
        result = strip_utm_params(url)

        assert result == url

    def test_strip_utm_params_empty_url(self):
        """Test empty URL."""
        from app.routers.meta_bulk_generator import strip_utm_params

        result = strip_utm_params("")

        assert result == ""

    def test_strip_utm_params_none(self):
        """Test None URL."""
        from app.routers.meta_bulk_generator import strip_utm_params

        result = strip_utm_params(None)

        assert result is None

    def test_strip_utm_params_case_insensitive(self):
        """Test that UTM params are removed case-insensitively."""
        from app.routers.meta_bulk_generator import strip_utm_params

        url = "https://example.com/product?UTM_SOURCE=google&Utm_Medium=cpc"
        result = strip_utm_params(url)

        assert "UTM_SOURCE" not in result
        assert "Utm_Medium" not in result


@pytest.mark.unit
class TestExtractProductName:
    """Test product name extraction function."""

    def test_extract_product_name_with_scientific_name(self):
        """Test extracting product name with scientific name."""
        from app.routers.meta_bulk_generator import extract_product_name

        title = 'Sundial Lupine Plant - Lupinus perennis - 2" Plug'
        result = extract_product_name(title)

        assert result == "Sundial Lupine Plants"
        assert "Lupinus" not in result
        assert "2\"" not in result

    def test_extract_product_name_with_size(self):
        """Test extracting product name removing size indicator."""
        from app.routers.meta_bulk_generator import extract_product_name

        title = 'Butterfly Weed Plant - Asclepias tuberosa - Multi-Pack'
        result = extract_product_name(title)

        assert result == "Butterfly Weed Plants"
        assert "Multi-Pack" not in result

    def test_extract_product_name_pluralize(self):
        """Test that 'Plant' is converted to 'Plants'."""
        from app.routers.meta_bulk_generator import extract_product_name

        title = 'Test Plant - Some name'
        result = extract_product_name(title)

        assert "Plants" in result
        assert "Plant " not in result  # Should not have singular

    def test_extract_product_name_simple(self):
        """Test simple product name without extras."""
        from app.routers.meta_bulk_generator import extract_product_name

        title = 'Garden Rose'
        result = extract_product_name(title)

        assert result == 'Garden Rose'

    def test_extract_product_name_remove_plugs(self):
        """Test removing plug/pack indicators."""
        from app.routers.meta_bulk_generator import extract_product_name

        title = 'Native Wildflower - 3" Plugs'
        result = extract_product_name(title)

        assert "Plugs" not in result
        assert "3\"" not in result


@pytest.mark.unit
class TestFetchAndParseFeed:
    """Test feed fetching and parsing."""

    @patch('httpx.AsyncClient')
    async def test_fetch_and_parse_feed_success(self, mock_client_class):
        """Test successfully fetching and parsing TSV feed."""
        from app.routers.meta_bulk_generator import fetch_and_parse_feed

        # Mock response with TSV data
        tsv_data = "title\tlink\tprice\timage_link\nTest Product\thttps://example.com/test\t$10.00\thttps://example.com/image.jpg"

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = tsv_data
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await fetch_and_parse_feed("https://example.com/feed.tsv")

        assert len(result) == 1
        assert result[0]['title'] == 'Test Product'
        assert result[0]['link'] == 'https://example.com/test'

    @patch('httpx.AsyncClient')
    async def test_fetch_and_parse_feed_http_error(self, mock_client_class):
        """Test feed fetch with HTTP error."""
        from app.routers.meta_bulk_generator import fetch_and_parse_feed
        from fastapi import HTTPException

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await fetch_and_parse_feed("https://example.com/feed.tsv")

        assert exc_info.value.status_code == 400

    @patch('httpx.AsyncClient')
    async def test_fetch_and_parse_feed_empty(self, mock_client_class):
        """Test parsing empty feed."""
        from app.routers.meta_bulk_generator import fetch_and_parse_feed

        # Just header, no products
        tsv_data = "title\tlink\tprice"

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = tsv_data
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await fetch_and_parse_feed("https://example.com/feed.tsv")

        assert len(result) == 0


@pytest.mark.unit
class TestGenerateMetaCsv:
    """Test Meta CSV generation endpoint."""

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_generate_csv_success(self, mock_fetch, client, auth_headers):
        """Test successful CSV generation."""
        from app.database import SettingsDatabase

        # Setup settings
        SettingsDatabase.set_setting("meta_page_id", "123456")
        SettingsDatabase.set_setting("meta_instagram_id", "789012")

        # Mock feed data
        mock_fetch.return_value = [
            {
                'title': 'Test Product 1',
                'link': 'https://example.com/product1',
                'image_link': 'https://example.com/image1.jpg',
                'additional_image_link': ''
            }
        ]

        response = client.get(
            "/api/meta-bulk-generator/generate-csv?feed_url=https://example.com/feed.tsv&total_budget=100&target_cpc=0.75",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/csv; charset=utf-8'
        assert 'attachment' in response.headers['content-disposition']

        # Verify CSV content
        content = response.text
        assert 'Test Product 1' in content
        assert 'Shopping Products Campaign' in content

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_generate_csv_no_products(self, mock_fetch, client, auth_headers):
        """Test CSV generation with no products in feed."""
        mock_fetch.return_value = []

        response = client.get(
            "/api/meta-bulk-generator/generate-csv?feed_url=https://example.com/feed.tsv",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "No products found" in response.json()['detail']

    def test_generate_csv_unauthorized(self, client):
        """Test CSV generation without authentication."""
        response = client.get(
            "/api/meta-bulk-generator/generate-csv?feed_url=https://example.com/feed.tsv"
        )

        assert response.status_code == 401

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_generate_csv_budget_distribution(self, mock_fetch, client, auth_headers):
        """Test that budget is distributed evenly across products."""
        from app.database import SettingsDatabase

        SettingsDatabase.set_setting("meta_page_id", "123456")

        # Mock 4 products with total budget of $100
        mock_fetch.return_value = [
            {'title': f'Product {i}', 'link': f'https://example.com/p{i}', 'image_link': ''}
            for i in range(4)
        ]

        response = client.get(
            "/api/meta-bulk-generator/generate-csv?feed_url=https://example.com/feed.tsv&total_budget=100",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Parse CSV and check budget per product (should be $25 each)
        csv_reader = csv.DictReader(io.StringIO(response.text))
        rows = list(csv_reader)
        assert len(rows) == 4

        # Ad Set Daily Budget should be around $25 (100/4)
        for row in rows:
            budget = float(row.get('Ad Set Daily Budget', 0))
            assert 24.0 <= budget <= 26.0  # Allow small rounding differences


@pytest.mark.unit
class TestPreviewFeed:
    """Test feed preview endpoint."""

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_preview_feed_success(self, mock_fetch, client, auth_headers):
        """Test successful feed preview."""
        mock_fetch.return_value = [
            {
                'title': 'Test Product',
                'link': 'https://example.com/test?utm_source=google',
                'price': '$10.00',
                'image_link': 'https://example.com/image.jpg'
            }
        ]

        response = client.get(
            "/api/meta-bulk-generator/preview?feed_url=https://example.com/feed.tsv&total_budget=50&target_cpc=0.50",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['total_products'] == 1
        assert data['total_daily_budget'] == 50
        assert len(data['products']) == 1

        # Check that UTM params are stripped
        assert 'utm_source' not in data['products'][0]['link']

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_preview_feed_custom_template(self, mock_fetch, client, auth_headers):
        """Test preview with custom body template."""
        mock_fetch.return_value = [
            {
                'title': 'Rose Plant - Rosa species',
                'link': 'https://example.com/rose',
                'price': '$15.00',
                'image_link': ''
            }
        ]

        response = client.get(
            "/api/meta-bulk-generator/preview?feed_url=https://example.com/feed.tsv&body_template=Buy {title} Now!",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data['products']) == 1

        # Check body text uses template with extracted product name
        body_text = data['products'][0]['body_text']
        assert 'Rose Plants' in body_text
        assert 'Buy' in body_text
        assert 'Now!' in body_text

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_preview_feed_limit_100(self, mock_fetch, client, auth_headers):
        """Test that preview limits to 100 products."""
        # Mock 150 products
        mock_fetch.return_value = [
            {'title': f'Product {i}', 'link': '', 'price': '$10', 'image_link': ''}
            for i in range(150)
        ]

        response = client.get(
            "/api/meta-bulk-generator/preview?feed_url=https://example.com/feed.tsv",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total_products'] == 150
        assert len(data['products']) == 100  # Limited to 100 in preview

    def test_preview_feed_unauthorized(self, client):
        """Test preview without authentication."""
        response = client.get(
            "/api/meta-bulk-generator/preview?feed_url=https://example.com/feed.tsv"
        )

        assert response.status_code == 401


@pytest.mark.unit
class TestImageUpload:
    """Test image upload endpoints."""

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_start_image_upload_success(self, mock_fetch, client, auth_headers):
        """Test starting image upload job."""
        from app.database import SettingsDatabase

        # Setup Meta credentials
        SettingsDatabase.set_setting("meta_access_token", "test_token")
        SettingsDatabase.set_setting("meta_ad_account_id", "act_123456")

        mock_fetch.return_value = [
            {'title': 'Test', 'link': '', 'image_link': 'https://example.com/img.jpg'}
        ]

        response = client.post(
            "/api/meta-bulk-generator/upload-images?feed_url=https://example.com/feed.tsv",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'job_id' in data
        assert data['status'] == 'pending'

    def test_start_image_upload_no_credentials(self, client, auth_headers):
        """Test starting upload without Meta credentials."""
        response = client.post(
            "/api/meta-bulk-generator/upload-images?feed_url=https://example.com/feed.tsv",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "not configured" in response.json()['detail']

    def test_start_image_upload_unauthorized(self, client):
        """Test starting upload without authentication."""
        response = client.post(
            "/api/meta-bulk-generator/upload-images?feed_url=https://example.com/feed.tsv"
        )

        assert response.status_code == 401

    def test_get_upload_status_not_found(self, client, auth_headers):
        """Test getting status for non-existent job."""
        response = client.get(
            "/api/meta-bulk-generator/upload-status/nonexistent-job-id",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']

    def test_get_upload_status_success(self, client, auth_headers):
        """Test getting upload status for existing job."""
        from app.database import SettingsDatabase

        # Create a fake job
        job_id = "test-job-123"
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:status", "processing")
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:total", "10")
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:uploaded", "5")
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:failed", "1")

        response = client.get(
            f"/api/meta-bulk-generator/upload-status/{job_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['job_id'] == job_id
        assert data['status'] == 'processing'
        assert data['total_images'] == 10
        assert data['uploaded_images'] == 5
        assert data['failed_images'] == 1
        assert data['progress_percent'] == 60.0  # (5+1)/10 * 100

    def test_get_upload_status_unauthorized(self, client):
        """Test getting status without authentication."""
        response = client.get(
            "/api/meta-bulk-generator/upload-status/some-job-id"
        )

        assert response.status_code == 401


@pytest.mark.unit
class TestMetaBulkGeneratorEdgeCases:
    """Test edge cases for Meta bulk generator."""

    def test_strip_utm_params_malformed_url(self):
        """Test stripping UTM from malformed URL."""
        from app.routers.meta_bulk_generator import strip_utm_params

        url = "not a valid url with utm_source=test"
        result = strip_utm_params(url)

        # Should return original if parsing fails
        assert result == url

    def test_extract_product_name_empty_string(self):
        """Test extracting from empty string."""
        from app.routers.meta_bulk_generator import extract_product_name

        result = extract_product_name('')

        assert result == ''

    @patch('app.routers.meta_bulk_generator.fetch_and_parse_feed')
    async def test_generate_csv_minimum_budget(self, mock_fetch, client, auth_headers):
        """Test that minimum budget per product is enforced."""
        from app.database import SettingsDatabase

        SettingsDatabase.set_setting("meta_page_id", "123456")

        # Mock 200 products with total budget of $100 (would be $0.50 each)
        mock_fetch.return_value = [
            {'title': f'Product {i}', 'link': '', 'image_link': ''}
            for i in range(200)
        ]

        response = client.get(
            "/api/meta-bulk-generator/generate-csv?feed_url=https://example.com/feed.tsv&total_budget=100",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Check that minimum $1/day is enforced
        csv_reader = csv.DictReader(io.StringIO(response.text))
        rows = list(csv_reader)

        for row in rows:
            budget = float(row.get('Ad Set Daily Budget', 0))
            assert budget >= 1.0  # Minimum enforced
