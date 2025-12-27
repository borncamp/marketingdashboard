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
        shipping_revenue: shopifyData.total_shipping_revenue || 0,
        shipping_cost: shopifyData.total_shipping_cost || 0,
        orders: shopifyData.total_orders || 0,
      });
    } catch (error) {
      console.error('Failed to load metrics summary:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate CTR, ROAS and POAS
  const ctr = totals.impressions > 0 ? (totals.clicks / totals.impressions) * 100 : 0;

  // ROAS = (Product Revenue + Shipping Collected) / Ad Spend
  const totalCollected = shopifyMetrics.revenue + shopifyMetrics.shipping_revenue;
  const actualROAS = totals.spend > 0 ? totalCollected / totals.spend : 0;

  // POAS = (Product Sold + Shipping Collected - Shipping Cost) / Ad Spend
  const totalProfit = shopifyMetrics.revenue + shopifyMetrics.shipping_revenue - shopifyMetrics.shipping_cost;
  const actualPOAS = totals.spend > 0 ? totalProfit / totals.spend : 0;

  const metrics = [
    {
      name: 'Impressions',
      value: totals.impressions.toLocaleString(),
      icon: '👁️',
      color: 'blue',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
      borderColor: 'border-blue-200'
    },
    {
      name: 'Clicks',
      value: totals.clicks.toLocaleString(),
      icon: '👆',
      color: 'indigo',
      bgColor: 'bg-indigo-50',
      textColor: 'text-indigo-600',
      borderColor: 'border-indigo-200'
    },
    {
      name: 'CTR',
      value: `${ctr.toFixed(2)}%`,
      icon: '🎯',
      color: 'cyan',
      bgColor: 'bg-cyan-50',
      textColor: 'text-cyan-600',
      borderColor: 'border-cyan-200'
    },
    {
      name: 'Conversions',
      value: totals.conversions.toLocaleString(),
      icon: '✅',
      color: 'lime',
      bgColor: 'bg-lime-50',
      textColor: 'text-lime-600',
      borderColor: 'border-lime-200'
    },
    {
      name: 'Orders',
      value: shopifyMetrics.orders.toLocaleString(),
      icon: '🛒',
      color: 'purple',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-600',
      borderColor: 'border-purple-200'
    },
    {
      name: 'Ad Spend',
      value: `$${totals.spend.toFixed(2)}`,
      icon: '💰',
      color: 'yellow',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-600',
      borderColor: 'border-yellow-200'
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
      name: 'Shipping Sold',
      value: `$${shopifyMetrics.shipping_revenue.toFixed(2)}`,
      icon: '🚢',
      color: 'teal',
      bgColor: 'bg-teal-50',
      textColor: 'text-teal-600',
      borderColor: 'border-teal-200'
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
      name: 'POAS',
      value: actualPOAS > 0 ? `${actualPOAS.toFixed(2)}x` : 'N/A',
      icon: '💎',
      color: actualPOAS >= 1.5 ? 'emerald' : actualPOAS >= 0.75 ? 'amber' : 'red',
      bgColor: actualPOAS >= 1.5 ? 'bg-emerald-50' : actualPOAS >= 0.75 ? 'bg-amber-50' : 'bg-red-50',
      textColor: actualPOAS >= 1.5 ? 'text-emerald-600' : actualPOAS >= 0.75 ? 'text-amber-600' : 'text-red-600',
      borderColor: actualPOAS >= 1.5 ? 'border-emerald-200' : actualPOAS >= 0.75 ? 'border-amber-200' : 'border-red-200'
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

      {/* Metrics Cards - Two Rows */}
      <div className="space-y-3">
        {/* First Row - Campaign Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {metrics.slice(0, 5).map((metric) => (
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

        {/* Second Row - Financial Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {metrics.slice(5).map((metric) => (
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
    </div>
  );
}
