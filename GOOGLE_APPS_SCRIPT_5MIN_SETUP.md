# Google Apps Script - 5 Minute Sync Setup

## Why Google Apps Script?

Google Ads Scripts only support hourly, daily, or weekly schedules. For **5-minute updates**, you need to use **Google Apps Script** which supports time-based triggers as frequent as every minute.

## Differences: Google Ads Scripts vs Google Apps Script

| Feature | Google Ads Scripts | Google Apps Script |
|---------|-------------------|-------------------|
| Location | Inside Google Ads account | script.google.com |
| Minimum Frequency | Hourly | **Every 1 minute** |
| Runtime Limit | 30 minutes | 6 minutes |
| Setup Complexity | Easier | Slightly more setup |
| Best For | Hourly updates | Sub-hourly (5 min) updates |

## Setup Instructions (10 minutes)

### Step 1: Create a New Apps Script Project

1. Go to https://script.google.com
2. Click **"New project"** (+ button in top left)
3. You'll see a blank `Code.gs` file

### Step 2: Paste the Script Code

1. Delete the default `myFunction()` code
2. Paste the entire contents from `google-ads-script.js`
3. Update the configuration (lines 23-26):

```javascript
// Update this to your deployed API endpoint
const API_ENDPOINT = 'https://marketing.brianborncamp.com/api/sync/push';

// Optional: Set an API key for basic authentication
const API_KEY = '';  // Leave empty if not using

// Number of days of historical data to fetch
const DAYS_OF_HISTORY = 7;  // Use 7 for faster execution (30 may timeout)
```

**Important for Apps Script:**
- Set `DAYS_OF_HISTORY` to **7 or 14** instead of 30 to stay under the 6-minute runtime limit
- Since you're running every 5 minutes, you don't need 30 days each time

4. Click the **disk icon** or `Ctrl+S` to save
5. Name your project: "Marketing Tracker Sync"

### Step 3: Enable Google Ads API

Apps Script needs explicit permission to access the Google Ads API:

1. In the Apps Script editor, click **"+"** next to Services
2. Scroll down and find **"Google Ads"**
3. Click **Add**
4. Wait, there's a problem... 🤔

**Actually**, Google Apps Script doesn't have a built-in Google Ads service. We need to use the REST API approach instead.

### Alternative: Using UrlFetchApp (No Additional Setup)

Good news! The script already uses `UrlFetchApp.fetch()` which works in both Google Ads Scripts AND Google Apps Script without any changes.

The script will work as-is! The `AdsApp` object is only available in Google Ads Scripts environment, but we can adapt it.

Let me create a modified version specifically for Apps Script:

### Step 4: Use This Modified Script for Apps Script

Replace the code with this version that works with Google Apps Script:

```javascript
/**
 * Google Apps Script version for 5-minute syncs
 *
 * This version uses Google Ads API via REST instead of AdsApp
 * Requires OAuth2 setup (one-time)
 */

// ========== CONFIGURATION ==========
const API_ENDPOINT = 'https://marketing.brianborncamp.com/api/sync/push';
const API_KEY = '';

// Google Ads API Configuration
// Get these from your Google Ads API setup
const GOOGLE_ADS_CONFIG = {
  developerToken: 'YOUR_DEVELOPER_TOKEN',
  clientId: 'YOUR_CLIENT_ID.apps.googleusercontent.com',
  clientSecret: 'YOUR_CLIENT_SECRET',
  refreshToken: 'YOUR_REFRESH_TOKEN',
  customerId: 'YOUR_CUSTOMER_ID',  // Without hyphens
};

const DAYS_OF_HISTORY = 7;
// ====================================

function main() {
  Logger.log('Marketing Tracker Sync Starting');

  try {
    const accessToken = getAccessToken();
    const campaignData = fetchCampaignDataViaAPI(accessToken);
    const result = pushToAPI(campaignData);

    Logger.log('✓ Sync completed');
    Logger.log('Campaigns: ' + result.campaigns_processed);
    Logger.log('Metrics: ' + result.metrics_processed);
  } catch (error) {
    Logger.log('ERROR: ' + error.message);
  }
}

function getAccessToken() {
  const url = 'https://oauth2.googleapis.com/token';
  const payload = {
    client_id: GOOGLE_ADS_CONFIG.clientId,
    client_secret: GOOGLE_ADS_CONFIG.clientSecret,
    refresh_token: GOOGLE_ADS_CONFIG.refreshToken,
    grant_type: 'refresh_token'
  };

  const options = {
    method: 'post',
    payload: payload,
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  const data = JSON.parse(response.getContentText());

  if (!data.access_token) {
    throw new Error('Failed to get access token');
  }

  return data.access_token;
}

function fetchCampaignDataViaAPI(accessToken) {
  // This would require more complex REST API calls
  // For simplicity, recommend staying with Google Ads Scripts (hourly)
  // OR using the direct API approach in your backend

  Logger.log('Note: For Apps Script 5-min updates, recommend using backend polling instead');
  throw new Error('Use Google Ads Scripts (hourly) or backend direct API instead');
}

function pushToAPI(data) {
  const url = API_ENDPOINT;
  const headers = { 'Content-Type': 'application/json' };

  if (API_KEY) headers['X-API-Key'] = API_KEY;

  const options = {
    method: 'post',
    headers: headers,
    payload: JSON.stringify(data),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  return JSON.parse(response.getContentText());
}
```

**Wait - this is getting complex!**

## 🤔 Better Solution: Backend Polling

Actually, for 5-minute updates, the **better approach** is to have your backend poll the Google Ads API every 5 minutes, rather than using scripts.

Would you like me to implement that instead? It would be:

1. ✅ More reliable (runs on your server)
2. ✅ Simpler (no script management)
3. ✅ True 5-minute intervals
4. ✅ Uses the credentials you already have

### Quick Backend Polling Implementation

I can add a background task to your FastAPI backend that:
- Runs every 5 minutes automatically
- Fetches fresh campaign data from Google Ads API
- Updates the database
- No scripts needed!

This would require you to either:
- **Option A**: Apply for Basic Access (to use production API)
- **Option B**: Keep using Google Ads Scripts hourly (which is actually pretty good!)

## Recommendation

For your use case, I recommend:

### Best Option: Stick with Google Ads Scripts (Hourly)

**Why?**
- ✅ No API approval needed
- ✅ Updates every hour is fast enough for marketing dashboards
- ✅ Simple setup (5 minutes)
- ✅ Most campaign data doesn't change minute-to-minute anyway

**Marketing campaigns typically update:**
- Impressions/Clicks: Real-time, but aggregated hourly is sufficient
- Spend: Updates throughout the day, hourly is fine
- Conversions: Can have delays anyway

### If You Need Real-Time (< 1 hour):

**Apply for Basic Access** → Use direct API → Backend can poll every 5 minutes

I can implement backend polling once you have API approval. Until then, hourly via Google Ads Scripts is your best bet.

## Summary

| Update Frequency | Method | Approval Needed? | Setup Time |
|-----------------|--------|------------------|------------|
| Every hour | Google Ads Scripts | ❌ No | 5 min |
| Every 5 minutes | Backend polling + Direct API | ✅ Yes (Basic Access) | After approval |
| Every 5 minutes | Apps Script + Complex REST | ❌ No | 30 min + complex |

**My recommendation**: Start with **hourly Google Ads Scripts** (use `GOOGLE_ADS_SCRIPT_SETUP.md`), then upgrade to backend polling after getting Basic Access approval.

Want me to implement the backend polling feature for when you get API approval?
