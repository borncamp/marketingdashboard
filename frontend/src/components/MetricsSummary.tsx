import { useState, useEffect } from 'react';
import { Campaign } from '../types/campaign';

interface MetricsSummaryProps {
  campaigns: Campaign[];
}

type TimePeriod = 7 | 30 | 90;

export default function MetricsSummary({ campaigns }: MetricsSummaryProps) {
  const [period, setPeriod] = useState<TimePeriod>(7);
  const [totals, setTotals] = useState({ spend: 0, clicks: 0, impressions: 0, conversions: 0 });
  const [shopifyMetrics, setShopifyMetrics] = useState({ revenue: 0, shipping_revenue: 0, shipping_cost: 0, orders: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMetrics();
  }, [period, campaigns]);

  const loadMetrics = async () => {
    if (campaigns.length === 0) return;

    setLoading(true);
    try {
      // Fetch campaign time series for all metrics
      const [spendData, clicksData, impressionsData, conversionsData, shopifyData] = await Promise.all([
        fetch(`/api/campaigns/all/metrics/spend?days=${period}`).then(r => r.json()),
        fetch(`/api/campaigns/all/metrics/clicks?days=${period}`).then(r => r.json()),
        fetch(`/api/campaigns/all/metrics/impressions?days=${period}`).then(r => r.json()),
        fetch(`/api/campaigns/all/metrics/conversions?days=${period}`).then(r => r.json()),
        fetch(`/api/shopify/metrics?days=${period}`).then(r => r.json()).catch(() => ({ total_revenue: 0, total_shipping_cost: 0, total_orders: 0 })),
      ]);

      // Sum up all data points across all campaigns
      const calculateTotal = (data: any[]) => {
        return data.reduce((sum, campaign) => {
          return sum + campaign.data_points.reduce((s: number, p: any) => s + p.value, 0);
        }, 0);
      };

      setTotals({
        spend: calculateTotal(spendData),
        clicks: calculateTotal(clicksData),
        impressions: calculateTotal(impressionsData),
        conversions: calculateTotal(conversionsData),
      });

      setShopifyMetrics({
        revenue: shopifyData.total_revenue || 0,
        shipping_cost: shopifyData.total_shipping_cost || 0,
        orders: shopifyData.total_orders || 0,
      });
    } catch (error) {
      console.error('Failed to load metrics summary:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate overall ROAS
  const totalCost = totals.spend + shopifyMetrics.shipping_cost;
  const actualROAS = totalCost > 0 ? shopifyMetrics.revenue / totalCost : 0;

  const metrics = [
    {
      name: 'Ad Spend',
      value: `$${totals.spend.toFixed(2)}`,
      icon: '💰',
      color: 'blue',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
      borderColor: 'border-blue-200'
    },
    {
      name: 'Revenue',
      value: `$${shopifyMetrics.revenue.toFixed(2)}`,
      icon: '💵',
      color: 'green',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600',
      borderColor: 'border-green-200'
    },
    {
      name: 'Shipping Cost',
      value: `$${shopifyMetrics.shipping_cost.toFixed(2)}`,
      icon: '📦',
      color: 'orange',
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-600',
      borderColor: 'border-orange-200'
    },
    {
      name: 'ROAS',
      value: actualROAS > 0 ? `${actualROAS.toFixed(2)}x` : 'N/A',
      icon: '📈',
      color: actualROAS >= 2 ? 'emerald' : actualROAS >= 1 ? 'amber' : 'red',
      bgColor: actualROAS >= 2 ? 'bg-emerald-50' : actualROAS >= 1 ? 'bg-amber-50' : 'bg-red-50',
      textColor: actualROAS >= 2 ? 'text-emerald-600' : actualROAS >= 1 ? 'text-amber-600' : 'text-red-600',
      borderColor: actualROAS >= 2 ? 'border-emerald-200' : actualROAS >= 1 ? 'border-amber-200' : 'border-red-200'
    },
    {
      name: 'Orders',
      value: shopifyMetrics.orders.toLocaleString(),
      icon: '🛒',
      color: 'purple',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-600',
      borderColor: 'border-purple-200'
    }
  ];

  const periodLabel = period === 7 ? 'Last 7 Days' : period === 30 ? 'Last 30 Days' : 'Last 90 Days';

  return (
    <div>
      {/* Period Toggle */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Performance Overview</h3>
        <div className="flex space-x-2">
          {[7, 30, 90].map((days) => (
            <button
              key={days}
              onClick={() => setPeriod(days as TimePeriod)}
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

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {metrics.map((metric) => (
          <div
            key={metric.name}
            className={`${metric.bgColor} border ${metric.borderColor} rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow ${loading ? 'opacity-50' : ''}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl">{metric.icon}</span>
              <span className={`text-xs font-semibold ${metric.textColor} uppercase tracking-wide`}>
                {periodLabel.split(' ')[1]}
              </span>
            </div>
            <div className={`text-3xl font-bold ${metric.textColor} mb-1`}>
              {loading ? '...' : metric.value}
            </div>
            <div className="text-xs text-gray-500">
              {metric.name}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
