import { useState, useEffect } from 'react';

interface SetupInstructionsProps {
  onComplete: () => void;
}

export default function SetupInstructions({ onComplete }: SetupInstructionsProps) {
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [checking, setChecking] = useState(false);

  const checkForData = async () => {
    setChecking(true);
    try {
      const response = await fetch('/api/sync/status');
      const data = await response.json();
      setSyncStatus(data);

      if (data.has_data) {
        // Data is available! Redirect to dashboard
        setTimeout(() => onComplete(), 1000);
      }
    } catch (error) {
      console.error('Failed to check sync status:', error);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkForData();
    // Check every 10 seconds for new data
    const interval = setInterval(checkForData, 10000);
    return () => clearInterval(interval);
  }, []);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Welcome to Marketing Campaign Tracker!
          </h1>
          <p className="text-xl text-gray-600">
            Let's get your campaign data flowing
          </p>
        </div>

        {/* Status Card */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {syncStatus?.has_data ? (
                <>
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-green-700 font-semibold">Data Connected!</span>
                </>
              ) : (
                <>
                  <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></div>
                  <span className="text-yellow-700 font-semibold">Waiting for first data sync...</span>
                </>
              )}
            </div>
            <button
              onClick={checkForData}
              disabled={checking}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm"
            >
              {checking ? 'Checking...' : 'Check Now'}
            </button>
          </div>
        </div>

        {/* Setup Options */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Choose Your Setup Method
          </h2>

          {/* Option 1: Google Ads Scripts (Recommended) */}
          <div className="border-2 border-blue-500 rounded-lg p-6 mb-6 bg-blue-50">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-blue-900 mb-2">
                  ⚡ Option 1: Google Ads Scripts (Recommended)
                </h3>
                <div className="flex items-center space-x-2 mb-3">
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">
                    NO APPROVAL NEEDED
                  </span>
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-semibold">
                    5 MINUTES SETUP
                  </span>
                </div>
                <p className="text-gray-700 mb-4">
                  Run a script inside your Google Ads account that automatically sends data to this dashboard every hour.
                </p>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 mb-4">
              <h4 className="font-semibold text-gray-900 mb-3">Quick Setup Steps:</h4>
              <ol className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start">
                  <span className="font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2 text-xs flex-shrink-0">1</span>
                  <span>Go to your <a href="https://ads.google.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline font-semibold">Google Ads account</a></span>
                </li>
                <li className="flex items-start">
                  <span className="font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2 text-xs flex-shrink-0">2</span>
                  <span>Click <strong>Tools & Settings</strong> → <strong>Bulk Actions</strong> → <strong>Scripts</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2 text-xs flex-shrink-0">3</span>
                  <span>Click the <strong>+</strong> button to create a new script</span>
                </li>
                <li className="flex items-start">
                  <span className="font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2 text-xs flex-shrink-0">4</span>
                  <span>Copy the script code below and paste it into the editor</span>
                </li>
                <li className="flex items-start">
                  <span className="font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2 text-xs flex-shrink-0">5</span>
                  <span>Update line 23 with your API endpoint (already filled below)</span>
                </li>
                <li className="flex items-start">
                  <span className="font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2 text-xs flex-shrink-0">6</span>
                  <span>Click <strong>Preview</strong> → select <strong>main</strong> → click <strong>Run</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2 text-xs flex-shrink-0">7</span>
                  <span>Once successful, click <strong>Create Schedule</strong> → <strong>Hourly</strong></span>
                </li>
              </ol>
            </div>

            <div className="bg-gray-900 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-xs font-mono">google-ads-script.js</span>
                <button
                  onClick={() => copyToClipboard(getScriptCode())}
                  className="px-3 py-1 bg-gray-700 text-white rounded text-xs hover:bg-gray-600 transition-colors"
                >
                  📋 Copy Script
                </button>
              </div>
              <div className="bg-gray-800 rounded p-3 overflow-x-auto">
                <pre className="text-green-400 text-xs font-mono">
{`// Line 23: Update this line with your domain
const API_ENDPOINT = '${window.location.origin}/api/sync/push';

// The rest of the script is ready to use!
// Full script available at:
// ${window.location.origin}/google-ads-script.js`}
                </pre>
              </div>
            </div>

            <div className="flex space-x-3">
              <a
                href="https://ads.google.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold text-center"
              >
                Open Google Ads →
              </a>
              <a
                href="/google-ads-script.js"
                download
                className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors font-semibold"
              >
                Download Full Script
              </a>
            </div>
          </div>

          {/* Option 2: Direct API */}
          <div className="border-2 border-gray-300 rounded-lg p-6 bg-gray-50">
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              🔧 Option 2: Direct Google Ads API
            </h3>
            <div className="flex items-center space-x-2 mb-3">
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-semibold">
                REQUIRES APPROVAL (24-48hrs)
              </span>
              <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-semibold">
                REAL-TIME DATA
              </span>
            </div>
            <p className="text-gray-700 mb-4">
              For real-time updates, you'll need to apply for Google Ads API Basic Access and complete the onboarding wizard.
            </p>
            <div className="flex space-x-3">
              <a
                href="https://ads.google.com/aw/apicenter"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm font-semibold"
              >
                Apply for API Access
              </a>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors text-sm font-semibold"
              >
                Start Onboarding Wizard
              </button>
            </div>
          </div>
        </div>

        {/* Help Section */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-3">
            Need Help?
          </h3>
          <div className="space-y-2 text-sm text-gray-700">
            <p>
              📚 <a href="https://github.com/yourusername/marketing-tracker" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                Full Setup Guide
              </a> - Complete documentation with screenshots
            </p>
            <p>
              💬 Having issues? The script logs will show any errors. Check the "Logs" tab in Google Ads Scripts.
            </p>
            <p>
              ⏱️ After running the script once, this page will automatically detect your data and load the dashboard.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function getScriptCode(): string {
  // Load the actual full script content
  return `/**
 * Google Ads Script to export campaign data to Marketing Tracker API
 *
 * IMPORTANT: Update the API_ENDPOINT on line 23 with your domain
 */

// ========== CONFIGURATION ==========
const API_ENDPOINT = '${window.location.origin}/api/sync/push';
const API_KEY = '';  // Optional: Add API key for authentication
const DAYS_OF_HISTORY = 30;
// ====================================

function main() {
  Logger.log('========================================');
  Logger.log('Marketing Tracker Sync Script Starting');
  Logger.log('========================================');

  try {
    const campaignData = fetchCampaignData();
    Logger.log('Fetched ' + campaignData.campaigns.length + ' campaigns');

    const result = pushToAPI(campaignData);
    Logger.log('✓ Sync completed successfully');
    Logger.log('Campaigns processed: ' + result.campaigns_processed);
    Logger.log('Metrics processed: ' + result.metrics_processed);
  } catch (error) {
    Logger.log('✗ ERROR: ' + error.message);
    Logger.log(error.stack);
  }
}

function fetchCampaignData() {
  const campaigns = [];
  const dateRange = getDateRange(DAYS_OF_HISTORY);
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

function fetchCampaignMetrics(campaignId, dateRange) {
  const metrics = [];
  const query = \`
    SELECT
      campaign.id,
      segments.date,
      metrics.cost_micros,
      metrics.clicks,
      metrics.impressions,
      metrics.ctr,
      metrics.conversions
    FROM campaign
    WHERE campaign.id = \$\{campaignId\}
      AND segments.date DURING \$\{dateRange\}
    ORDER BY segments.date ASC
  \`;

  const report = AdsApp.report(query);
  const rows = report.rows();

  while (rows.hasNext()) {
    const row = rows.next();
    const date = row['segments.date'];
    const costMicros = parseInt(row['metrics.cost_micros']) || 0;
    const costDollars = costMicros / 1000000;
    const clicks = parseInt(row['metrics.clicks']) || 0;
    const impressions = parseInt(row['metrics.impressions']) || 0;
    const ctr = parseFloat(row['metrics.ctr']) || 0;
    const conversions = parseFloat(row['metrics.conversions']) || 0;

    metrics.push({ date: date, name: 'spend', value: costDollars, unit: 'USD' });
    metrics.push({ date: date, name: 'clicks', value: clicks, unit: 'count' });
    metrics.push({ date: date, name: 'impressions', value: impressions, unit: 'count' });
    metrics.push({ date: date, name: 'ctr', value: ctr * 100, unit: '%' });
    metrics.push({ date: date, name: 'conversions', value: conversions, unit: 'count' });
  }

  return metrics;
}

function getDateRange(days) {
  if (days === 7) return 'LAST_7_DAYS';
  if (days === 14) return 'LAST_14_DAYS';
  if (days === 30) return 'LAST_30_DAYS';

  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - days);

  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return \`\$\{year\}\$\{month\}\$\{day\}\`;
  };

  return formatDate(startDate) + ',' + formatDate(today);
}

function pushToAPI(data) {
  const url = API_ENDPOINT;
  const headers = { 'Content-Type': 'application/json' };

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

function testPreview() {
  Logger.log('========================================');
  Logger.log('TEST PREVIEW MODE');
  Logger.log('========================================');

  const data = fetchCampaignData();

  Logger.log('\\n' + 'Data that would be sent to API:');
  Logger.log(JSON.stringify(data, null, 2));

  Logger.log('\\n' + 'Total campaigns: ' + data.campaigns.length);

  let totalMetrics = 0;
  for (let i = 0; i < data.campaigns.length; i++) {
    totalMetrics += data.campaigns[i].metrics.length;
  }
  Logger.log('Total metric data points: ' + totalMetrics);

  Logger.log('\\n' + '✓ Preview completed');
  Logger.log('To actually push data, run the "main" function');
}`;
}
