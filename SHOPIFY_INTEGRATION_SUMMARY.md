# Shopify Integration - Implementation Summary

## What Was Built

I've successfully integrated Shopify revenue and shipping data into your Marketing Campaign Tracker. The system now calculates **real ROAS** based on actual revenue and total costs (ad spend + shipping).

## New Features

### 1. Backend API Endpoints

**File:** `backend/app/routers/shopify.py`

- `POST /api/shopify/push` - Receives daily aggregated Shopify data
- `GET /api/shopify/metrics?days=7` - Returns aggregated metrics for N days
- `GET /api/shopify/metrics/{metric_name}` - Returns time series data

### 2. Database Schema

**Updated:** `backend/app/database.py`

New table `shopify_daily_metrics`:
- `date` - Date of the metrics
- `revenue` - Total product revenue (excluding shipping)
- `shipping_revenue` - Shipping charges collected from customers
- `shipping_cost` - Actual shipping costs paid
- `order_count` - Number of orders

New class `ShopifyDatabase` with methods:
- `upsert_daily_metrics()` - Store/update daily data
- `get_metrics_summary(days)` - Get aggregated totals
- `get_time_series(metric_name, days)` - Get daily breakdown
- `bulk_upsert_from_orders()` - Bulk insert from export script

### 3. Updated Dashboard Metrics

**Updated:** `frontend/src/components/MetricsSummary.tsx`

The performance overview now shows 5 key metrics:

1. **Ad Spend** - Total Google Ads spend
2. **Revenue** - Total Shopify product revenue
3. **Shipping Cost** - Actual shipping costs paid
4. **ROAS** - Calculated as `Revenue / (Ad Spend + Shipping Cost)`
   - Green (≥2.0x) = Great performance
   - Yellow (1.0-2.0x) = Okay performance
   - Red (<1.0x) = Losing money
5. **Orders** - Total number of orders

The old manual ROAS calculator has been removed - ROAS is now calculated automatically from real data!

### 4. Shopify Export Script

**File:** `shopify-export-script.js`

A Node.js script that:
- Fetches orders from Shopify Admin API
- Aggregates revenue and shipping by date
- Pushes data to your backend
- Supports scheduling via cron or GitHub Actions

### 5. Documentation

**Files:**
- `SHOPIFY_SETUP.md` - Complete setup guide
- `SHOPIFY_INTEGRATION_SUMMARY.md` - This file

## How It Works

```
┌─────────────────┐
│  Shopify Store  │
└────────┬────────┘
         │ Orders + Shipping Data
         ▼
┌─────────────────────┐
│ shopify-export-     │ (Run via cron/scheduled task)
│ script.js           │
└────────┬────────────┘
         │ POST /api/shopify/push
         ▼
┌─────────────────────┐
│ Marketing Tracker   │
│ Backend (FastAPI)   │
└────────┬────────────┘
         │ Store in SQLite
         ▼
┌─────────────────────┐
│ shopify_daily_      │
│ metrics table       │
└────────┬────────────┘
         │ Aggregate & Calculate ROAS
         ▼
┌─────────────────────┐
│ Dashboard           │
│ (React Frontend)    │
└─────────────────────┘
```

## Next Steps to Get Shopify Data Flowing

### 1. Create Shopify Custom App

1. Go to Shopify Admin → Settings → Apps and sales channels
2. Click "Develop apps" → "Create an app"
3. Name it "Marketing Tracker"
4. Enable `read_orders` and `read_shipping` scopes
5. Install app and copy the Admin API access token

### 2. Configure Environment Variables

Add to your `.env` file:
```bash
SHOPIFY_SHOP_NAME=your-shop-name
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxx
MARKETING_TRACKER_URL=https://marketing.brianborncamp.com
SYNC_API_KEY=optional-security-key
```

### 3. Install Dependencies

```bash
cd /Users/melon/marketing
npm install node-fetch
```

### 4. Test the Script

```bash
node shopify-export-script.js
```

Expected output:
```
🛍️  Shopify Order Export Script
✅ Fetched 45 orders
✅ Aggregated into 28 daily records
✅ Success! Processed 28 records
```

### 5. Schedule Regular Syncs

**Option A: Cron (Recommended for server)**
```bash
crontab -e
# Add:
0 * * * * cd /path/to/marketing && node shopify-export-script.js
```

**Option B: GitHub Actions (Cloud-based)**
See `SHOPIFY_SETUP.md` for GitHub Actions workflow

### 6. Verify on Dashboard

Visit https://marketing.brianborncamp.com and you should see:
- Revenue populated
- Shipping Cost populated
- ROAS calculated automatically
- Orders count displayed

## Customization Options

### Adjust Shipping Cost Calculation

By default, the script estimates shipping cost as 30% of shipping revenue. To use actual costs:

```javascript
// In shopify-export-script.js, replace:
const shippingCost = shippingRevenue * 0.3;

// With your actual cost logic:
const SHIPPING_COST_MAP = {
  'Standard': 5.50,
  'Express': 12.00,
};
const shippingCost = SHIPPING_COST_MAP[shippingMethod] || 5.00;
```

### Adjust History Period

```javascript
// In shopify-export-script.js
const DAYS_OF_HISTORY = 30; // Change to 60, 90, etc.
```

### Add More Metrics

You can extend the system to track:
- Refunds
- Taxes
- Discounts
- Product categories
- Customer lifetime value

## Metrics Calculation Details

### ROAS Formula

```
ROAS = Total Revenue / (Ad Spend + Shipping Costs)
```

**Example:**
- Revenue: $1,000
- Ad Spend: $300
- Shipping Costs: $50
- ROAS = $1,000 / ($300 + $50) = 2.86x

This means for every dollar spent (ads + shipping), you made $2.86 in revenue.

### Why Include Shipping Costs?

Including shipping costs in the denominator gives you a more accurate picture of profitability. If you only divided by ad spend, you'd overestimate performance.

## Security Considerations

1. ✅ Shopify API token stored in `.env` (not committed to git)
2. ✅ Optional `SYNC_API_KEY` to protect the push endpoint
3. ✅ Only aggregated daily totals stored (no customer PII)
4. ✅ HTTP Basic Auth protects dashboard access
5. ✅ Shopify app scoped to minimum permissions (`read_orders`)

## Troubleshooting

### Dashboard shows $0.00 revenue
- Run the Shopify export script
- Check script output for errors
- Verify `SHOPIFY_ACCESS_TOKEN` is correct
- Check browser console for API errors

### Script fails with 401 error
- Verify `SHOPIFY_ACCESS_TOKEN` is correct
- Ensure Shopify app is installed
- Check app has `read_orders` scope

### ROAS shows "N/A"
- Ensure both ad spend and Shopify data are synced
- Check that `MARKETING_TRACKER_URL` is correct
- Verify backend is receiving data (`docker-compose logs backend`)

## Files Modified/Created

### Backend
- ✅ `backend/app/database.py` - Added Shopify tables and methods
- ✅ `backend/app/routers/shopify.py` - New Shopify API endpoints
- ✅ `backend/app/main.py` - Registered Shopify router

### Frontend
- ✅ `frontend/src/components/MetricsSummary.tsx` - Updated with Shopify metrics

### Scripts & Documentation
- ✅ `shopify-export-script.js` - Shopify data export script
- ✅ `SHOPIFY_SETUP.md` - Setup instructions
- ✅ `SHOPIFY_INTEGRATION_SUMMARY.md` - This file

## Deployment Status

✅ **DEPLOYED TO PRODUCTION**
- Backend updated with Shopify endpoints
- Frontend updated with new metrics display
- Database schema migrated automatically
- Available at: https://marketing.brianborncamp.com

## What's Next?

1. **Set up Shopify app** (see step 1 above)
2. **Run the export script** to populate initial data
3. **Schedule automated syncs** (cron or GitHub Actions)
4. **Monitor your real ROAS** and optimize campaigns!

Optional enhancements:
- Add product category breakdowns
- Track profit margins
- Set up ROAS alerts
- Integrate Meta Ads and Reddit Ads
- Add refund tracking
