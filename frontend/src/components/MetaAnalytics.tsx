import { useState, useEffect } from 'react';

interface MetaCampaign {
  id: string;
  name: string;
  status: string;
  objective: string;
  spend: number;
  impressions: number;
  clicks: number;
  reach: number;
  ctr: number;
  conversions: number;
  conversion_value: number;
  roas: number;
}

interface MetaAdSet {
  id: string;
  name: string;
  status: string;
  optimization_goal: string;
  billing_event: string;
  spend: number;
  impressions: number;
  clicks: number;
  reach: number;
  ctr: number;
  conversions: number;
  conversion_value: number;
  roas: number;
}

const getAuthHeaders = (): HeadersInit => {
  const credentials = sessionStorage.getItem('authCredentials');
  const headers: HeadersInit = {};
  if (credentials) {
    headers['Authorization'] = `Basic ${credentials}`;
  }
  return headers;
};

export default function MetaAnalytics() {
  const [campaigns, setCampaigns] = useState<MetaCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<7 | 14 | 30 | 90>(30);
  const [expandedCampaign, setExpandedCampaign] = useState<string | null>(null);
  const [adSets, setAdSets] = useState<{ [campaignId: string]: MetaAdSet[] }>({});
  const [hideInactive, setHideInactive] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<any>(null);

  useEffect(() => {
    checkSyncStatus();
    fetchCampaigns();
  }, [period]);

  const checkSyncStatus = async () => {
    try {
      const response = await fetch('/api/meta/sync/status', {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setSyncStatus(data);
      }
    } catch (err) {
      console.error('Failed to check sync status:', err);
    }
  };

  const syncCampaigns = async () => {
    setSyncing(true);
    setError(null);

    try {
      const response = await fetch(`/api/meta/sync?days=${period}`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to sync campaigns');
      }

      const data = await response.json();

      // Refresh campaigns and sync status after successful sync
      await fetchCampaigns();
      await checkSyncStatus();

      alert(`Successfully synced ${data.campaigns_synced} campaigns with ${data.metrics_synced} metrics!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      alert(`Sync failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setSyncing(false);
    }
  };

  const fetchCampaigns = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/meta/campaigns?days=${period}`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to fetch campaigns');
      }

      const data = await response.json();
      setCampaigns(data.campaigns || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const toggleCampaign = async (campaignId: string) => {
    if (expandedCampaign === campaignId) {
      setExpandedCampaign(null);
      return;
    }

    setExpandedCampaign(campaignId);

    // Fetch ad sets if not already loaded
    if (!adSets[campaignId]) {
      try {
        const response = await fetch(`/api/meta/campaigns/${campaignId}/adsets?days=${period}`, {
          headers: getAuthHeaders()
        });

        if (response.ok) {
          const data = await response.json();
          setAdSets(prev => ({
            ...prev,
            [campaignId]: data.adsets || []
          }));
        }
      } catch (err) {
        console.error('Failed to fetch ad sets:', err);
      }
    }
  };

  const formatCurrency = (value: number) => `$${value.toFixed(2)}`;
  const formatNumber = (value: number) => value.toLocaleString();

  // Filter campaigns based on hideInactive toggle
  const filteredCampaigns = hideInactive
    ? campaigns.filter(c => c.status === 'ACTIVE')
    : campaigns;

  // Calculate totals from filtered campaigns
  const totals = filteredCampaigns.reduce((acc, campaign) => {
    acc.spend += campaign.spend;
    acc.impressions += campaign.impressions;
    acc.clicks += campaign.clicks;
    acc.reach += campaign.reach;
    acc.conversions += campaign.conversions;
    acc.conversion_value += campaign.conversion_value;
    return acc;
  }, {
    spend: 0,
    impressions: 0,
    clicks: 0,
    reach: 0,
    conversions: 0,
    conversion_value: 0
  });

  const avgCTR = totals.impressions > 0 ? (totals.clicks / totals.impressions * 100) : 0;
  const totalROAS = totals.spend > 0 ? (totals.conversion_value / totals.spend) : 0;

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading Meta campaigns...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Campaigns</h3>
          <p className="text-red-700">{error}</p>
          <p className="text-sm text-red-600 mt-2">
            Make sure you've configured your Meta credentials in Settings.
          </p>
        </div>
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Meta Ad Campaigns</h2>
            <p className="text-gray-600 mt-1">
              Performance overview of your Meta advertising campaigns
              {syncStatus?.synced && syncStatus.last_sync_at && (
                <span className="text-xs ml-2">
                  • Last synced: {new Date(syncStatus.last_sync_at).toLocaleString()}
                </span>
              )}
            </p>
          </div>
          <button
            onClick={syncCampaigns}
            disabled={syncing}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              syncing
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {syncing ? '⟳ Syncing...' : '↻ Sync from Meta'}
          </button>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">No Campaigns Found</h3>
          <p className="text-yellow-700 mb-4">
            {syncStatus?.synced
              ? "No campaigns found in database. Your Meta ad account may not have any campaigns yet."
              : "No campaigns in database yet. Click 'Sync from Meta' above to fetch your campaigns."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Period Toggle and Controls */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Meta Ad Campaigns</h2>
          <p className="text-gray-600 mt-1">
            Performance overview of your Meta advertising campaigns
            {syncStatus?.synced && syncStatus.last_sync_at && (
              <span className="text-xs ml-2">
                • Last synced: {new Date(syncStatus.last_sync_at).toLocaleString()}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={syncCampaigns}
            disabled={syncing}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              syncing
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {syncing ? '⟳ Syncing...' : '↻ Sync from Meta'}
          </button>
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
          <button
            onClick={() => setHideInactive(!hideInactive)}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              hideInactive
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {hideInactive ? '✓ Active Only' : 'Show All'}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">💰</span>
            <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">
              Total Spend
            </span>
          </div>
          <div className="text-3xl font-bold text-blue-600 mb-1">
            {formatCurrency(totals.spend)}
          </div>
          <div className="text-xs text-gray-500">Last {period} days</div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">👁️</span>
            <span className="text-xs font-semibold text-purple-600 uppercase tracking-wide">
              Impressions
            </span>
          </div>
          <div className="text-3xl font-bold text-purple-600 mb-1">
            {formatNumber(totals.impressions)}
          </div>
          <div className="text-xs text-gray-500">Total views</div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">🎯</span>
            <span className="text-xs font-semibold text-green-600 uppercase tracking-wide">
              Conversions
            </span>
          </div>
          <div className="text-3xl font-bold text-green-600 mb-1">
            {formatNumber(totals.conversions)}
          </div>
          <div className="text-xs text-gray-500">{formatCurrency(totals.conversion_value)} value</div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">📈</span>
            <span className="text-xs font-semibold text-orange-600 uppercase tracking-wide">
              ROAS
            </span>
          </div>
          <div className="text-3xl font-bold text-orange-600 mb-1">
            {totalROAS.toFixed(2)}x
          </div>
          <div className="text-xs text-gray-500">Return on ad spend</div>
        </div>
      </div>

      {/* Campaigns Table */}
      <div className="bg-white shadow-md rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-2 py-3 w-12"></th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Campaign
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Spend
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Impressions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Clicks
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                CTR
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                CPC
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Conversions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ROAS
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredCampaigns.map((campaign) => (
              <>
                <tr key={campaign.id} className="hover:bg-gray-50">
                  <td className="px-2 py-4 text-center">
                    <button
                      onClick={() => toggleCampaign(campaign.id)}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      {expandedCampaign === campaign.id ? '▼' : '▶'}
                    </button>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{campaign.name}</div>
                    <div className="text-xs text-gray-500">{campaign.objective}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      campaign.status === 'ACTIVE'
                        ? 'bg-green-100 text-green-800'
                        : campaign.status === 'PAUSED'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {campaign.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {formatCurrency(campaign.spend)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {formatNumber(campaign.impressions)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {formatNumber(campaign.clicks)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {campaign.ctr.toFixed(2)}%
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {campaign.clicks > 0 ? formatCurrency(campaign.spend / campaign.clicks) : '$0.00'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {formatNumber(campaign.conversions)}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`font-semibold ${
                      campaign.roas >= 2 ? 'text-green-600' :
                      campaign.roas >= 1 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {campaign.roas.toFixed(2)}x
                    </span>
                  </td>
                </tr>

                {/* Ad Sets Expanded View */}
                {expandedCampaign === campaign.id && adSets[campaign.id] && (() => {
                  const filteredAdSets = hideInactive
                    ? adSets[campaign.id].filter(a => a.status === 'ACTIVE')
                    : adSets[campaign.id];

                  return (
                    <tr>
                      <td colSpan={10} className="px-0 py-0">
                        <div className="bg-gray-50 px-8 py-4">
                          <h4 className="text-sm font-semibold text-gray-700 mb-3">Ad Sets</h4>
                          <table className="min-w-full">
                            <thead>
                              <tr className="text-xs text-gray-500">
                                <th className="px-4 py-2 text-left">Ad Set Name</th>
                                <th className="px-4 py-2 text-left">Status</th>
                                <th className="px-4 py-2 text-left">Optimization</th>
                                <th className="px-4 py-2 text-left">Spend</th>
                                <th className="px-4 py-2 text-left">Impressions</th>
                                <th className="px-4 py-2 text-left">Clicks</th>
                                <th className="px-4 py-2 text-left">CTR</th>
                                <th className="px-4 py-2 text-left">CPC</th>
                                <th className="px-4 py-2 text-left">Conv.</th>
                                <th className="px-4 py-2 text-left">ROAS</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                              {filteredAdSets.map((adset) => (
                              <tr key={adset.id} className="hover:bg-white">
                                <td className="px-4 py-3 text-sm text-gray-900">{adset.name}</td>
                                <td className="px-4 py-3">
                                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                    adset.status === 'ACTIVE'
                                      ? 'bg-green-100 text-green-800'
                                      : adset.status === 'PAUSED'
                                      ? 'bg-yellow-100 text-yellow-800'
                                      : 'bg-gray-100 text-gray-800'
                                  }`}>
                                    {adset.status}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-xs text-gray-600">{adset.optimization_goal}</td>
                                <td className="px-4 py-3 text-sm text-gray-900">{formatCurrency(adset.spend)}</td>
                                <td className="px-4 py-3 text-sm text-gray-900">{formatNumber(adset.impressions)}</td>
                                <td className="px-4 py-3 text-sm text-gray-900">{formatNumber(adset.clicks)}</td>
                                <td className="px-4 py-3 text-sm text-gray-900">{adset.ctr.toFixed(2)}%</td>
                                <td className="px-4 py-3 text-sm text-gray-900">
                                  {adset.clicks > 0 ? formatCurrency(adset.spend / adset.clicks) : '$0.00'}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-900">{formatNumber(adset.conversions)}</td>
                                <td className="px-4 py-3 text-sm">
                                  <span className={`font-semibold ${
                                    adset.roas >= 2 ? 'text-green-600' :
                                    adset.roas >= 1 ? 'text-yellow-600' :
                                    'text-red-600'
                                  }`}>
                                    {adset.roas.toFixed(2)}x
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                  );
                })()}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary Footer */}
      <div className="mt-4 text-sm text-gray-600 text-center">
        Showing {filteredCampaigns.length} campaigns • Total spend: {formatCurrency(totals.spend)} •
        Avg CTR: {avgCTR.toFixed(2)}% • Total ROAS: {totalROAS.toFixed(2)}x
      </div>
    </div>
  );
}
