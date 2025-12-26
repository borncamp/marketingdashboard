# Shopify Integration Setup

This guide explains how to integrate Shopify order data into your Marketing Tracker dashboard to calculate real ROAS and track revenue metrics.

## Overview

The Shopify integration works by:
1. Fetching order data from Shopify Admin API
2. Aggregating revenue and shipping costs by date
3. Pushing the data to your Marketing Tracker backend
4. Displaying revenue, ROAS, and shipping metrics alongside ad performance

## Setup Steps

### 1. Create a Shopify Custom App

1. Go to your Shopify Admin → **Settings** → **Apps and sales channels**
2. Click **Develop apps** → **Create an app**
3. Name it "Marketing Tracker" and assign it to yourself
4. Click **Configure Admin API scopes**
5. Enable the following scopes:
   - `read_orders` - To fetch order data
   - `read_shipping` - To get shipping information
6. Click **Save**, then **Install app**
7. Copy the **Admin API access token** (you'll only see this once!)

### 2. Set Up Environment Variables

Create a `.env` file in the `/marketing` directory (or add to your existing `.env`):

```bash
# Shopify Configuration
SHOPIFY_SHOP_NAME=your-shop-name  # e.g., 'my-store' from my-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxx

# Marketing Tracker URL
MARKETING_TRACKER_URL=https://marketing.brianborncamp.com

# Optional: API key for sync endpoint security
SYNC_API_KEY=your-secret-key
```

### 3. Install Script Dependencies

```bash
cd /marketing
npm install node-fetch
```

### 4. Test the Script

Run manually to test:

```bash
node shopify-export-script.js
```

You should see output like:
```
🛍️  Shopify Order Export Script
================================
Shop: your-shop.myshopify.com
Fetching last 30 days of orders...
✅ Fetched 45 orders
✅ Aggregated into 28 daily records
📤 Pushing to Marketing Tracker...
✅ Success! Processed 28 records
✨ Export complete!
```

### 5. Schedule Automatic Sync

**Option A: Cron Job (Linux/Mac)**

Add to your crontab (`crontab -e`):

```bash
# Run every hour at minute 0
0 * * * * cd /path/to/marketing && /usr/bin/node shopify-export-script.js >> /var/log/shopify-sync.log 2>&1

# Or run once daily at 3 AM
0 3 * * * cd /path/to/marketing && /usr/bin/node shopify-export-script.js >> /var/log/shopify-sync.log 2>&1
```

**Option B: Node.js Scheduler (Alternative)**

Create a `scheduled-sync.js` file:

```javascript
const cron = require('node-cron');
const { execSync } = require('child_process');

// Run every hour
cron.schedule('0 * * * *', () => {
  console.log('Running Shopify sync...');
  execSync('node shopify-export-script.js', { stdio: 'inherit' });
});

console.log('Shopify sync scheduler started');
```

Install `node-cron` and run:
```bash
npm install node-cron
node scheduled-sync.js
```

**Option C: GitHub Actions (Cloud)**

Create `.github/workflows/shopify-sync.yml`:

```yaml
name: Shopify Data Sync

on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:  # Manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install node-fetch
      - name: Run sync script
        env:
          SHOPIFY_SHOP_NAME: ${{ secrets.SHOPIFY_SHOP_NAME }}
          SHOPIFY_ACCESS_TOKEN: ${{ secrets.SHOPIFY_ACCESS_TOKEN }}
          MARKETING_TRACKER_URL: ${{ secrets.MARKETING_TRACKER_URL }}
          SYNC_API_KEY: ${{ secrets.SYNC_API_KEY }}
        run: node shopify-export-script.js
```

Add secrets in GitHub repo settings.

## Customizing Shipping Cost Calculation

By default, the script estimates shipping cost as 30% of shipping revenue. To use actual carrier costs:

### Option 1: Manual Cost Table

Edit `shopify-export-script.js` and add a cost table:

```javascript
const SHIPPING_COST_MAP = {
  'Standard Shipping': 5.50,
  'Express Shipping': 12.00,
  'International': 25.00,
};

const shippingCost = order.shipping_lines.reduce((sum, line) => {
  return sum + (SHIPPING_COST_MAP[line.title] || shippingRevenue * 0.3);
}, 0);
```

### Option 2: Integrate Shipping Carrier API

For real-time costs, integrate with your carrier (USPS, UPS, FedEx):

```javascript
// Example for actual carrier costs
async function getActualShippingCost(trackingNumber) {
  // Call your carrier's API here
  // Return actual cost
}
```

## Dashboard Features

Once synced, your dashboard will display:

- **Revenue** - Total product revenue (excluding shipping)
- **Shipping Cost** - Actual cost of shipping orders
- **ROAS** - Calculated as `Revenue / (Ad Spend + Shipping Cost)`
- **Orders** - Total number of orders
- **Profit** - Revenue - (Ad Spend + Shipping Cost)

## Troubleshooting

### "Shopify API error: 401"
- Check your `SHOPIFY_ACCESS_TOKEN` is correct
- Ensure the app is installed and has `read_orders` scope

### "Failed to push data: 401"
- If using `SYNC_API_KEY`, ensure it matches in both `.env` and backend config
- Check `MARKETING_TRACKER_URL` is correct

### "No orders found"
- Verify your shop has orders in the date range
- Check the shop name is correct (without `.myshopify.com`)

### Missing data on dashboard
- Ensure the script ran successfully (check logs)
- Try refreshing the dashboard
- Check browser console for API errors

## API Endpoints

The backend provides these Shopify endpoints:

- `POST /api/shopify/push` - Push order data (used by script)
- `GET /api/shopify/metrics?days=7` - Get aggregated metrics
- `GET /api/shopify/metrics/{metric_name}?days=30` - Get time series

## Security Notes

1. **Never commit** `.env` or tokens to git
2. Use `SYNC_API_KEY` in production to protect the sync endpoint
3. Limit Shopify app scopes to only what's needed (`read_orders`)
4. Rotate access tokens periodically
5. Monitor sync logs for unauthorized access attempts

## Data Privacy

- Order data is stored locally in your SQLite database
- Only aggregated daily totals are stored (no customer PII)
- Data includes: date, revenue, shipping costs, order count
- Individual order details are not retained

## Next Steps

After setup, you can:
- Adjust the `DAYS_OF_HISTORY` constant to fetch more/less historical data
- Add additional metrics (refunds, taxes, etc.)
- Integrate with other platforms (Meta Ads, Reddit Ads)
- Set up alerts for low ROAS or high costs
