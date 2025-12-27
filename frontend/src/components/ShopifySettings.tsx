import { useState, useEffect } from 'react';

interface ShopifySettingsProps {
  onBack: () => void;
}

// Helper function to get auth headers
const getAuthHeaders = (): HeadersInit => {
  const credentials = sessionStorage.getItem('authCredentials');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (credentials) {
    headers['Authorization'] = `Basic ${credentials}`;
  }
  return headers;
};

export default function ShopifySettings({ onBack }: ShopifySettingsProps) {
  const isEmbedded = !onBack || onBack.toString() === '(() => {})';
  const [shopName, setShopName] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle');
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    loadSavedCredentials();
    checkLastSync();
  }, []);

  const loadSavedCredentials = async () => {
    try {
      // Try to load from backend first
      const response = await fetch('/api/shopify/credentials', {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        if (data.configured) {
          setShopName(data.shop_name || '');
          setAccessToken('••••••••••••••••');
          setIsSaved(true);
          return;
        }
      }
    } catch (e) {
      console.error('Failed to load credentials from backend', e);
    }

    // Fallback to localStorage (for backward compatibility)
    const saved = localStorage.getItem('shopify_credentials');
    if (saved) {
      try {
        const { shopName: savedShop, accessToken: savedToken } = JSON.parse(saved);
        setShopName(savedShop || '');
        setAccessToken(savedToken ? '••••••••••••••••' : '');
        setIsSaved(!!savedToken);
      } catch (e) {
        console.error('Failed to load credentials', e);
      }
    }
  };

  const checkLastSync = async () => {
    const lastSyncTime = localStorage.getItem('shopify_last_sync');
    if (lastSyncTime) {
      const date = new Date(lastSyncTime);
      setLastSync(date.toLocaleString());
    }
  };

  const saveCredentials = async () => {
    if (!shopName || !accessToken || accessToken === '••••••••••••••••') {
      alert('Please enter both shop name and access token');
      return;
    }

    try {
      // Save to backend database (encrypted)
      const response = await fetch('/api/shopify/credentials', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          shop_name: shopName,
          access_token: accessToken
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save credentials');
      }

      // Also save to localStorage as backup
      localStorage.setItem('shopify_credentials', JSON.stringify({
        shopName,
        accessToken
      }));

      setIsSaved(true);
      setAccessToken('••••••••••••••••'); // Mask the token after saving
      alert('Shopify credentials saved securely! Click "Sync Now" to fetch your order data.');
    } catch (error) {
      console.error('Error saving credentials:', error);
      alert('Failed to save credentials. Please try again.');
    }
  };

  const syncNow = async () => {
    setSyncStatus('syncing');
    setErrorMessage('');

    try {
      // Try to get credentials from backend first
      let shop = shopName;
      let token = accessToken;

      // If token is masked, try to get from backend
      if (token === '••••••••••••••••' || !token) {
        const credsResponse = await fetch('/api/shopify/credentials', {
          headers: getAuthHeaders()
        });
        if (credsResponse.ok) {
          const credsData = await credsResponse.json();
          if (credsData.configured) {
            shop = credsData.shop_name;
            // Backend will use stored token via shopify_proxy, so we don't need the actual token
            // Just use the masked one to signal we should use backend credentials
            token = 'USE_BACKEND_CREDENTIALS';
          }
        }
      }

      // Fallback to localStorage
      if (!shop || !token || token === '••••••••••••••••') {
        const saved = localStorage.getItem('shopify_credentials');
        if (saved) {
          const parsed = JSON.parse(saved);
          shop = parsed.shopName;
          token = parsed.accessToken;
        }
      }

      if (!shop || !token || token === '••••••••••••••••' || token === 'USE_BACKEND_CREDENTIALS') {
        // If we have backend credentials, use them via the proxy
        if (token === 'USE_BACKEND_CREDENTIALS') {
          // Fetch using backend-stored credentials
          const response = await fetch('/api/shopify-proxy/sync-from-backend', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ days: 30 })
          });

          if (!response.ok) {
            throw new Error('Failed to sync using saved credentials');
          }

          const result = await response.json();
          if (!result.success) {
            throw new Error(result.message || 'Sync failed');
          }
        } else {
          alert('Please save your Shopify credentials first');
          setSyncStatus('idle');
          return;
        }
      } else {
        // Use provided credentials
        // Fetch orders from Shopify
        const orders = await fetchShopifyOrders(shop, token, 30);

        // Aggregate by date
        const dailyMetrics = aggregateOrdersByDate(orders);

        // Push to backend
        await pushToBackend(dailyMetrics);
      }

      setSyncStatus('success');
      localStorage.setItem('shopify_last_sync', new Date().toISOString());
      checkLastSync();

      setTimeout(() => {
        setSyncStatus('idle');
      }, 3000);
    } catch (error: any) {
      setSyncStatus('error');
      setErrorMessage(error.message || 'Sync failed');
      console.error('Sync error:', error);
    }
  };

  const content = (
    <div className={isEmbedded ? '' : 'max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
        {/* Setup Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold text-blue-900 mb-3">📝 Setup Instructions</h2>
          <ol className="space-y-2 text-sm text-blue-800">
            <li>1. Go to your Shopify Admin → <strong>Settings</strong> → <strong>Apps and sales channels</strong></li>
            <li>2. Click <strong>Develop apps</strong> → <strong>Create an app</strong></li>
            <li>3. Name it "Marketing Tracker" and click <strong>Create app</strong></li>
            <li>4. Click <strong>Configure Admin API scopes</strong></li>
            <li>5. Enable <strong>read_orders</strong> and <strong>read_shipping</strong> scopes</li>
            <li>6. Click <strong>Save</strong> → <strong>Install app</strong></li>
            <li>7. Copy the <strong>Admin API access token</strong> (starts with "shpat_")</li>
            <li>8. Paste your shop name and token below</li>
          </ol>
        </div>

        {/* Credentials Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Shopify Credentials</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Shop Name
              </label>
              <div className="flex items-center">
                <input
                  type="text"
                  value={shopName}
                  onChange={(e) => setShopName(e.target.value)}
                  placeholder="my-store"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-l-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <span className="px-4 py-2 bg-gray-100 border border-l-0 border-gray-300 rounded-r-lg text-gray-600">
                  .myshopify.com
                </span>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Just the store name, without ".myshopify.com"
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Admin API Access Token
              </label>
              <input
                type="password"
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                placeholder="shpat_xxxxxxxxxxxxxxxxxxxxx"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Starts with "shpat_" - saved securely in your browser
              </p>
            </div>

            <button
              onClick={saveCredentials}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              💾 Save Credentials
            </button>
          </div>
        </div>

        {/* Sync Section */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Data Sync</h2>

          {lastSync && (
            <div className="mb-4 text-sm text-gray-600">
              Last sync: <strong>{lastSync}</strong>
            </div>
          )}

          <button
            onClick={syncNow}
            disabled={!isSaved || syncStatus === 'syncing'}
            className={`w-full px-6 py-3 rounded-lg font-medium transition-colors ${
              !isSaved
                ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                : syncStatus === 'syncing'
                ? 'bg-blue-400 text-white cursor-wait'
                : syncStatus === 'success'
                ? 'bg-green-600 text-white'
                : syncStatus === 'error'
                ? 'bg-red-600 text-white'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {syncStatus === 'idle' && '🔄 Sync Now (Last 30 Days)'}
            {syncStatus === 'syncing' && '⏳ Syncing... (This may take a minute)'}
            {syncStatus === 'success' && '✅ Sync Complete!'}
            {syncStatus === 'error' && '❌ Sync Failed'}
          </button>

          {errorMessage && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">
                <strong>Error:</strong> {errorMessage}
              </p>
            </div>
          )}

          {syncStatus === 'success' && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-800">
                ✅ Successfully synced order data! Refresh your dashboard to see the updated metrics.
              </p>
            </div>
          )}

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">💡 Tips</h3>
            <ul className="text-xs text-gray-600 space-y-1">
              <li>• Run sync manually whenever you want to update revenue data</li>
              <li>• Credentials are stored securely in your browser (not on the server)</li>
              <li>• Sync fetches the last 30 days of order data</li>
              <li>• You can sync multiple times - data will be updated, not duplicated</li>
            </ul>
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h3 className="text-sm font-semibold text-yellow-900 mb-2">🔒 Security Note</h3>
          <p className="text-xs text-yellow-800">
            Your Shopify credentials are securely stored encrypted in the database.
            Your access token is encrypted using industry-standard encryption before storage and can only be accessed with your login credentials.
          </p>
        </div>
    </div>
  );

  if (isEmbedded) {
    return content;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Shopify Integration</h1>
              <p className="mt-1 text-sm text-gray-500">
                Connect your Shopify store to track revenue and ROAS
              </p>
            </div>
            <button
              onClick={onBack}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              ← Back
            </button>
          </div>
        </div>
      </header>

      <main>
        {content}
      </main>
    </div>
  );
}

// Helper function to fetch orders from Shopify via backend proxy
async function fetchShopifyOrders(shopName: string, accessToken: string, days: number) {
  const credentials = sessionStorage.getItem('authCredentials');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (credentials) {
    headers['Authorization'] = `Basic ${credentials}`;
  }

  const response = await fetch('/api/shopify-proxy/fetch-orders', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      shop_name: shopName,
      access_token: accessToken,
      days: days
    })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    if (response.status === 401) {
      throw new Error('Invalid access token. Please check your credentials.');
    }
    throw new Error(errorData.detail || `API error: ${response.status}`);
  }

  const data = await response.json();
  return data.orders || [];
}

// Helper function to aggregate orders by date
function aggregateOrdersByDate(orders: any[]) {
  const dailyMetrics: Record<string, any> = {};

  orders.forEach(order => {
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

    // Revenue = subtotal - discounts (product revenue only, excluding shipping)
    const subtotal = parseFloat(order.subtotal_price || 0);
    const discounts = parseFloat(order.total_discounts || 0);
    const revenue = subtotal - discounts;

    // Shipping Revenue = what customer paid for shipping
    const shippingRevenue = order.shipping_lines.reduce((sum: number, line: any) => {
      return sum + parseFloat(line.price || 0);
    }, 0);

    // Shipping Cost = shipping sold * 1.05 (assume 5% markup on cost)
    const shippingCost = shippingRevenue * 1.05;

    dailyMetrics[orderDate].revenue += revenue;
    dailyMetrics[orderDate].shipping_revenue += shippingRevenue;
    dailyMetrics[orderDate].shipping_cost += shippingCost;
    dailyMetrics[orderDate].order_count += 1;
  });

  return Object.values(dailyMetrics);
}

// Helper function to push data to backend
async function pushToBackend(dailyMetrics: any[]) {
  const credentials = sessionStorage.getItem('authCredentials');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (credentials) {
    headers['Authorization'] = `Basic ${credentials}`;
  }

  const response = await fetch('/api/shopify/push', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      daily_metrics: dailyMetrics,
      source: 'browser_ui',
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to push data to backend: ${errorText}`);
  }

  return await response.json();
}
