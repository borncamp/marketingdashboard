/**
 * Shopify Order Data Export Script
 *
 * This script fetches order data from Shopify and pushes it to your
 * Marketing Tracker backend for revenue and shipping cost analysis.
 *
 * Setup Instructions:
 * 1. Install dependencies: npm install node-fetch
 * 2. Create a custom app in Shopify Admin with Order read permissions
 * 3. Set environment variables (see below)
 * 4. Run: node shopify-export-script.js
 * 5. Schedule with cron to run daily/hourly
 *
 * Environment Variables:
 * - SHOPIFY_SHOP_NAME: Your shop name (e.g., 'my-store' from my-store.myshopify.com)
 * - SHOPIFY_ACCESS_TOKEN: Admin API access token from your custom app
 * - MARKETING_TRACKER_URL: Your backend URL (e.g., 'https://marketing.brianborncamp.com')
 * - SYNC_API_KEY: (Optional) API key if you configured one
 */

const fetch = require('node-fetch');

// Configuration from environment variables
const SHOPIFY_SHOP = process.env.SHOPIFY_SHOP_NAME || 'your-shop-name';
const SHOPIFY_ACCESS_TOKEN = process.env.SHOPIFY_ACCESS_TOKEN || '';
const MARKETING_TRACKER_URL = process.env.MARKETING_TRACKER_URL || 'http://localhost:8000';
const SYNC_API_KEY = process.env.SYNC_API_KEY || '';
const DAYS_OF_HISTORY = 30; // Fetch last 30 days

/**
 * Fetch orders from Shopify for a specific date range
 */
async function fetchShopifyOrders(startDate, endDate) {
  const shopifyUrl = `https://${SHOPIFY_SHOP}.myshopify.com/admin/api/2024-01/orders.json`;

  const params = new URLSearchParams({
    status: 'any',
    created_at_min: startDate.toISOString(),
    created_at_max: endDate.toISOString(),
    limit: 250, // Max per page
  });

  const response = await fetch(`${shopifyUrl}?${params}`, {
    headers: {
      'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Shopify API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data.orders || [];
}

/**
 * Aggregate orders by date
 */
function aggregateOrdersByDate(orders) {
  const dailyMetrics = {};

  orders.forEach(order => {
    // Extract date (YYYY-MM-DD)
    const orderDate = order.created_at.split('T')[0];

    if (!dailyMetrics[orderDate]) {
      dailyMetrics[orderDate] = {
        date: orderDate,
        revenue: 0,
        shipping_revenue: 0,
        shipping_cost: 0,
        order_count: 0,
      };
    }

    // Calculate revenue (subtotal - discounts)
    const subtotal = parseFloat(order.subtotal_price || 0);
    const discounts = parseFloat(order.total_discounts || 0);
    const revenue = subtotal - discounts;

    // Shipping revenue collected from customer
    const shippingRevenue = order.shipping_lines.reduce((sum, line) => {
      return sum + parseFloat(line.price || 0);
    }, 0);

    // Estimated shipping cost (you may want to customize this logic)
    // For now, we'll estimate 30% of shipping revenue as actual cost
    // In production, you might integrate with your shipping carrier API
    const shippingCost = shippingRevenue * 0.3;

    dailyMetrics[orderDate].revenue += revenue;
    dailyMetrics[orderDate].shipping_revenue += shippingRevenue;
    dailyMetrics[orderDate].shipping_cost += shippingCost;
    dailyMetrics[orderDate].order_count += 1;
  });

  return Object.values(dailyMetrics);
}

/**
 * Push aggregated data to Marketing Tracker backend
 */
async function pushToMarketingTracker(dailyMetrics) {
  const url = `${MARKETING_TRACKER_URL}/api/shopify/push`;

  const headers = {
    'Content-Type': 'application/json',
  };

  if (SYNC_API_KEY) {
    headers['X-API-Key'] = SYNC_API_KEY;
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({
      daily_metrics: dailyMetrics,
      source: 'shopify_node_script',
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to push data: ${response.status} ${errorText}`);
  }

  return await response.json();
}

/**
 * Main execution
 */
async function main() {
  console.log('🛍️  Shopify Order Export Script');
  console.log('================================');
  console.log(`Shop: ${SHOPIFY_SHOP}.myshopify.com`);
  console.log(`Fetching last ${DAYS_OF_HISTORY} days of orders...`);

  try {
    // Calculate date range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - DAYS_OF_HISTORY);

    console.log(`Date range: ${startDate.toISOString().split('T')[0]} to ${endDate.toISOString().split('T')[0]}`);

    // Fetch orders from Shopify
    console.log('\n📥 Fetching orders from Shopify...');
    const orders = await fetchShopifyOrders(startDate, endDate);
    console.log(`✅ Fetched ${orders.length} orders`);

    if (orders.length === 0) {
      console.log('⚠️  No orders found in this date range');
      return;
    }

    // Aggregate by date
    console.log('\n📊 Aggregating data by date...');
    const dailyMetrics = aggregateOrdersByDate(orders);
    console.log(`✅ Aggregated into ${dailyMetrics.length} daily records`);

    // Display summary
    console.log('\n📋 Summary:');
    dailyMetrics.forEach(day => {
      console.log(`  ${day.date}: $${day.revenue.toFixed(2)} revenue, ${day.order_count} orders`);
    });

    // Push to Marketing Tracker
    console.log(`\n📤 Pushing to Marketing Tracker: ${MARKETING_TRACKER_URL}`);
    const result = await pushToMarketingTracker(dailyMetrics);
    console.log(`✅ Success! Processed ${result.records_processed} records`);

    console.log('\n✨ Export complete!');

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    process.exit(1);
  }
}

// Run the script
main();
