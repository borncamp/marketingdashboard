/**
 * Google Ads Script to export campaign data to Marketing Tracker API
 *
 * SETUP INSTRUCTIONS:
 * 1. Go to your Google Ads account: https://ads.google.com
 * 2. Click Tools & Settings → Bulk Actions → Scripts
 * 3. Click the "+" button to create a new script
 * 4. Paste this entire code
 * 5. Update the API_BASE_URL constant below with your domain
 * 6. Optional: Set API_KEY if you want authentication
 * 7. Click "Preview" to test, then "Save"
 * 8. Schedule to run every hour or daily
 *
 * The script fetches its configuration from your server at runtime,
 * so you can change settings without updating the script.
 *
 * This script will:
 * - Fetch all active campaigns
 * - Get metrics for the last 30 days
 * - Push data to your API endpoint
 * - No Google Ads API developer token needed!
 */

// ========== CONFIGURATION ==========
// Update this to your deployed domain
const API_BASE_URL = 'https://marketing.brianborncamp.com';

// Optional: Set an API key for basic authentication
const API_KEY = '';  // Leave empty if not using authentication

// ====================================
// Runtime config (fetched from server)
let CONFIG = null;


/**
 * Fetch runtime configuration from the server
 */
function fetchConfig() {
  try {
    const url = API_BASE_URL + '/api/script-config';
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      muteHttpExceptions: true
    });

    if (response.getResponseCode() === 200) {
      CONFIG = JSON.parse(response.getContentText());
      Logger.log('✓ Loaded config version: ' + CONFIG.version);
      Logger.log('  Days of history: ' + CONFIG.days_of_history);
      Logger.log('  Campaign status filter: ' + CONFIG.campaign_filters.status);
      Logger.log('  Require impressions: ' + CONFIG.campaign_filters.require_impressions);
      return true;
    } else {
      Logger.log('⚠ Could not fetch config from server, using defaults');
      // Fallback defaults
      CONFIG = {
        days_of_history: 30,
        product_days_of_history: 7,
        campaign_filters: { status: 'ENABLED', require_impressions: true },
        metrics: ['cost_micros', 'clicks', 'impressions', 'ctr', 'conversions', 'conversions_value'],
        query_settings: { include_today: true },
        endpoints: { push_campaigns: '/api/sync/push', push_products: '/api/sync/push-products' }
      };
      return false;
    }
  } catch (e) {
    Logger.log('⚠ Error fetching config: ' + e.message + ', using defaults');
    CONFIG = {
      days_of_history: 30,
      product_days_of_history: 7,
      campaign_filters: { status: 'ENABLED', require_impressions: true },
      metrics: ['cost_micros', 'clicks', 'impressions', 'ctr', 'conversions', 'conversions_value'],
      query_settings: { include_today: true },
      endpoints: { push_campaigns: '/api/sync/push', push_products: '/api/sync/push-products' }
    };
    return false;
  }
}


/**
 * Main function - this is called when the script runs
 */
function main() {
  Logger.log('========================================');
  Logger.log('Marketing Tracker Sync Script Starting');
  Logger.log('========================================');

  try {
    // Fetch configuration from server
    fetchConfig();

    // Fetch campaign data
    const campaignData = fetchCampaignData();

    Logger.log('Fetched ' + campaignData.campaigns.length + ' campaigns');

    // Push to API
    const result = pushToAPI(campaignData);

    Logger.log('✓ Sync completed successfully');
    Logger.log('Campaigns processed: ' + result.campaigns_processed);
    Logger.log('Metrics processed: ' + result.metrics_processed);

    // Fetch and push Shopping product data
    try {
      const productData = fetchShoppingProductData();

      if (productData.products.length > 0) {
        Logger.log('Fetched ' + productData.products.length + ' Shopping products');
        const productResult = pushProductDataToAPI(productData);
        Logger.log('✓ Product sync completed');
        Logger.log('Products processed: ' + productResult.products_processed);
      } else {
        Logger.log('No Shopping campaign data available');
      }
    } catch (productError) {
      Logger.log('Note: Product data sync skipped - ' + productError.message);
    }

  } catch (error) {
    Logger.log('✗ ERROR: ' + error.message);
    Logger.log(error.stack);
  }
}


/**
 * Fetch campaign data with metrics from Google Ads
 */
function fetchCampaignData() {
  const campaigns = {};
  const dateRange = getDateRange(CONFIG.days_of_history);

  Logger.log('Fetching campaign list and metrics...');

  // Build metrics list dynamically from CONFIG
  const metricsToFetch = CONFIG.metrics || ['cost_micros', 'clicks', 'impressions', 'ctr', 'conversions'];
  const metricsFields = metricsToFetch.map(m => 'metrics.' + m).join(',\n      ');

  // First query: Get all campaigns with historical data
  const historicalQuery = `
    SELECT
      campaign.id,
      campaign.name,
      campaign.status,
      segments.date,
      ${metricsFields}
    FROM campaign
    WHERE campaign.status != REMOVED
      AND segments.date DURING ${dateRange}
    ORDER BY campaign.id, segments.date ASC
  `;

  const report = AdsApp.report(historicalQuery);
  const rows = report.rows();

  while (rows.hasNext()) {
    const row = rows.next();
    const campaignId = row['campaign.id'];
    const campaignName = row['campaign.name'];
    const campaignStatus = row['campaign.status'];
    const date = row['segments.date'];

    // Initialize campaign if not exists
    if (!campaigns[campaignId]) {
      campaigns[campaignId] = {
        id: campaignId,
        name: campaignName,
        status: campaignStatus,
        platform: 'google_ads',
        metrics: []
      };
      Logger.log('  - ' + campaignName + ' (' + campaignStatus + ')');
    }

    // Parse metrics dynamically
    parseAndAddMetrics(row, date, campaigns[campaignId].metrics);
  }

  // Second query: Get TODAY's data for real-time updates
  if (CONFIG.query_settings && CONFIG.query_settings.include_today) {
    try {
      const todayQuery = `
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          segments.date,
          ${metricsFields}
        FROM campaign
        WHERE campaign.status != REMOVED
          AND segments.date DURING TODAY
        ORDER BY campaign.id, segments.date ASC
      `;

      const todayReport = AdsApp.report(todayQuery);
      const todayRows = todayReport.rows();

      while (todayRows.hasNext()) {
        const row = todayRows.next();
        const campaignId = row['campaign.id'];
        const campaignName = row['campaign.name'];
        const campaignStatus = row['campaign.status'];
        const date = row['segments.date'];

        // Initialize campaign if not exists (in case it's a new campaign today)
        if (!campaigns[campaignId]) {
          campaigns[campaignId] = {
            id: campaignId,
            name: campaignName,
            status: campaignStatus,
            platform: 'google_ads',
            metrics: []
          };
        }

        // Parse metrics dynamically
        parseAndAddMetrics(row, date, campaigns[campaignId].metrics);
      }

      Logger.log('✓ Included today\'s real-time data');
    } catch (e) {
      Logger.log('Note: No data available for today yet');
    }
  }

  // Convert to array
  const campaignArray = Object.values(campaigns);
  Logger.log('Total campaigns processed: ' + campaignArray.length);

  return {
    campaigns: campaignArray,
    source: 'google_ads_script'
  };
}


/**
 * Parse metrics from a row and add to metrics array
 * Dynamically handles metrics based on CONFIG.metrics
 */
function parseAndAddMetrics(row, date, metricsArray) {
  const metricsConfig = CONFIG.metrics || ['cost_micros', 'clicks', 'impressions', 'ctr', 'conversions'];

  metricsConfig.forEach(function(metricName) {
    const fieldName = 'metrics.' + metricName;
    const rawValue = row[fieldName];

    if (rawValue === undefined || rawValue === null) {
      return;  // Skip if metric not available
    }

    // Parse value and determine name/unit
    let value, name, unit;

    if (metricName === 'cost_micros') {
      value = parseInt(rawValue) / 1000000;
      name = 'spend';
      unit = 'USD';
    } else if (metricName === 'ctr') {
      value = parseFloat(rawValue) * 100;
      name = 'ctr';
      unit = '%';
    } else if (metricName === 'conversions_value') {
      value = parseFloat(rawValue);
      name = 'conversion_value';
      unit = 'USD';
    } else if (metricName.includes('micros')) {
      value = parseInt(rawValue) / 1000000;
      name = metricName.replace('_micros', '');
      unit = 'USD';
    } else if (metricName.includes('rate') || metricName.includes('ctr')) {
      value = parseFloat(rawValue) * 100;
      name = metricName;
      unit = '%';
    } else {
      value = parseFloat(rawValue) || parseInt(rawValue) || 0;
      name = metricName;
      unit = 'count';
    }

    metricsArray.push({
      date: date,
      name: name,
      value: value,
      unit: unit
    });
  });
}


/**
 * Fetch Shopping product performance data
 */
function fetchShoppingProductData() {
  const products = {};
  const productDays = CONFIG.product_days_of_history || CONFIG.days_of_history;
  const dateRange = getDateRange(productDays);

  Logger.log('Fetching Shopping product performance data (last ' + productDays + ' days)...');

  // Step 1: Get currently enabled product item IDs from product groups
  Logger.log('Step 1: Finding currently enabled product item IDs in ad groups...');
  const enabledProducts = {};  // Map of campaign_id|product_id -> true

  const productGroupQuery = `
    SELECT
      campaign.id,
      ad_group.id,
      ad_group_criterion.listing_group.case_value.product_item_id.value,
      ad_group_criterion.status
    FROM ad_group_criterion
    WHERE campaign.status = 'ENABLED'
      AND ad_group.status = 'ENABLED'
      AND ad_group_criterion.type = 'LISTING_GROUP'
      AND ad_group_criterion.status = 'ENABLED'
      AND ad_group_criterion.listing_group.type = 'UNIT'
  `;

  try {
    const pgReport = AdsApp.report(productGroupQuery);
    const pgRows = pgReport.rows();

    let rowCount = 0;
    let nullCount = 0;

    while (pgRows.hasNext()) {
      const row = pgRows.next();
      rowCount++;
      const campaignId = row['campaign.id'];
      const adGroupId = row['ad_group.id'];
      const productItemId = row['ad_group_criterion.listing_group.case_value.product_item_id.value'];

      if (productItemId && productItemId.trim() !== '') {
        const key = campaignId + '|' + productItemId;
        enabledProducts[key] = {
          enabled: true,
          adGroupId: adGroupId
        };
      } else {
        nullCount++;
      }
    }

    Logger.log('Product group query returned ' + rowCount + ' rows (' + nullCount + ' with null product_item_id)');
    Logger.log('Found ' + Object.keys(enabledProducts).length + ' unique enabled product item IDs');

    if (Object.keys(enabledProducts).length === 0) {
      Logger.log('WARNING: No enabled products found! Falling back to include all products.');
    }
  } catch (e) {
    Logger.log('ERROR fetching product groups: ' + e.message);
    Logger.log('Stack: ' + e.stack);
    Logger.log('Falling back to performance-only data (all products will be included)');
  }

  // Step 2: Get performance data for the date range
  Logger.log('Step 2: Fetching performance metrics...');

  // Build metrics list dynamically from CONFIG
  const metricsToFetch = CONFIG.metrics || ['cost_micros', 'clicks', 'impressions', 'ctr', 'conversions', 'conversions_value'];
  const metricsFields = metricsToFetch.map(m => 'metrics.' + m).join(',\n      ');

  const performanceQuery = `
    SELECT
      campaign.id,
      campaign.name,
      campaign.status,
      segments.product_item_id,
      segments.product_title,
      segments.date,
      ${metricsFields}
    FROM shopping_performance_view
    WHERE campaign.status = 'ENABLED'
      AND segments.date DURING ${dateRange}
    ORDER BY segments.product_item_id, segments.date ASC
  `;

  const report = AdsApp.report(performanceQuery);
  const rows = report.rows();

  while (rows.hasNext()) {
    const row = rows.next();
    const campaignId = row['campaign.id'];
    const campaignName = row['campaign.name'];
    const productId = row['segments.product_item_id'];
    const productTitle = row['segments.product_title'];
    const date = row['segments.date'];

    // Create unique key for product-campaign combination
    const productCampaignKey = campaignId + '|' + productId;

    // FILTER: Only include if this product is currently enabled in the campaign's product groups
    if (Object.keys(enabledProducts).length > 0 && !enabledProducts[productCampaignKey]) {
      continue;  // Skip products that are not currently enabled
    }

    // Initialize product-campaign combination if not exists
    if (!products[productCampaignKey]) {
      const adGroupId = enabledProducts[productCampaignKey] ? enabledProducts[productCampaignKey].adGroupId : null;
      products[productCampaignKey] = {
        product_id: productId,
        product_title: productTitle,
        campaign_id: campaignId,
        campaign_name: campaignName,
        ad_group_id: adGroupId,
        metrics: []
      };
    }

    // Parse metrics dynamically
    parseAndAddMetrics(row, date, products[productCampaignKey].metrics);
  }

  // Query TODAY's data for real-time updates
  if (CONFIG.query_settings && CONFIG.query_settings.include_today) {
    try {
      Logger.log('Step 3: Fetching today\'s data...');

      const todayQuery = `
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          segments.product_item_id,
          segments.product_title,
          segments.date,
          ${metricsFields}
        FROM shopping_performance_view
        WHERE campaign.status = 'ENABLED'
          AND segments.date DURING TODAY
        ORDER BY segments.product_item_id, segments.date ASC
      `;

      const todayReport = AdsApp.report(todayQuery);
      const todayRows = todayReport.rows();

      while (todayRows.hasNext()) {
        const row = todayRows.next();
        const campaignId = row['campaign.id'];
        const campaignName = row['campaign.name'];
        const productId = row['segments.product_item_id'];
        const productTitle = row['segments.product_title'];
        const date = row['segments.date'];

        // Create unique key for product-campaign combination
        const productCampaignKey = campaignId + '|' + productId;

        // FILTER: Only include if this product is currently enabled in the campaign's product groups
        if (Object.keys(enabledProducts).length > 0 && !enabledProducts[productCampaignKey]) {
          continue;  // Skip products that are not currently enabled
        }

        // Initialize product-campaign combination if not exists
        if (!products[productCampaignKey]) {
          const adGroupId = enabledProducts[productCampaignKey] ? enabledProducts[productCampaignKey].adGroupId : null;
          products[productCampaignKey] = {
            product_id: productId,
            product_title: productTitle,
            campaign_id: campaignId,
            campaign_name: campaignName,
            ad_group_id: adGroupId,
            metrics: []
          };
        }

        // Parse metrics dynamically
        parseAndAddMetrics(row, date, products[productCampaignKey].metrics);
      }

      Logger.log('✓ Included today\'s product data');
    } catch (e) {
      Logger.log('Note: No product data available for today yet');
    }
  }

  const productArray = Object.values(products);
  Logger.log('Total products processed: ' + productArray.length);

  return {
    products: productArray,
    source: 'google_ads_script'
  };
}


/**
 * Get date range string for GAQL query
 */
function getDateRange(days) {
  if (days === 7) return 'LAST_7_DAYS';
  if (days === 14) return 'LAST_14_DAYS';
  if (days === 30) return 'LAST_30_DAYS';

  // Custom date range
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - days);

  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
  };

  return formatDate(startDate) + ',' + formatDate(today);
}


/**
 * Push data to the API endpoint
 */
function pushToAPI(data) {
  const url = API_BASE_URL + CONFIG.endpoints.push_campaigns;

  const headers = {
    'Content-Type': 'application/json'
  };

  // Add API key if configured
  if (API_KEY && API_KEY.length > 0) {
    headers['X-API-Key'] = API_KEY;
  }

  const options = {
    method: 'post',
    headers: headers,
    payload: JSON.stringify(data),
    muteHttpExceptions: true
  };

  Logger.log('Pushing data to API: ' + url);

  const response = UrlFetchApp.fetch(url, options);
  const responseCode = response.getResponseCode();
  const responseBody = response.getContentText();

  Logger.log('API Response Code: ' + responseCode);

  if (responseCode !== 200) {
    throw new Error('API returned error: ' + responseCode + ' - ' + responseBody);
  }

  const result = JSON.parse(responseBody);

  if (!result.success) {
    throw new Error('API indicated failure: ' + responseBody);
  }

  return result;
}


/**
 * Push product data to the API endpoint
 */
function pushProductDataToAPI(data) {
  // Use the products endpoint from config
  const url = API_BASE_URL + CONFIG.endpoints.push_products;

  const headers = {
    'Content-Type': 'application/json'
  };

  // Add API key if configured
  if (API_KEY && API_KEY.length > 0) {
    headers['X-API-Key'] = API_KEY;
  }

  const options = {
    method: 'post',
    headers: headers,
    payload: JSON.stringify(data),
    muteHttpExceptions: true
  };

  Logger.log('Pushing product data to API: ' + url);

  const response = UrlFetchApp.fetch(url, options);
  const responseCode = response.getResponseCode();
  const responseBody = response.getContentText();

  Logger.log('API Response Code: ' + responseCode);

  if (responseCode !== 200) {
    throw new Error('API returned error: ' + responseCode + ' - ' + responseBody);
  }

  const result = JSON.parse(responseBody);

  if (!result.success) {
    throw new Error('API indicated failure: ' + responseBody);
  }

  return result;
}


/**
 * Test function to preview data without pushing to API
 * Run this from "Preview" to see what data would be sent
 */
function testPreview() {
  Logger.log('========================================');
  Logger.log('TEST PREVIEW MODE');
  Logger.log('========================================');

  const data = fetchCampaignData();

  Logger.log('\n' + 'Data that would be sent to API:');
  Logger.log(JSON.stringify(data, null, 2));

  Logger.log('\n' + 'Total campaigns: ' + data.campaigns.length);

  let totalMetrics = 0;
  for (let i = 0; i < data.campaigns.length; i++) {
    totalMetrics += data.campaigns[i].metrics.length;
  }
  Logger.log('Total metric data points: ' + totalMetrics);

  Logger.log('\n' + '✓ Preview completed');
  Logger.log('To actually push data, run the "main" function');
}
