"""
Meta Ads Bulk Generator API endpoint.
Fetches Google Shopping feed and converts to Meta Ads CSV format.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict
from pydantic import BaseModel
import io
import csv
import httpx
import logging
import asyncio
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from app.auth import verify_credentials
from app.database import SettingsDatabase
from app.services.meta_image_upload import MetaImageUploadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meta-bulk-generator", tags=["meta-bulk-generator"])


def strip_utm_params(url: str) -> str:
    """Remove UTM parameters from URL."""
    if not url:
        return url

    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # Remove all UTM parameters
        cleaned_params = {k: v for k, v in query_params.items() if not k.lower().startswith('utm_')}

        # Reconstruct URL
        new_query = urlencode(cleaned_params, doseq=True)
        cleaned_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        return cleaned_url
    except:
        return url


def extract_product_name(title: str) -> str:
    """Extract clean product name from title.

    Examples:
        "Sundial Lupine Plant - Lupinus perennis - 2\" Plug" -> "Sundial Lupine Plants"
        "Butterfly Weed Plant - Asclepias tuberosa - Multi-Pack" -> "Butterfly Weed Plants"
    """
    import re

    # Remove common suffixes and technical details
    # Remove everything after " - " (removes scientific names, sizes, etc.)
    clean = re.split(r'\s+-\s+', title)[0]

    # Remove size/quantity indicators in quotes or at end
    clean = re.sub(r'\s+\d+["\']?\s*(Plug|Pack|Container|Pot)s?.*$', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+(Multi-Pack|Starter Plant|Bare Root)s?.*$', '', clean, flags=re.IGNORECASE)

    # Replace "Plant" with "Plants" for better ad copy
    clean = re.sub(r'\bPlant\b', 'Plants', clean)
    clean = re.sub(r'\bplant\b', 'plants', clean)

    return clean.strip()


async def fetch_and_parse_feed(feed_url: str) -> list:
    """Fetch and parse Google Shopping TSV feed."""
    logger.info(f"Fetching feed from URL: {feed_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(feed_url)

        logger.info(f"Feed fetch status: {response.status_code}, content length: {len(response.text)}")

        if response.status_code != 200:
            logger.error(f"Failed to fetch feed: HTTP {response.status_code}")
            raise HTTPException(status_code=400, detail=f"Failed to fetch feed: {response.status_code}")

        # Parse TSV using csv.DictReader to handle quoted fields properly
        reader = csv.DictReader(io.StringIO(response.text), delimiter='\t')
        products = []

        for row in reader:
            products.append(row)

        logger.info(f"Successfully parsed {len(products)} products")
        return products

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching feed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing feed: {str(e)}", exc_info=True)
        raise


@router.get("/generate-csv")
async def generate_meta_csv(
    feed_url: str,
    total_budget: float = 50.0,
    target_cpc: float = 0.50,
    body_template: str = "{title} For Sale",
    link_description: str = "Prices range from $2.25-$5.00 per plant",
    credentials=Depends(verify_credentials)
):
    """
    Generate Meta Ads CSV from Google Shopping feed.

    Args:
        feed_url: URL to Google Shopping TSV feed
        total_budget: Total daily budget to allocate across products (default: $50)
        target_cpc: Target cost per click for bid amount (default: $0.50)
        body_template: Template for body text, use {title} as placeholder (default: "{title} For Sale")
        link_description: Link description for all ads (default: "Prices range from $2.25-$5.00 per plant")

    Returns:
        CSV file for Meta Ads Manager import
    """
    logger.info(f"generate_meta_csv called: feed_url={feed_url}, total_budget={total_budget}, target_cpc={target_cpc}, user={credentials}")

    try:
        # Get Meta Page ID from settings or use default
        meta_page_id = SettingsDatabase.get_setting("meta_page_id") or "162671656938231"
        meta_instagram_id = SettingsDatabase.get_setting("meta_instagram_id") or "544782808663328"
        logger.info(f"Using Meta Page ID: {meta_page_id}, Instagram ID: {meta_instagram_id}")

        # Fetch and parse feed
        products = await fetch_and_parse_feed(feed_url)

        if not products:
            raise HTTPException(status_code=400, detail="No products found in feed")

        # Budget per product (equal distribution for now)
        budget_per_product = round(total_budget / len(products), 2) if products else 1.0
        budget_per_product = max(budget_per_product, 1.0)  # Minimum $1/day
        logger.info(f"Budget per product: ${budget_per_product}/day for {len(products)} products")

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Meta Ads CSV header - exact match to Meta's export format
        header = ["Campaign ID","Creation Package Config ID","Campaign Name","Special Ad Categories","Special Ad Category Country","Campaign Status","Campaign Objective","Buying Type","Campaign Spend Limit","Campaign Daily Budget","Campaign Lifetime Budget","Campaign Bid Strategy","Tags","Campaign Is Using L3 Schedule","Campaign Start Time","Campaign Stop Time","Product Catalog ID","Campaign Page ID","New Objective","Buy With Prime Type","Is Budget Scheduling Enabled For Campaign","Campaign High Demand Periods","Buy With Integration Partner","Ad Set ID","Ad Set Run Status","Ad Set Lifetime Impressions","Ad Set Name","Ad Set Time Start","Ad Set Time Stop","Ad Set Daily Budget","Destination Type","Use Dynamic Creative","Ad Set Lifetime Budget","Rate Card","Ad Set Schedule","Use Accelerated Delivery","Frequency Control","Ad Set Minimum Spend Limit","Ad Set Maximum Spend Limit","Is Budget Scheduling Enabled For Ad Set","Ad Set High Demand Periods","Link Object ID","Optimized Conversion Tracking Pixels","Optimized Custom Conversion ID","Optimized Pixel Rule","Optimized Event","Custom Event Name","Link","Application ID","Product Set ID","Place Page Set ID","Object Store URL","Offer ID","Offline Event Data Set ID","Countries","Cities","Regions","Electoral Districts","Zip","Addresses","Geo Markets (DMA)","Global Regions","Large Geo Areas","Medium Geo Areas","Small Geo Areas","Metro Areas","Neighborhoods","Subneighborhoods","Subcities","Location Types","Location Cluster IDs","Location Set IDs","Excluded Countries","Excluded Cities","Excluded Large Geo Areas","Excluded Medium Geo Areas","Excluded Metro Areas","Excluded Small Geo Areas","Excluded Subcities","Excluded Neighborhoods","Excluded Subneighborhoods","Excluded Regions","Excluded Electoral Districts","Excluded Zip","Excluded Addresses","Excluded Geo Markets (DMA)","Excluded Global Regions","Excluded Location Cluster IDs","Gender","Age Min","Age Max","Education Status","Fields of Study","Education Schools","Work Job Titles","Work Employers","College Start Year","College End Year","Interested In","Relationship","Family Statuses","Industries","Life Events","Income","Multicultural Affinity","Household Composition","Behaviors","Connections","Excluded Connections","Friends of Connections","Locales","Site Category","Unified Interests","Excluded User AdClusters","Broad Category Clusters","Targeting Categories - ALL OF","Custom Audiences","Excluded Custom Audiences","Flexible Inclusions","Flexible Exclusions","Advantage Audience","Age Range","Targeting Optimization","Targeting Relaxation","Product Audience Specs","Excluded Product Audience Specs","Targeted Business Locations","Dynamic Audiences","Excluded Dynamic Audiences","Beneficiary","Payer","Publisher Platforms","Facebook Positions","Instagram Positions","Audience Network Positions","Messenger Positions","WhatsApp Positions","Oculus Positions","Device Platforms","User Device","Excluded User Device","User Operating System","User OS Version","Wireless Carrier","Excluded Publisher Categories","Brand Safety Inventory Filtering Levels","Optimization Goal","Attribution Spec","Billing Event","Bid Amount","Ad Set Bid Strategy","Regional Regulated Categories","Beneficiary (financial ads in Australia)","Payer (financial ads in Australia)","Beneficiary (financial ads in Taiwan)","Payer (financial ads in Taiwan)","Beneficiary (Taiwan)","Payer (Taiwan)","Beneficiary (Singapore)","Payer (Singapore)","Beneficiary (securities ads in India)","Payer (securities ads in India)","Beneficiary (selected locations)","Payer (selected locations)","Story ID","Ad ID","Ad Status","Preview Link","Instagram Preview Link","Ad Name","Dynamic Creative Ad Format","Title","Additional Title 1","Additional Title 2","Additional Title 3","Additional Title 4","Body","Additional Body 1","Additional Body 2","Additional Body 3","Additional Body 4","Display Link","Link Description","Additional Link Description 1","Additional Link Description 2","Additional Link Description 3","Additional Link Description 4","Optimize text per person","Retailer IDs","Post Click Item Headline","Post Click Item Description","Conversion Tracking Pixels","Optimized Ad Creative","Image Hash","Image File Name","Image Crops","Video Thumbnail URL","Additional Image 1 Hash","Additional Image 1 Crops","Additional Image 2 Hash","Additional Image 2 Crops","Additional Image 3 Hash","Additional Image 3 Crops","Additional Image 4 Hash","Additional Image 4 Crops","Additional Image 5 Hash","Additional Image 5 Crops","Additional Image 6 Hash","Additional Image 6 Crops","Additional Image 7 Hash","Additional Image 7 Crops","Additional Image 8 Hash","Additional Image 8 Crops","Additional Image 9 Hash","Additional Image 9 Crops","Instagram Platform Image Hash","Instagram Platform Image Crops","Instagram Platform Image URL","Carousel Delivery Mode","Creative Type","URL Tags","Event ID","Video ID","Video File Name","Additional Video 1 ID","Additional Video 1 Thumbnail URL","Additional Video 2 ID","Additional Video 2 Thumbnail URL","Additional Video 3 ID","Additional Video 3 Thumbnail URL","Additional Video 4 ID","Additional Video 4 Thumbnail URL","Additional Video 5 ID","Additional Video 5 Thumbnail URL","Additional Video 6 ID","Additional Video 6 Thumbnail URL","Additional Video 7 ID","Additional Video 7 Thumbnail URL","Additional Video 8 ID","Additional Video 8 Thumbnail URL","Additional Video 9 ID","Additional Video 9 Thumbnail URL","Instagram Account ID","Mobile App Deep Link","Product Link","App Link Destination","Call Extension Phone Data ID","Call to Action","Additional Call To Action 1","Additional Call To Action 2","Additional Call To Action 3","Additional Call To Action 4","Additional Call To Action 5","Additional Call To Action 6","Additional Call To Action 7","Additional Call To Action 8","Additional Call To Action 9","Call to Action Link","Call to Action WhatsApp Number","Marketing Message Primary Text","Marketing Message Auto Reply - Body Text","Marketing Message Auto Reply - Image Hash","Marketing Message Auto Reply - Video ID","Marketing Message Auto Reply - Button 1 - Text","Marketing Message Auto Reply - Button 1 - Type","Marketing Message Auto Reply - Button 1 - URL","Marketing Message Button 1 - Button Text","Marketing Message Button 1 - Type","Marketing Message Button 1 - Response Text","Marketing Message Button 1 - Image Hash","Marketing Message Button 1 - Video ID","Marketing Message Button 1 - Video Thumbnail URL","Marketing Message Button 1 - Call to Action Button - Type","Marketing Message Button 1 - Call to Action Button - Text","Marketing Message Button 1 - Call to Action Button - URL","Marketing Message Button 2 - Button Text","Marketing Message Button 2 - Type","Marketing Message Button 2 - Response Text","Marketing Message Button 2 - Image Hash","Marketing Message Button 2 - Video ID","Marketing Message Button 2 - Video Thumbnail URL","Marketing Message Button 2 - Call to Action Button - Type","Marketing Message Button 2 - Call to Action Button - Text","Marketing Message Button 2 - Call to Action Button - URL","Additional Custom Tracking Specs","Video Retargeting","Lead Form ID","Permalink","Force Single Link","Format Option","Dynamic Ad Voice","Creative Optimization","Template URL","Android App Name","Android Package Name","Deep Link For Android","Facebook App ID","iOS App Name","iOS App Store ID","Deep Link For iOS","iPad App Name","iPad App Store ID","Deep Link For iPad","iPhone App Name","iPhone App Store ID","Deep Link For iPhone","Deep link to website","Windows Store ID","Windows App Name","Deep Link For Windows Phone","Add End Card","Dynamic Ads Ad Context","Page Welcome Message","App Destination","App Destination Page ID","Use Page as Actor","Image Overlay Template","Image Overlay Text Type","Image Overlay Text Font","Image Overlay Position","Image Overlay Theme Color","Image Overlay Float With Margin","Image Layer 1 - layer_type","Image Layer 1 - image_source","Image Layer 1 - overlay_shape","Image Layer 1 - text_font","Image Layer 1 - shape_color","Image Layer 1 - text_color","Image Layer 1 - content_type","Image Layer 1 - price","Image Layer 1 - low_price","Image Layer 1 - high_price","Image Layer 1 - frame_source","Image Layer 1 - frame_image_hash","Image Layer 1 - scale","Image Layer 1 - blending_mode","Image Layer 1 - opacity","Image Layer 1 - overlay_position","Image Layer 1 - pad_image","Image Layer 1 - crop_image","Image Layer 2 - layer_type","Image Layer 2 - image_source","Image Layer 2 - overlay_shape","Image Layer 2 - text_font","Image Layer 2 - shape_color","Image Layer 2 - text_color","Image Layer 2 - content_type","Image Layer 2 - price","Image Layer 2 - low_price","Image Layer 2 - high_price","Image Layer 2 - frame_source","Image Layer 2 - frame_image_hash","Image Layer 2 - scale","Image Layer 2 - blending_mode","Image Layer 2 - opacity","Image Layer 2 - overlay_position","Image Layer 2 - pad_image","Image Layer 2 - crop_image","Image Layer 3 - layer_type","Image Layer 3 - image_source","Image Layer 3 - overlay_shape","Image Layer 3 - text_font","Image Layer 3 - shape_color","Image Layer 3 - text_color","Image Layer 3 - content_type","Image Layer 3 - price","Image Layer 3 - low_price","Image Layer 3 - high_price","Image Layer 3 - frame_source","Image Layer 3 - frame_image_hash","Image Layer 3 - scale","Image Layer 3 - blending_mode","Image Layer 3 - opacity","Image Layer 3 - overlay_position","Image Layer 3 - pad_image","Image Layer 3 - crop_image","Product 1 - Link","Product 1 - Name","Product 1 - Description","Product 1 - Marketing Message - Description","Product 1 - Image Hash","Product 1 - Image Crops","Product 1 - Video ID","Product 1 - Call To Action Link","Product 1 - Mobile App Deep Link","Product 1 - Display Link","Product 1 - Place Data","Product 1 - Is Static Card","Product 2 - Link","Product 2 - Name","Product 2 - Description","Product 2 - Marketing Message - Description","Product 2 - Image Hash","Product 2 - Image Crops","Product 2 - Video ID","Product 2 - Call To Action Link","Product 2 - Mobile App Deep Link","Product 2 - Display Link","Product 2 - Place Data","Product 2 - Is Static Card","Product 3 - Link","Product 3 - Name","Product 3 - Description","Product 3 - Marketing Message - Description","Product 3 - Image Hash","Product 3 - Image Crops","Product 3 - Video ID","Product 3 - Call To Action Link","Product 3 - Mobile App Deep Link","Product 3 - Display Link","Product 3 - Place Data","Product 3 - Is Static Card","Product 4 - Link","Product 4 - Name","Product 4 - Description","Product 4 - Marketing Message - Description","Product 4 - Image Hash","Product 4 - Image Crops","Product 4 - Video ID","Product 4 - Call To Action Link","Product 4 - Mobile App Deep Link","Product 4 - Display Link","Product 4 - Place Data","Product 4 - Is Static Card","Product 5 - Link","Product 5 - Name","Product 5 - Description","Product 5 - Marketing Message - Description","Product 5 - Image Hash","Product 5 - Image Crops","Product 5 - Video ID","Product 5 - Call To Action Link","Product 5 - Mobile App Deep Link","Product 5 - Display Link","Product 5 - Place Data","Product 5 - Is Static Card","Product 6 - Link","Product 6 - Name","Product 6 - Description","Product 6 - Marketing Message - Description","Product 6 - Image Hash","Product 6 - Image Crops","Product 6 - Video ID","Product 6 - Call To Action Link","Product 6 - Mobile App Deep Link","Product 6 - Display Link","Product 6 - Place Data","Product 6 - Is Static Card","Product 7 - Link","Product 7 - Name","Product 7 - Description","Product 7 - Marketing Message - Description","Product 7 - Image Hash","Product 7 - Image Crops","Product 7 - Video ID","Product 7 - Call To Action Link","Product 7 - Mobile App Deep Link","Product 7 - Display Link","Product 7 - Place Data","Product 7 - Is Static Card","Product 8 - Link","Product 8 - Name","Product 8 - Description","Product 8 - Marketing Message - Description","Product 8 - Image Hash","Product 8 - Image Crops","Product 8 - Video ID","Product 8 - Call To Action Link","Product 8 - Mobile App Deep Link","Product 8 - Display Link","Product 8 - Place Data","Product 8 - Is Static Card","Product 9 - Link","Product 9 - Name","Product 9 - Description","Product 9 - Marketing Message - Description","Product 9 - Image Hash","Product 9 - Image Crops","Product 9 - Video ID","Product 9 - Call To Action Link","Product 9 - Mobile App Deep Link","Product 9 - Display Link","Product 9 - Place Data","Product 9 - Is Static Card","Product 10 - Link","Product 10 - Name","Product 10 - Description","Product 10 - Marketing Message - Description","Product 10 - Image Hash","Product 10 - Image Crops","Product 10 - Video ID","Product 10 - Call To Action Link","Product 10 - Mobile App Deep Link","Product 10 - Display Link","Product 10 - Place Data","Product 10 - Is Static Card","Product Sales Channel","Dynamic Creative Lead Form ID","Additional Dynamic Creative Lead Gen Form ID 1","Additional Dynamic Creative Lead Gen Form ID 2","Additional Dynamic Creative Lead Gen Form ID 3","Additional Dynamic Creative Lead Gen Form ID 4","Additional Dynamic Creative Lead Gen Form ID 5","Additional Dynamic Creative Lead Gen Form ID 6","Additional Dynamic Creative Lead Gen Form ID 7","Additional Dynamic Creative Lead Gen Form ID 8","Additional Dynamic Creative Lead Gen Form ID 9","Dynamic Creative Call to Action","Additional Dynamic Creative Call To Action Type 1","Additional Dynamic Creative Call To Action Type 2","Additional Dynamic Creative Call To Action Type 3","Additional Dynamic Creative Call To Action Type 4","Additional Dynamic Creative Call To Action Type 5","Additional Dynamic Creative Call To Action Type 6","Additional Dynamic Creative Call To Action Type 7","Additional Dynamic Creative Call To Action Type 8","Additional Dynamic Creative Call To Action Type 9","Dynamic Creative Additional Optimizations","Degrees of Freedom Type","Creative Destination Type","Creative Onsite Destinations","Mockup ID","Text Transformations","Ad Stop Time","Ad Start Time"]
        writer.writerow(header)

        # Write each product as an ad
        for product in products:
            # Extract fields from Google Shopping feed - NO TRUNCATION
            title = product.get('title', 'Product')
            raw_link = product.get('link', '')
            link = strip_utm_params(raw_link)  # Remove UTM parameters

            # Extract clean product name and generate body text from template
            product_name = extract_product_name(title)
            body_text = body_template.replace('{title}', product_name)

            # Extract domain for display link
            display_link = ''
            if link:
                try:
                    parsed = urlparse(link)
                    display_link = parsed.netloc.replace('www.', '')
                except:
                    pass

            # Get cached image hash if available
            image_url = product.get('image_link', '')
            image_hash = ''
            if image_url:
                cached_hash = MetaImageUploadService.get_cached_image_hash(image_url)
                if cached_hash:
                    image_hash = cached_hash

            # Get additional images from feed (comma-separated URLs)
            additional_images = []
            additional_image_link = product.get('additional_image_link', '')
            if additional_image_link:
                # Split by comma and strip whitespace
                additional_images = [url.strip() for url in additional_image_link.split(',') if url.strip()]

            # Get cached hashes for additional images
            additional_image_hashes = []
            for img_url in additional_images[:9]:  # Meta supports up to 9 additional images
                cached_hash = MetaImageUploadService.get_cached_image_hash(img_url)
                if cached_hash:
                    additional_image_hashes.append(cached_hash)
                else:
                    additional_image_hashes.append('')  # Empty if not cached

            # Create a row with all 525 columns (most will be empty)
            row = [''] * len(header)

            # Fill in the relevant columns
            row[2] = 'Shopping Products Campaign'  # Campaign Name
            row[5] = 'PAUSED'  # Campaign Status
            row[6] = 'Traffic'  # Campaign Objective
            row[7] = 'AUCTION'  # Buying Type
            row[11] = 'Cost per result goal'  # Campaign Bid Strategy
            row[17] = meta_page_id or ''  # Campaign Page ID
            row[18] = 'Yes'  # New Objective
            row[19] = 'NONE'  # Buy With Prime Type
            row[20] = 'No'  # Is Budget Scheduling Enabled For Campaign
            row[21] = '[]'  # Campaign High Demand Periods
            row[22] = 'NONE'  # Buy With Integration Partner
            row[24] = 'PAUSED'  # Ad Set Run Status
            row[25] = '0'  # Ad Set Lifetime Impressions
            row[26] = f"Ad Set - {title}"  # Ad Set Name
            row[29] = budget_per_product  # Ad Set Daily Budget
            row[30] = 'UNDEFINED'  # Destination Type
            row[31] = 'Yes'  # Use Dynamic Creative
            row[35] = 'No'  # Use Accelerated Delivery
            row[39] = 'No'  # Is Budget Scheduling Enabled For Ad Set
            row[40] = '[]'  # Ad Set High Demand Periods
            row[47] = link  # Link
            row[54] = 'United States'  # Countries
            row[56] = 'Connecticut US, Delaware US, Indiana US, Kentucky US, Maine US, Maryland US, Massachusetts US, Michigan US, Minnesota US, New Hampshire US, New Jersey US, New York US, Ohio US, Pennsylvania US, Rhode Island US, Tennessee US, Vermont US, Virginia US, West Virginia US, Wisconsin US'  # Regions
            row[69] = 'home, recent'  # Location Types
            row[89] = '30'  # Age Min
            row[90] = '65'  # Age Max
            row[118] = '[{"interests":[{"id":"6003053056644","name":"Gardening"},{"id":"6003137618950","name":"Ornamental plant"},{"id":"6003320013018","name":"Garden"},{"id":"6003325525709","name":"Horticulture"},{"id":"6004025434189","name":"Plant"},{"id":"6005060777126","name":"Backyard"}]}]'  # Flexible Inclusions
            row[120] = '0'  # Advantage Audience
            row[145] = 'FACEBOOK_STANDARD, AN_STANDARD'  # Brand Safety Inventory Filtering Levels
            row[146] = 'LINK_CLICKS'  # Optimization Goal
            row[147] = '[{"event_type":"CLICK_THROUGH","window_days":1}]'  # Attribution Spec
            row[148] = 'IMPRESSIONS'  # Billing Event
            row[149] = f'{target_cpc:.2f}'  # Bid Amount
            row[166] = 'PAUSED'  # Ad Status
            row[169] = f"Ad - {title}"  # Ad Name
            row[170] = 'Image Carousel'  # Dynamic Creative Ad Format
            row[171] = title  # Title (no truncation)
            row[176] = body_text  # Body (from template)
            row[181] = display_link  # Display Link
            row[182] = link_description  # Link Description
            row[187] = 'No'  # Optimize text per person
            row[192] = 'No'  # Optimized Ad Creative
            row[193] = image_hash  # Image Hash (from cache)

            # Add additional image hashes (up to 9)
            additional_hash_indices = [197, 199, 201, 203, 205, 207, 209, 211, 213]
            for i, hash_value in enumerate(additional_image_hashes):
                if i < len(additional_hash_indices):
                    row[additional_hash_indices[i]] = hash_value

            row[219] = 'Link Page Post Ad'  # Creative Type
            row[242] = meta_instagram_id  # Instagram Account ID
            row[247] = 'SHOP_NOW'  # Call to Action
            row[284] = '[]'  # Additional Custom Tracking Specs
            row[285] = 'No'  # Video Retargeting
            row[288] = ''  # Force Single Link (empty, not 'No')
            row[315] = 'No'  # Use Page as Actor
            row[507] = 'SHOP_NOW'  # Dynamic Creative Call to Action
            row[517] = 'No'  # Dynamic Creative Additional Optimizations
            row[518] = 'DISABLED'  # Degrees of Freedom Type

            writer.writerow(row)

        # Return CSV
        output.seek(0)
        csv_content = output.getvalue()
        logger.info(f"Generated CSV: {len(csv_content)} bytes, {len(products)} product rows")

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=meta_ads_bulk_import.csv"
            }
        )

    except httpx.TimeoutException:
        logger.error("Feed fetch timed out")
        raise HTTPException(status_code=408, detail="Feed fetch timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate CSV: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate CSV: {str(e)}")


@router.get("/preview")
async def preview_feed(
    feed_url: str,
    total_budget: float = 50.0,
    target_cpc: float = 0.50,
    body_template: str = "{title} For Sale",
    link_description: str = "Prices range from $2.25-$5.00 per plant",
    credentials=Depends(verify_credentials)
):
    """
    Preview products from Google Shopping feed.

    Args:
        feed_url: URL to Google Shopping TSV feed
        total_budget: Total daily budget (default: $50)
        target_cpc: Target cost per click for bid amount (default: $0.50)
        body_template: Template for body text, use {title} as placeholder (default: "{title} For Sale")
        link_description: Link description for all ads (default: "Prices range from $2.25-$5.00 per plant")

    Returns:
        Preview of products that will be included
    """
    logger.info(f"preview_feed called: feed_url={feed_url}, total_budget={total_budget}, target_cpc={target_cpc}, user={credentials}")

    try:
        # Fetch and parse feed
        products = await fetch_and_parse_feed(feed_url)

        if not products:
            raise HTTPException(status_code=400, detail="No products found in feed")

        # Budget per product
        budget_per_product = round(total_budget / len(products), 2) if products else 1.0
        budget_per_product = max(budget_per_product, 1.0)
        logger.info(f"Preview: {len(products)} products, ${budget_per_product}/day per product")

        # Build preview
        preview_data = []
        for product in products[:100]:  # Limit preview to 100
            title = product.get('title', 'N/A')
            product_name = extract_product_name(title)
            body_text = body_template.replace('{title}', product_name)

            preview_data.append({
                'title': title,
                'link': strip_utm_params(product.get('link', 'N/A')),
                'price': product.get('price', 'N/A'),
                'ad_set_budget': budget_per_product,
                'bid_amount': target_cpc,
                'body_text': body_text,
                'link_description': link_description
            })

        logger.info(f"Returning preview with {len(preview_data)} products")

        return {
            'success': True,
            'total_products': len(products),
            'total_daily_budget': total_budget,
            'budget_per_product': budget_per_product,
            'products': preview_data
        }

    except httpx.TimeoutException:
        logger.error("Feed fetch timed out")
        raise HTTPException(status_code=408, detail="Feed fetch timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview feed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to preview feed: {str(e)}")


class ImageUploadStatus(BaseModel):
    """Status of image upload job."""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    total_images: int
    uploaded_images: int
    failed_images: int
    progress_percent: float


async def upload_images_background(feed_url: str, job_id: str):
    """Background task to upload product images to Meta."""
    try:
        # Update status to processing
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:status", "processing")

        # Get Meta credentials
        access_token = SettingsDatabase.get_setting("meta_access_token")
        ad_account_id = SettingsDatabase.get_setting("meta_ad_account_id")

        if not access_token or not ad_account_id:
            logger.error("Meta credentials not configured")
            SettingsDatabase.set_setting(f"image_upload_job:{job_id}:status", "failed")
            SettingsDatabase.set_setting(f"image_upload_job:{job_id}:error", "Meta credentials not configured")
            return

        # Fetch products from feed
        products = await fetch_and_parse_feed(feed_url)

        if not products:
            logger.error("No products found in feed")
            SettingsDatabase.set_setting(f"image_upload_job:{job_id}:status", "failed")
            SettingsDatabase.set_setting(f"image_upload_job:{job_id}:error", "No products found")
            return

        # Count all images (main image + additional images per product)
        all_image_urls = []
        for product in products:
            # Main image
            image_url = product.get('image_link', '')
            if image_url:
                all_image_urls.append(image_url)

            # Additional images
            additional_image_link = product.get('additional_image_link', '')
            if additional_image_link:
                additional_images = [url.strip() for url in additional_image_link.split(',') if url.strip()]
                all_image_urls.extend(additional_images[:9])  # Max 9 additional images

        total_images = len(all_image_urls)
        uploaded_count = 0
        failed_count = 0
        error_summary = {"exceptions": [], "api_failures": 0}

        # Log sample image URLs for debugging
        sample_urls = all_image_urls[:3]
        logger.info(f"Sample image URLs (first 3): {sample_urls}")
        logger.info(f"Starting upload of {total_images} images (including additional images) with account: {ad_account_id}")

        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:total", str(total_images))
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:uploaded", "0")
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:failed", "0")

        # Upload images in batches to avoid rate limits
        batch_size = 10
        for i in range(0, len(all_image_urls), batch_size):
            batch_urls = all_image_urls[i:i + batch_size]

            # Upload batch concurrently
            tasks = []
            for image_url in batch_urls:
                tasks.append(
                    MetaImageUploadService.get_or_upload_image(
                        image_url, access_token, ad_account_id
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successes and failures
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_count += 1
                    error_type = f"{type(result).__name__}: {str(result)}"
                    logger.error(f"Image upload failed with exception: {error_type}")
                    if error_type not in error_summary["exceptions"]:
                        error_summary["exceptions"].append(error_type)
                elif result is None:
                    failed_count += 1
                    error_summary["api_failures"] += 1
                    logger.warning(f"Image upload returned None (likely API error or download failure)")
                else:
                    uploaded_count += 1
                    logger.debug(f"Image uploaded successfully, hash: {result}")

            # Update progress
            SettingsDatabase.set_setting(f"image_upload_job:{job_id}:uploaded", str(uploaded_count))
            SettingsDatabase.set_setting(f"image_upload_job:{job_id}:failed", str(failed_count))

            logger.info(f"Batch complete: {uploaded_count}/{total_images} uploaded, {failed_count} failed")

            # Rate limit: wait between batches
            if i + batch_size < len(all_image_urls):
                await asyncio.sleep(2)

        # Mark as completed
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:status", "completed")
        logger.info(f"Image upload job {job_id} completed: {uploaded_count} uploaded, {failed_count} failed")

        # Log error summary
        if failed_count > 0:
            logger.warning(f"Error summary - API failures (None returned): {error_summary['api_failures']}")
            logger.warning(f"Error summary - Unique exception types: {error_summary['exceptions']}")

    except Exception as e:
        logger.error(f"Image upload job {job_id} failed: {str(e)}", exc_info=True)
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:status", "failed")
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:error", str(e))


@router.post("/upload-images")
async def start_image_upload(
    feed_url: str,
    background_tasks: BackgroundTasks,
    credentials=Depends(verify_credentials)
):
    """
    Start background job to upload product images to Meta.

    Args:
        feed_url: URL to Google Shopping TSV feed
        background_tasks: FastAPI background tasks

    Returns:
        Job ID for tracking upload progress
    """
    logger.info(f"start_image_upload called: feed_url={feed_url}, user={credentials}")

    try:
        import uuid

        logger.debug("Validating Meta credentials...")

        # Validate Meta credentials exist
        access_token = SettingsDatabase.get_setting("meta_access_token")
        ad_account_id = SettingsDatabase.get_setting("meta_ad_account_id")

        logger.debug(f"Meta credentials check: access_token={'exists' if access_token else 'missing'}, ad_account_id={'exists' if ad_account_id else 'missing'}")

        if not access_token or not ad_account_id:
            logger.warning("Meta credentials not configured")
            raise HTTPException(
                status_code=400,
                detail="Meta credentials not configured. Please configure Meta access token and ad account ID in settings."
            )

        job_id = str(uuid.uuid4())
        logger.info(f"Creating image upload job with ID: {job_id}")

        # Initialize job status
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:status", "pending")
        SettingsDatabase.set_setting(f"image_upload_job:{job_id}:feed_url", feed_url)
        logger.debug(f"Initialized job status in database for job {job_id}")

        # Start background task
        background_tasks.add_task(upload_images_background, feed_url, job_id)
        logger.info(f"Started background task for image upload job {job_id}")

        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Image upload job started"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start image upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start image upload: {str(e)}")


@router.get("/upload-status/{job_id}")
async def get_upload_status(
    job_id: str,
    credentials=Depends(verify_credentials)
) -> ImageUploadStatus:
    """
    Get status of an image upload job.

    Args:
        job_id: Job ID from start_image_upload

    Returns:
        Current status of the upload job
    """
    logger.debug(f"get_upload_status called for job_id={job_id}, user={credentials}")

    try:
        status = SettingsDatabase.get_setting(f"image_upload_job:{job_id}:status")

        if not status:
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        total = int(SettingsDatabase.get_setting(f"image_upload_job:{job_id}:total") or "0")
        uploaded = int(SettingsDatabase.get_setting(f"image_upload_job:{job_id}:uploaded") or "0")
        failed = int(SettingsDatabase.get_setting(f"image_upload_job:{job_id}:failed") or "0")

        progress_percent = (uploaded + failed) / total * 100 if total > 0 else 0

        logger.debug(f"Job {job_id} status: {status}, progress: {uploaded + failed}/{total} ({progress_percent:.1f}%)")

        return ImageUploadStatus(
            job_id=job_id,
            status=status,
            total_images=total,
            uploaded_images=uploaded,
            failed_images=failed,
            progress_percent=round(progress_percent, 1)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload status for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get upload status: {str(e)}")
