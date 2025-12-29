import { useState, useEffect } from 'react';
import { Campaign, TimeSeriesData } from '../types/campaign';
import { campaignApi } from '../services/api';
import MetricsChart from './MetricsChart';
import CombinationChart from './CombinationChart';

interface CampaignCardProps {
  campaign: Campaign;
  days: number;
  onDaysChange: (days: number) => void;
}

export default function CampaignCard({ campaign, days, onDaysChange }: CampaignCardProps) {
  const [selectedMetric, setSelectedMetric] = useState<string>('combination');
  const [metricsData, setMetricsData] = useState<TimeSeriesData | null>(null);
  const [combinationData, setCombinationData] = useState<{
    spend: TimeSeriesData | null;
    ctr: TimeSeriesData | null;
    cpc: TimeSeriesData | null;
  }>({ spend: null, ctr: null, cpc: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (selectedMetric === 'combination') {
      loadCombinationData();
    } else {
      loadMetricsData(selectedMetric);
    }
  }, [campaign.id, selectedMetric, days]);

  const loadMetricsData = async (metricName: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await campaignApi.getCampaignMetrics(campaign.id, metricName, days);
      setMetricsData(data);
    } catch (err) {
      setError('Failed to load metrics data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCombinationData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [spendData, ctrData, cpcData] = await Promise.all([
        campaignApi.getCampaignMetrics(campaign.id, 'spend', days),
        campaignApi.getCampaignMetrics(campaign.id, 'ctr', days),
        campaignApi.getCampaignMetrics(campaign.id, 'cpc', days),
      ]);
      setCombinationData({ spend: spendData, ctr: ctrData, cpc: cpcData });
    } catch (err) {
      setError('Failed to load combination data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ENABLED':
        return 'bg-green-100 text-green-800';
      case 'PAUSED':
        return 'bg-yellow-100 text-yellow-800';
      case 'REMOVED':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getMetricValue = (metricName: string) => {
    const metric = campaign.metrics.find(m => m.name === metricName);
    if (!metric) return 'N/A';

    if (metric.unit === 'USD') {
      return `$${metric.value.toFixed(2)}`;
    } else if (metric.unit === '%') {
      return `${metric.value.toFixed(2)}%`;
    }
    return metric.value.toString();
  };

  const metricColors: Record<string, string> = {
    spend: '#3b82f6',
    ctr: '#10b981',
    cpc: '#ec4899',
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-900">{campaign.name}</h3>
          <p className="text-sm text-gray-500 mt-1">
            Platform: <span className="font-medium">{campaign.platform}</span>
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(campaign.status)}`}>
          {campaign.status}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-3 bg-blue-50 rounded">
          <p className="text-xs text-gray-600 mb-1">Spend (7d)</p>
          <p className="text-lg font-bold text-blue-600">{getMetricValue('spend')}</p>
        </div>
        <div className="text-center p-3 bg-green-50 rounded">
          <p className="text-xs text-gray-600 mb-1">CTR (7d avg)</p>
          <p className="text-lg font-bold text-green-600">{getMetricValue('ctr')}</p>
        </div>
        <div className="text-center p-3 bg-pink-50 rounded">
          <p className="text-xs text-gray-600 mb-1">CPC (7d avg)</p>
          <p className="text-lg font-bold text-pink-600">{getMetricValue('cpc')}</p>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex space-x-2">
            {['combination', 'spend', 'cpc', 'ctr'].map((metric) => (
              <button
                key={metric}
                onClick={() => setSelectedMetric(metric)}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  selectedMetric === metric
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {metric.charAt(0).toUpperCase() + metric.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex space-x-1">
            {[7, 14, 30, 90].map((period) => (
              <button
                key={period}
                onClick={() => onDaysChange(period)}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                  days === period
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {period}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {!loading && !error && selectedMetric === 'combination' && (
        <CombinationChart
          spendData={combinationData.spend}
          ctrData={combinationData.ctr}
          cpcData={combinationData.cpc}
        />
      )}

      {!loading && !error && selectedMetric !== 'combination' && metricsData && (
        <MetricsChart data={metricsData} color={metricColors[selectedMetric]} />
      )}
    </div>
  );
}
