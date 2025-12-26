# Shopify Integration - Browser Setup Guide

## 🎉 Easy Browser-Based Setup

Your Marketing Tracker now has a **browser-based Shopify integration**! No scripts, no command line, no environment variables - just enter your credentials in the dashboard and click sync.

## Quick Start (5 Minutes)

### Step 1: Create Shopify Custom App

1. Open your Shopify Admin
2. Go to **Settings** → **Apps and sales channels**
3. Click **Develop apps**
4. Click **Create an app**
5. Name it "Marketing Tracker" → **Create app**
6. Click **Configure Admin API scopes**
7. Enable these permissions:
   - ✅ `read_orders`
   - ✅ `read_shipping`
8. Click **Save** → **Install app**
9. **Copy the Admin API access token** (starts with `shpat_`)
   - ⚠️ You'll only see this once! Save it somewhere safe temporarily

### Step 2: Enter Credentials in Dashboard

1. Go to https://marketing.brianborncamp.com
2. Log in with your credentials
3. Click **🛍️ Shopify** button in the header
4. Enter your **Shop Name** (just "my-store", not the full URL)
5. Paste your **Access Token** (the `shpat_` token from step 1)
6. Click **💾 Save Credentials**

### Step 3: Sync Your Data

1. Click **🔄 Sync Now (Last 30 Days)**
2. Wait ~30-60 seconds while it fetches your orders
3. See the success message ✅
4. Click **← Back** to return to dashboard
5. Your revenue, ROAS, and shipping metrics are now populated!

## What Gets Synced?

The sync pulls the last 30 days of Shopify orders and calculates:
- **Revenue** - Total product sales (minus discounts)
- **Shipping Revenue** - Shipping fees collected from customers
- **Shipping Cost** - Estimated shipping costs (30% of shipping revenue)*
- **Order Count** - Total number of orders

*You can customize the shipping cost calculation later if needed

## How Often Should I Sync?

**Manual Sync (Current Setup)**
- Click "Sync Now" whenever you want to update the data
- Recommended: Once per day or week
- Takes ~30-60 seconds per sync

**Future: Automatic Sync**
- We can set up automatic hourly/daily syncing if you prefer
- Requires running the Node.js script on a schedule (see `SHOPIFY_SETUP.md`)

## Security & Privacy

✅ **Your credentials are secure:**
- Stored only in your browser's localStorage
- Never sent to our backend servers
- Used directly from your browser to call Shopify's API
- Only aggregated daily totals are stored (no customer PII)

✅ **Minimal permissions:**
- App only has `read_orders` access (can't modify anything)
- Can't access customer personal information
- Can't access payment details

## Troubleshooting

### "Invalid access token" error
- Double-check the token starts with `shpat_`
- Make sure you copied the entire token
- Verify the app is installed in Shopify
- Try creating a new app and token

### "Failed to push data to backend" error
- Check your internet connection
- Verify you're logged into the dashboard
- Try refreshing the page and syncing again

### Dashboard still shows $0.00 revenue
- Make sure sync completed successfully (look for ✅)
- Click the **🔄 Refresh** button in the dashboard header
- Check that your Shopify store has orders in the last 30 days
- Open browser console (F12) and check for errors

### Sync takes a very long time
- This is normal if you have many orders (100+)
- Shopify API has rate limits
- For stores with 500+ orders, consider using the Node.js script instead

## Customizing Shipping Cost Calculation

By default, shipping cost is estimated as 30% of shipping revenue. To change this:

1. Open browser DevTools (F12)
2. Go to **Sources** tab
3. Find the ShopifySettings component
4. Look for this line:
   ```javascript
   const shippingCost = shippingRevenue * 0.3;
   ```
5. For now, this requires editing the source code

**Better option:** Tell me your shipping structure and I can update the calculation for you!

Examples:
- "Flat $5.50 per order"
- "Use actual shipping line costs from Shopify"
- "Different rates for domestic vs international"

## What's Next?

Now that Shopify is connected, you can:

### ✅ View Real ROAS
The ROAS metric is now calculated automatically:
```
ROAS = Revenue / (Ad Spend + Shipping Cost)
```

Green (≥2.0x) = Great performance
Yellow (1.0-2.0x) = Okay performance
Red (<1.0x) = Losing money

### ✅ Track Revenue Over Time
- Use the 7d/30d/90d toggle to see different time periods
- Compare revenue trends with ad spend
- Identify your most profitable weeks

### ✅ Calculate Profit
With ad spend, shipping costs, and revenue all tracked:
```
Profit = Revenue - Ad Spend - Shipping Cost
```

### Optional: Set Up Auto-Sync
If you want data to sync automatically without clicking "Sync Now":
- Option 1: Run the Node.js script via cron (see `SHOPIFY_SETUP.md`)
- Option 2: Set up GitHub Actions to run hourly
- Option 3: I can help set up a serverless function

## Comparison: Browser vs Script

| Feature | Browser Setup | Node.js Script |
|---------|--------------|----------------|
| Setup Time | 5 minutes | 10-15 minutes |
| Credentials | Saved in browser | Environment variables |
| Sync Method | Manual click | Automated schedule |
| Technical Skills | None required | Basic command line |
| Best For | Small stores, manual control | Large stores, automation |

## Need Help?

Common questions:

**Q: Can I sync older data?**
A: Currently limited to last 30 days. I can adjust this if needed.

**Q: Will this slow down my store?**
A: No, it only reads data via API. No impact on store performance.

**Q: Can I disconnect Shopify?**
A: Yes, just clear your credentials in the browser settings page.

**Q: What if I change my Shopify access token?**
A: Just re-enter the new token in the Shopify settings page.

**Q: Can I sync multiple Shopify stores?**
A: Currently one store per dashboard. Let me know if you need multiple.

## Files Created

For this browser-based setup:
- ✅ `frontend/src/components/ShopifySettings.tsx` - Settings page UI
- ✅ `frontend/src/App.tsx` - Added Shopify button
- ✅ `backend/app/routers/shopify.py` - API endpoints (already created)
- ✅ `backend/app/database.py` - Database schema (already created)

## Success! 🎉

You should now see:
- 💰 Ad Spend
- 💵 Revenue (from Shopify)
- 📦 Shipping Cost
- 📈 ROAS (automatically calculated)
- 🛒 Orders

All updating based on real data from your store!
