import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface ShopifyMetrics {
  total_revenue: number;
  total_shipping_revenue: number;
  total_shipping_cost: number;
  total_orders: number;
  average_order_value: number;
}

interface DailyMetric {
  date: string;
  revenue: number;
  orders: number;
  shipping_revenue: number;
}

const getAuthHeaders = (): HeadersInit => {
  const credentials = sessionStorage.getItem('authCredentials');
  const headers: HeadersInit = {};
  if (credentials) {
    headers['Authorization'] = `Basic ${credentials}`;
  }
  return headers;
};

export default function ShopifyAnalytics() {
  const [period, setPeriod] = useState<7 | 14 | 30 | 90>(30);
  const [metrics, setMetrics] = useState<ShopifyMetrics | null>(null);
  const [dailyData, setDailyData] = useState<DailyMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, [period]);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/shopify/metrics?days=${period}`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch Shopify metrics');
      }

      const data = await response.json();
      setMetrics({
        total_revenue: data.total_revenue || 0,
        total_shipping_revenue: data.total_shipping_revenue || 0,
        total_shipping_cost: data.total_shipping_cost || 0,
        total_orders: data.total_orders || 0,
        average_order_value: data.total_orders > 0
          ? (data.total_revenue + data.total_shipping_revenue) / data.total_orders
          : 0
      });

      // Fetch daily time series data
      const dailyResponse = await fetch(`/api/shopify/daily-metrics?days=${period}`, {
        headers: getAuthHeaders()
      });

      if (dailyResponse.ok) {
        const dailyData = await dailyResponse.json();
        setDailyData(dailyData.metrics || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading Shopify data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Data</h3>
          <p className="text-red-700">{error}</p>
          <p className="text-sm text-red-600 mt-2">
            Make sure you've configured your Shopify integration in Settings and synced data.
          </p>
        </div>
      </div>
    );
  }

  if (!metrics || metrics.total_orders === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">No Shopify Data</h3>
          <p className="text-yellow-700 mb-4">
            No order data has been synced yet. Configure your Shopify integration in Settings.
          </p>
          <a
            href="#settings"
            className="inline-block px-6 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
          >
            Go to Settings
          </a>
        </div>
      </div>
    );
  }

  const formatCurrency = (value: number) => `$${value.toFixed(2)}`;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Period Toggle */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Shopify Sales Analytics</h2>
          <p className="text-gray-600 mt-1">Track revenue, orders, and shipping performance</p>
        </div>
        <div className="flex space-x-2">
          {[7, 14, 30, 90].map((days) => (
            <button
              key={days}
              onClick={() => setPeriod(days as 7 | 14 | 30 | 90)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                period === days
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">🛒</span>
            <span className="text-xs font-semibold text-purple-600 uppercase tracking-wide">
              Orders
            </span>
          </div>
          <div className="text-3xl font-bold text-purple-600 mb-1">
            {metrics.total_orders.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500">Total Orders</div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">💵</span>
            <span className="text-xs font-semibold text-green-600 uppercase tracking-wide">
              Revenue
            </span>
          </div>
          <div className="text-3xl font-bold text-green-600 mb-1">
            {formatCurrency(metrics.total_revenue)}
          </div>
          <div className="text-xs text-gray-500">Product Sales</div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">🚢</span>
            <span className="text-xs font-semibold text-teal-600 uppercase tracking-wide">
              Shipping
            </span>
          </div>
          <div className="text-3xl font-bold text-teal-600 mb-1">
            {formatCurrency(metrics.total_shipping_revenue)}
          </div>
          <div className="text-xs text-gray-500">Shipping Revenue</div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">📦</span>
            <span className="text-xs font-semibold text-orange-600 uppercase tracking-wide">
              Cost
            </span>
          </div>
          <div className="text-3xl font-bold text-orange-600 mb-1">
            {formatCurrency(metrics.total_shipping_cost)}
          </div>
          <div className="text-xs text-gray-500">Shipping Cost</div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">💰</span>
            <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">
              AOV
            </span>
          </div>
          <div className="text-3xl font-bold text-blue-600 mb-1">
            {formatCurrency(metrics.average_order_value)}
          </div>
          <div className="text-xs text-gray-500">Average Order Value</div>
        </div>
      </div>

      {/* Charts */}
      {dailyData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Revenue Chart */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Daily Revenue</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  stroke="#6b7280"
                  tick={{ fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis
                  stroke="#6b7280"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `$${value}`}
                />
                <Tooltip
                  formatter={(value: number) => formatCurrency(value)}
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Revenue"
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="shipping_revenue"
                  stroke="#14b8a6"
                  strokeWidth={2}
                  name="Shipping Revenue"
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Orders Chart */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Daily Orders</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  stroke="#6b7280"
                  tick={{ fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis stroke="#6b7280" tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Bar dataKey="orders" fill="#8b5cf6" name="Orders" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
