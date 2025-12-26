# Google Ads Script Setup Guide

## Why Use Google Ads Scripts Instead of API?

**The Problem:** Google Ads API requires applying for "Basic Access" approval, which can take 24-48 hours and requires submitting design documentation.

**The Solution:** Google Ads Scripts run **inside your Google Ads account** and don't require any developer token approval! This gives you immediate access to your campaign data.

## How It Works

```
┌─────────────────────┐
│  Google Ads Account │
│                     │
│  ┌───────────────┐  │
│  │ Ads Script    │  │ ← Runs every hour (or your schedule)
│  │ (JavaScript)  │  │
│  └───────┬───────┘  │
│          │          │
└──────────┼──────────┘
           │ HTTPS POST
           ▼
    ┌──────────────┐
    │  Your API    │
    │ /api/sync    │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ SQLite DB    │
    │ (Local)      │
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │  Dashboard   │
    │  (React UI)  │
    └──────────────┘
```

## Setup Steps

### Step 1: Access Google Ads Scripts

1. Go to your Google Ads account: https://ads.google.com
2. Click **Tools & Settings** (wrench icon) in the top right
3. Under **Bulk Actions**, click **Scripts**
4. Click the blue **"+"** button to create a new script

### Step 2: Install the Script

1. Open the file `google-ads-script.js` from this repository
2. Copy the entire contents
3. Paste into the Google Ads Script editor
4. Update the `API_ENDPOINT` constant (line 23) to your domain:
   ```javascript
   const API_ENDPOINT = 'https://marketing.brianborncamp.com/api/sync/push';
   ```

### Step 3: Test the Script

1. Click the **"Preview"** button (play icon with magnifying glass)
2. Select the `testPreview` function from the dropdown
3. Click **"Run"**
4. Check the "Logs" tab to see what data would be sent
5. Verify the campaigns and metrics look correct

### Step 4: Run the Script for Real

1. Select the `main` function from the dropdown
2. Click **"Preview"** to test without pushing to API
3. If successful, click **"Run"** to push data to your API
4. Check the logs for:
   ```
   ✓ Sync completed successfully
   Campaigns processed: X
   Metrics processed: Y
   ```

### Step 5: Schedule Automatic Runs

Google Ads Scripts supports these scheduling options:

#### Option A: Every Hour (Recommended)
1. Click **"Create Schedule"** (clock icon)
2. Select **"Hourly"**
3. Choose **"Every hour"**
4. Click **"Save"**

This gives you data updates every hour throughout the day.

#### Option B: Multiple Times Per Hour (Every 15 minutes)
Unfortunately, Google Ads Scripts doesn't support scheduling more frequently than hourly through the UI. However, you can create **4 separate schedules** to run every 15 minutes:

1. Create Schedule #1: Hourly at :00 (12:00, 1:00, 2:00...)
2. Create Schedule #2: Hourly at :15 (12:15, 1:15, 2:15...)
3. Create Schedule #3: Hourly at :30 (12:30, 1:30, 2:30...)
4. Create Schedule #4: Hourly at :45 (12:45, 1:45, 2:45...)

**To create offset schedules:**
- Google Ads Scripts only allows hourly, daily, or weekly
- For sub-hourly updates, use Google Apps Script (see Advanced Setup below)

#### Option C: Daily Updates
1. Click **"Create Schedule"**
2. Select **"Daily"**
3. Choose time (9 AM recommended)
4. Click **"Save"**

Good for low-traffic accounts or daily summary reports.

### Advanced: 5-Minute Updates

For updates more frequent than hourly, you have two options:

#### Option 1: Google Apps Script (Complex)
See detailed guide: [GOOGLE_APPS_SCRIPT_5MIN_SETUP.md](./GOOGLE_APPS_SCRIPT_5MIN_SETUP.md)

**Pros:** No API approval needed
**Cons:** Complex setup with REST API calls

#### Option 2: Backend Polling (Recommended)
Once you have Basic Access approval, your backend can poll the API every 5 minutes automatically.

**Pros:** More reliable, simpler
**Cons:** Requires API approval first

**💡 Reality check:** For marketing dashboards, **hourly updates are usually sufficient**. Campaign metrics don't change dramatically minute-to-minute, and hourly gives you 24 data points per day which is plenty for trend analysis.

## Script Configuration Options

### Change Data History Length

By default, the script fetches 30 days of historical data. To change this:

```javascript
// Line 26
const DAYS_OF_HISTORY = 30;  // Change to 7, 14, or 60
```

### Add API Authentication (Optional)

If you want to protect your sync endpoint with an API key:

```javascript
// Line 29
const API_KEY = 'your-secret-key-here';
```

Then update your backend to verify the key in `backend/app/routers/sync.py`.

## Troubleshooting

### Error: "API returned error: 404"

**Cause:** API endpoint URL is incorrect

**Fix:** Verify the `API_ENDPOINT` constant matches your deployed domain exactly

### Error: "API returned error: 500"

**Cause:** Server error processing the data

**Fix:**
1. Check your server logs: `docker-compose logs backend`
2. Verify the database file permissions
3. Make sure the backend container is running

### Error: "ReferenceError: AdsApp is not defined"

**Cause:** Script is running outside Google Ads environment

**Fix:** Make sure you're running this script **inside Google Ads Scripts**, not locally

### No data appearing in dashboard

**Checks:**
1. Run the script manually and check logs for errors
2. Verify the API endpoint is accessible: `curl https://your-domain.com/api/sync/status`
3. Check that campaigns exist and aren't all REMOVED
4. Look at backend logs for any database errors

### Script times out

**Cause:** Too many campaigns or too much data

**Solutions:**
1. Reduce `DAYS_OF_HISTORY` to fewer days (e.g., 14 or 7)
2. Process campaigns in batches (split into multiple scripts)
3. Run more frequently with shorter history windows

## Metrics Collected

The script automatically collects these metrics for each campaign:

| Metric | Unit | Description |
|--------|------|-------------|
| `spend` | USD | Total advertising spend |
| `clicks` | count | Number of clicks |
| `impressions` | count | Number of ad impressions |
| `ctr` | % | Click-through rate (percentage) |
| `conversions` | count | Number of conversions |

### Adding More Metrics

To collect additional metrics, edit the `fetchCampaignMetrics` function:

```javascript
// Add to the GAQL query (line 101):
SELECT
  campaign.id,
  segments.date,
  metrics.cost_micros,
  metrics.clicks,
  metrics.impressions,
  metrics.ctr,
  metrics.conversions,
  metrics.average_cpc,  // ← Add this
  metrics.conversion_rate  // ← And this

// Then add to the metrics array (after line 124):
const avgCpc = parseInt(row['metrics.average_cpc']) || 0;
const conversionRate = parseFloat(row['metrics.conversion_rate']) || 0;

metrics.push({ date: date, name: 'avg_cpc', value: avgCpc, unit: 'USD' });
metrics.push({ date: date, name: 'conversion_rate', value: conversionRate * 100, unit: '%' });
```

See [Google Ads GAQL Metrics](https://developers.google.com/google-ads/api/fields/v16/metrics) for all available metrics.

## Script Execution Limits

Google Ads Scripts have execution limits:

- **30 minutes maximum runtime** per execution
- **20 hours total** per day across all scripts
- **10 MB** log size limit

For most accounts with under 100 campaigns, this script should complete in under 1 minute.

## Benefits of This Approach

✅ **No API approval needed** - runs immediately
✅ **No developer token required** - works with any Google Ads account
✅ **Scheduled automation** - runs automatically
✅ **Same account access** - uses your existing Google Ads permissions
✅ **Free** - no API quota costs
✅ **Simple setup** - just paste and configure

## Comparison: API vs Script

| Feature | Google Ads API | Google Ads Script |
|---------|----------------|-------------------|
| Approval needed | Yes (24-48hrs) | No |
| Developer token | Required | Not required |
| Setup complexity | High | Low |
| Real-time data | Yes | Near real-time (depends on schedule) |
| Rate limits | Yes (complex) | 30 min per run |
| Cost | Quota-based | Free |
| Best for | Large scale, real-time | Personal dashboards, scheduled reports |

## Next Steps

After setting up the script:

1. Run it manually once to populate initial data
2. Check your dashboard at https://marketing.brianborncamp.com
3. Set up a schedule (hourly recommended)
4. Monitor the "Logs" in Google Ads Scripts for any errors

## Need Help?

- **Google Ads Scripts Documentation**: https://developers.google.com/google-ads/scripts/docs/your-first-script
- **GAQL Reference**: https://developers.google.com/google-ads/api/docs/query/overview
- **Check sync status**: Visit https://marketing.brianborncamp.com/api/sync/status
