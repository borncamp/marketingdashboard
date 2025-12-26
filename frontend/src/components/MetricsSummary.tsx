import { useState, useEffect } from 'react';
import { Campaign } from '../types/campaign';
import ROASCalculator from './ROASCalculator';

interface MetricsSummaryProps {
  campaigns: Campaign[];
}

type TimePeriod = 7 | 30 | 90;

export default function MetricsSummary({ campaigns }: MetricsSummaryProps) {
  const [period, setPeriod] = useState<TimePeriod>(7);
  const [totals, setTotals] = useState({ spend: 0, clicks: 0, impressions: 0, conversions: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMetrics();
  }, [period, campaigns]);

  const loadMetrics = async () => {
    if (campaigns.length === 0) return;

    setLoading(true);
    try {
      // Fetch time series for all metrics
      const [spendData, clicksData, impressionsData, conversionsData] = await Promise.all([
        fetch(`/api/campaigns/all/metrics/spend?days=${period}`).then(r => r.json()),
        fetch(`/api/campaigns/all/metrics/clicks?days=${period}`).then(r => r.json()),
        fetch(`/api/campaigns/all/metrics/impressions?days=${period}`).then(r => r.json()),
        fetch(`/api/campaigns/all/metrics/conversions?days=${period}`).then(r => r.json()),
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
    } catch (error) {
      console.error('Failed to load metrics summary:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate overall CTR
  const ctr = totals.impressions > 0 ? (totals.clicks / totals.impressions) * 100 : 0;

  const metrics = [
    {
      name: 'Total Spend',
      value: `$${totals.spend.toFixed(2)}`,
      icon: '💰',
      color: 'blue',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
      borderColor: 'border-blue-200'
    },
    {
      name: 'Total Clicks',
      value: totals.clicks.toLocaleString(),
      icon: '🖱️',
      color: 'green',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600',
      borderColor: 'border-green-200'
    },
    {
      name: 'Total Impressions',
      value: totals.impressions.toLocaleString(),
      icon: '👁️',
      color: 'purple',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-600',
      borderColor: 'border-purple-200'
    },
    {
      name: 'Average CTR',
      value: `${ctr.toFixed(2)}%`,
      icon: '📊',
      color: 'amber',
      bgColor: 'bg-amber-50',
      textColor: 'text-amber-600',
      borderColor: 'border-amber-200'
    },
    {
      name: 'Total Conversions',
      value: totals.conversions.toFixed(0),
      icon: '✅',
      color: 'emerald',
      bgColor: 'bg-emerald-50',
      textColor: 'text-emerald-600',
      borderColor: 'border-emerald-200'
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
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4">
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

      {/* ROAS Calculator - Inline */}
      <div className="mb-8 flex justify-end">
        <ROASCalculator totalSpend={totals.spend} />
      </div>
    </div>
  );
}
