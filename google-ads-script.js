/**
 * Google Ads Script to export campaign data to Marketing Tracker API
 *
 * SETUP INSTRUCTIONS:
 * 1. Go to your Google Ads account: https://ads.google.com
 * 2. Click Tools & Settings → Bulk Actions → Scripts
 * 3. Click the "+" button to create a new script
 * 4. Paste this entire code
 * 5. Update the API_ENDPOINT constant below with your domain
 * 6. Optional: Set API_KEY if you want authentication
 * 7. Click "Preview" to test, then "Save"
 * 8. Schedule to run every hour or daily
 *
 * This script will:
 * - Fetch all active campaigns
 * - Get metrics for the last 30 days
 * - Push data to your API endpoint
 * - No Google Ads API developer token needed!
 */

// ========== CONFIGURATION ==========
// Update this to your deployed API endpoint
const API_ENDPOINT = 'https://marketing.brianborncamp.com/api/sync/push';

// Optional: Set an API key for basic authentication
const API_KEY = '';  // Leave empty if not using authentication

// Number of days of historical data to fetch
const DAYS_OF_HISTORY = 30;

// ====================================


/**
 * Main function - this is called when the script runs
 */
function main() {
  Logger.log('========================================');
  Logger.log('Marketing Tracker Sync Script Starting');
  Logger.log('========================================');

  try {
    // Fetch campaign data
    const campaignData = fetchCampaignData();

    Logger.log('Fetched ' + campaignData.campaigns.length + ' campaigns');

    // Push to API
    const result = pushToAPI(campaignData);

    Logger.log('✓ Sync completed successfully');
    Logger.log('Campaigns processed: ' + result.campaigns_processed);
    Logger.log('Metrics processed: ' + result.metrics_processed);

  } catch (error) {
    Logger.log('✗ ERROR: ' + error.message);
    Logger.log(error.stack);
  }
}


/**
 * Fetch campaign data with metrics from Google Ads
 */
function fetchCampaignData() {
  const campaigns = [];

  // Date range for metrics
  const dateRange = getDateRange(DAYS_OF_HISTORY);

  // Fetch all campaigns (excluding removed ones)
  const campaignIterator = AdsApp.campaigns()
    .withCondition("Status != REMOVED")
    .get();

  Logger.log('Processing campaigns...');

  while (campaignIterator.hasNext()) {
    const campaign = campaignIterator.next();
    const campaignId = campaign.getId().toString();
    const campaignName = campaign.getName();
    const campaignStatus = campaign.getStatus();

    Logger.log('  - ' + campaignName + ' (' + campaignStatus + ')');

    // Fetch metrics for this campaign
    const metrics = fetchCampaignMetrics(campaignId, dateRange);

    campaigns.push({
      id: campaignId,
      name: campaignName,
      status: campaignStatus,
      platform: 'google_ads',
      metrics: metrics
    });
  }

  return {
    campaigns: campaigns,
    source: 'google_ads_script'
  };
}


/**
 * Fetch metrics for a specific campaign
 */
function fetchCampaignMetrics(campaignId, dateRange) {
  const metrics = [];

  // GAQL query to get daily metrics
  const query = `
    SELECT
      campaign.id,
      segments.date,
      metrics.cost_micros,
      metrics.clicks,
      metrics.impressions,
      metrics.ctr,
      metrics.conversions
    FROM campaign
    WHERE campaign.id = ${campaignId}
      AND segments.date DURING ${dateRange}
    ORDER BY segments.date ASC
  `;

  const report = AdsApp.report(query);
  const rows = report.rows();

  while (rows.hasNext()) {
    const row = rows.next();
    const date = row['segments.date'];

    // Cost is in micros (millionths), convert to dollars
    const costMicros = parseInt(row['metrics.cost_micros']) || 0;
    const costDollars = costMicros / 1000000;

    // Parse other metrics
    const clicks = parseInt(row['metrics.clicks']) || 0;
    const impressions = parseInt(row['metrics.impressions']) || 0;
    const ctr = parseFloat(row['metrics.ctr']) || 0;
    const conversions = parseFloat(row['metrics.conversions']) || 0;

    // Add each metric as a separate data point
    metrics.push({ date: date, name: 'spend', value: costDollars, unit: 'USD' });
    metrics.push({ date: date, name: 'clicks', value: clicks, unit: 'count' });
    metrics.push({ date: date, name: 'impressions', value: impressions, unit: 'count' });
    metrics.push({ date: date, name: 'ctr', value: ctr * 100, unit: '%' });  // Convert to percentage
    metrics.push({ date: date, name: 'conversions', value: conversions, unit: 'count' });
  }

  return metrics;
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
  const url = API_ENDPOINT;

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
