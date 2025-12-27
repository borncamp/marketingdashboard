import { useState, useEffect } from 'react';
import { Campaign } from '../types/campaign';
import { campaignApi } from '../services/api';
import CampaignCard from './CampaignCard';
import AllCampaignsChart from './AllCampaignsChart';
import MetricsSummary from './MetricsSummary';

type TimePeriod = 7 | 14 | 30 | 90;

const getUrlPeriod = (): TimePeriod => {
  const hashParts = window.location.hash.split('?');
  const queryString = hashParts.length > 1 ? hashParts[1] : '';
  const params = new URLSearchParams(queryString);
  const period = params.get('days');
  if (period) {
    const parsed = parseInt(period, 10);
    if ([7, 14, 30, 90].includes(parsed)) {
      return parsed as TimePeriod;
    }
  }
  return 7;
};

const updateUrlPeriod = (days: TimePeriod) => {
  const hashParts = window.location.hash.split('?');
  const hashBase = hashParts[0];
  const params = new URLSearchParams(hashParts.length > 1 ? hashParts[1] : '');

  if (days !== 7) {
    params.set('days', days.toString());
  } else {
    params.delete('days');
  }

  const newUrl = params.toString() ?
    `${window.location.pathname}${hashBase}?${params.toString()}` :
    `${window.location.pathname}${hashBase}`;
  window.history.pushState({}, '', newUrl);
};

export default function CampaignList() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>('spend');
  const [period, setPeriod] = useState<TimePeriod>(getUrlPeriod());

  const handlePeriodChange = (newPeriod: TimePeriod) => {
    setPeriod(newPeriod);
    updateUrlPeriod(newPeriod);
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setPeriod(getUrlPeriod());
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const loadCampaigns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await campaignApi.getCampaigns();
      setCampaigns(data);
    } catch (err) {
      setError('Failed to load campaigns. Please check your API credentials and try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 text-lg">Loading campaigns...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border-l-4 border-red-400 p-6 rounded">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-red-800">Error Loading Campaigns</h3>
              <p className="mt-2 text-red-700">{error}</p>
              <button
                onClick={loadCampaigns}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-6 rounded">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-yellow-800">No Campaigns Found</h3>
              <p className="mt-2 text-yellow-700">
                No campaigns were found in your Google Ads account. Make sure your account has active campaigns.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Active Campaigns</h2>
          <p className="mt-2 text-gray-600">
            Monitoring {campaigns.length} campaign{campaigns.length !== 1 ? 's' : ''} across all platforms
          </p>
        </div>
        <button
          onClick={loadCampaigns}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Refresh</span>
        </button>
      </div>

      {/* Metrics Summary */}
      <MetricsSummary campaigns={campaigns} period={period} onPeriodChange={handlePeriodChange} />

      {/* Combo Chart for All Campaigns */}
      <div className="mb-8">
        <div className="mb-4 flex space-x-2">
          {['spend', 'clicks', 'impressions', 'ctr', 'conversions'].map((metric) => (
            <button
              key={metric}
              onClick={() => setSelectedMetric(metric)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedMetric === metric
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50 shadow-sm'
              }`}
            >
              {metric.charAt(0).toUpperCase() + metric.slice(1)}
            </button>
          ))}
        </div>
        <AllCampaignsChart metricName={selectedMetric} days={period} />
      </div>

      {/* Individual Campaign Cards */}
      <div className="mb-4">
        <h3 className="text-2xl font-bold text-gray-900 mb-4">Individual Campaigns</h3>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {campaigns.map((campaign) => (
          <CampaignCard
            key={campaign.id}
            campaign={campaign}
            days={period}
            onDaysChange={(days) => setPeriod(days as TimePeriod)}
          />
        ))}
      </div>
    </div>
  );
}
