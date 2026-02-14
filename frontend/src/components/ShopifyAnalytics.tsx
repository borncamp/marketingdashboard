import { useState, useEffect } from 'react';
import { shippingApi, ordersApi } from '../services/api';

interface ShopifyMetrics {
  total_revenue: number;
  total_shipping_revenue: number;
  total_shipping_cost: number;
  total_orders: number;
  average_order_value: number;
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Shipping Rules State
  const [profiles, setProfiles] = useState<any[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingProfile, setEditingProfile] = useState<any | null>(null);
  const [profilesLoading, setProfilesLoading] = useState(false);
  const [usageCounts, setUsageCounts] = useState<Record<string, number>>({});

  // Orders State
  const [orders, setOrders] = useState<any[]>([]);
  const [orderDays, setOrderDays] = useState<number>(30);
  const [calculating, setCalculating] = useState<string | null>(null);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, [period]);

  useEffect(() => {
    loadProfiles();
  }, []);

  useEffect(() => {
    loadUsageCounts();
    loadOrders();
  }, [orderDays]);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const loadProfiles = async () => {
    try {
      setProfilesLoading(true);
      const data = await shippingApi.getProfiles(false);
      setProfiles(data);
    } catch (err) {
      console.error('Failed to load profiles:', err);
    } finally {
      setProfilesLoading(false);
    }
  };

  const loadUsageCounts = async () => {
    try {
      const countsData = await shippingApi.getProfileUsageCounts(orderDays);
      setUsageCounts(countsData.counts || {});
    } catch (err) {
      console.error('Failed to load usage counts:', err);
    }
  };

  const loadOrders = async () => {
    try {
      setOrdersLoading(true);
      const data = await ordersApi.getOrders(orderDays, undefined, 100, 0);
      setOrders(data.orders || []);
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      setOrdersLoading(false);
    }
  };

  const handleCreateProfile = async (profile: any) => {
    try {
      await shippingApi.createProfile(profile);
      await loadProfiles();
      setShowCreateForm(false);
    } catch (err) {
      alert('Failed to create profile');
      console.error(err);
    }
  };

  const handleEditProfile = async (profile: any) => {
    try {
      await shippingApi.updateProfile(editingProfile.id, profile);
      await loadProfiles();
      setEditingProfile(null);
    } catch (err) {
      alert('Failed to update profile');
      console.error(err);
    }
  };

  const handleDeleteProfile = async (profileId: string) => {
    if (!confirm('Delete this shipping rule?')) return;
    try {
      await shippingApi.deleteProfile(profileId);
      await loadProfiles();
    } catch (err) {
      alert('Failed to delete profile');
      console.error(err);
    }
  };

  const handleCalculateOrder = async (orderId: string) => {
    try {
      setCalculating(orderId);
      await ordersApi.calculateSingleOrder(orderId);
      await loadOrders();
      await loadUsageCounts();
    } catch (err) {
      alert('Failed to calculate shipping cost');
      console.error(err);
    } finally {
      setCalculating(null);
    }
  };

  const handleCalculateAll = async () => {
    try {
      setCalculating('all');
      setSuccessMessage(null);
      const orderIds = orders.map(o => o.id);
      await ordersApi.calculateShipping(orderIds);
      await loadOrders();
      await loadUsageCounts();
      await fetchMetrics();

      // Show success message
      setSuccessMessage(`Successfully calculated shipping costs for ${orderIds.length} orders`);

      // Auto-hide success message after 5 seconds
      setTimeout(() => {
        setSuccessMessage(null);
      }, 5000);
    } catch (err) {
      alert('Failed to calculate shipping costs');
      console.error(err);
    } finally {
      setCalculating(null);
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

      {/* SECTION 2: Shipping Rules Manager */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Shipping Rules</h2>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            + Create Rule
          </button>
        </div>

        {profilesLoading ? (
          <div className="text-center py-8 text-gray-600">Loading rules...</div>
        ) : profiles.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <p className="text-yellow-800">No shipping rules yet. Create your first rule to start calculating shipping costs.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Field</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Operator</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Active</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applied</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {profiles.map((profile) => (
                  <tr key={profile.id} className={!profile.is_active ? 'opacity-50' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{profile.priority}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{profile.name}</div>
                      {profile.description && <div className="text-xs text-gray-500">{profile.description}</div>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{profile.match_conditions?.field || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{profile.match_conditions?.operator || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{profile.match_conditions?.value || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{profile.cost_rules?.type || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${profile.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                        {profile.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {usageCounts[profile.id] || 0}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <button
                        onClick={() => setEditingProfile(profile)}
                        className="text-blue-600 hover:text-blue-900 mr-4"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteProfile(profile.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Create/Edit Rule Form Modal */}
        {(showCreateForm || editingProfile) && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <h3 className="text-lg font-bold mb-4">{editingProfile ? 'Edit Shipping Rule' : 'Create Shipping Rule'}</h3>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const formData = new FormData(e.currentTarget);
                  const costType = formData.get('cost_type') as string;
                  const baseCost = parseFloat(formData.get('base_cost') as string) || 0;

                  // Build cost_rules based on type
                  const costRules: any = { type: costType };

                  if (costType === 'fixed') {
                    costRules.base_cost = baseCost;
                  } else if (costType === 'per_item') {
                    costRules.per_item_cost = baseCost;
                  } else if (costType === 'percentage') {
                    costRules.percentage = baseCost;
                  } else if (costType === 'based_on_shipping_charged') {
                    costRules.adjustment = baseCost;
                  }

                  const profile = {
                    name: formData.get('name'),
                    description: formData.get('description'),
                    priority: parseInt(formData.get('priority') as string),
                    is_active: formData.get('is_active') === 'on',
                    match_conditions: {
                      field: formData.get('match_field'),
                      operator: formData.get('operator'),
                      value: formData.get('match_value'),
                      case_sensitive: false
                    },
                    cost_rules: costRules
                  };

                  if (editingProfile) {
                    handleEditProfile(profile);
                  } else {
                    handleCreateProfile(profile);
                  }
                }}
              >
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name</label>
                    <input
                      name="name"
                      required
                      className="w-full px-3 py-2 border rounded-lg"
                      placeholder="e.g., 2-Plug Items"
                      defaultValue={editingProfile?.name || ''}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
                    <input
                      name="description"
                      className="w-full px-3 py-2 border rounded-lg"
                      defaultValue={editingProfile?.description || ''}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Priority (lower = higher priority)</label>
                    <input
                      name="priority"
                      type="number"
                      required
                      defaultValue={editingProfile?.priority || 100}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="flex items-center">
                      <input
                        name="is_active"
                        type="checkbox"
                        defaultChecked={editingProfile?.is_active !== false}
                        className="mr-2"
                      />
                      <span className="text-sm font-medium text-gray-700">Active</span>
                    </label>
                  </div>

                  <hr className="my-4" />
                  <h4 className="font-semibold">Match Conditions</h4>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Field</label>
                      <select
                        name="match_field"
                        required
                        className="w-full px-3 py-2 border rounded-lg"
                        defaultValue={editingProfile?.match_conditions?.field || 'product_title'}
                      >
                        <option value="product_title">Product Title</option>
                        <option value="variant_title">Variant Title</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Operator</label>
                      <select
                        name="operator"
                        required
                        className="w-full px-3 py-2 border rounded-lg"
                        defaultValue={editingProfile?.match_conditions?.operator || 'contains'}
                      >
                        <option value="contains">Contains</option>
                        <option value="equals">Equals</option>
                        <option value="starts_with">Starts With</option>
                        <option value="ends_with">Ends With</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Value</label>
                      <input
                        name="match_value"
                        required
                        className="w-full px-3 py-2 border rounded-lg"
                        placeholder="e.g., 2 plug"
                        defaultValue={editingProfile?.match_conditions?.value || ''}
                      />
                    </div>
                  </div>

                  <hr className="my-4" />
                  <h4 className="font-semibold">Cost Calculation</h4>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Cost Type</label>
                      <select
                        name="cost_type"
                        required
                        className="w-full px-3 py-2 border rounded-lg"
                        defaultValue={editingProfile?.cost_rules?.type || 'fixed'}
                        onChange={(e) => {
                          const costInput = e.target.closest('form')?.querySelector('#cost_input') as HTMLInputElement;
                          const costLabel = e.target.closest('form')?.querySelector('#cost_input_label') as HTMLElement;

                          if (e.target.value === 'based_on_shipping_charged') {
                            if (costLabel) costLabel.textContent = 'Adjustment ($)';
                            if (costInput) costInput.placeholder = '-5 (for shipping_charged - $5)';
                          } else if (e.target.value === 'percentage') {
                            if (costLabel) costLabel.textContent = 'Percentage (%)';
                            if (costInput) costInput.placeholder = '10';
                          } else if (e.target.value === 'per_item') {
                            if (costLabel) costLabel.textContent = 'Cost per Item ($)';
                            if (costInput) costInput.placeholder = '5.00';
                          } else {
                            if (costLabel) costLabel.textContent = 'Base Cost ($)';
                            if (costInput) costInput.placeholder = '0';
                          }
                        }}
                      >
                        <option value="fixed">Fixed Cost</option>
                        <option value="per_item">Per Item</option>
                        <option value="percentage">Percentage of Subtotal</option>
                        <option value="based_on_shipping_charged">Based on Shipping Charged</option>
                      </select>
                    </div>
                    <div id="cost-input-container">
                      <label id="cost_input_label" className="block text-sm font-medium text-gray-700 mb-1">
                        {editingProfile?.cost_rules?.type === 'based_on_shipping_charged' ? 'Adjustment ($)' :
                         editingProfile?.cost_rules?.type === 'percentage' ? 'Percentage (%)' :
                         editingProfile?.cost_rules?.type === 'per_item' ? 'Cost per Item ($)' :
                         'Base Cost ($)'}
                      </label>
                      <input
                        id="cost_input"
                        name="base_cost"
                        type="number"
                        step="0.01"
                        required
                        className="w-full px-3 py-2 border rounded-lg"
                        defaultValue={
                          editingProfile?.cost_rules?.type === 'fixed' ? editingProfile.cost_rules.base_cost :
                          editingProfile?.cost_rules?.type === 'per_item' ? editingProfile.cost_rules.per_item_cost :
                          editingProfile?.cost_rules?.type === 'percentage' ? editingProfile.cost_rules.percentage :
                          editingProfile?.cost_rules?.type === 'based_on_shipping_charged' ? editingProfile.cost_rules.adjustment :
                          0
                        }
                        placeholder="0"
                      />
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateForm(false);
                      setEditingProfile(null);
                    }}
                    className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                    {editingProfile ? 'Update Rule' : 'Create Rule'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 3: Orders Table */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Orders</h2>
          <div className="flex items-center space-x-4">
            <select
              value={orderDays}
              onChange={(e) => setOrderDays(parseInt(e.target.value))}
              className="px-3 py-2 border rounded-lg"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={handleCalculateAll}
              disabled={calculating === 'all' || orders.length === 0}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all"
            >
              {calculating === 'all' ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Calculating...
                </span>
              ) : 'Calculate All Orders'}
            </button>
          </div>
        </div>

        {/* Rules Applied Summary */}
        {profiles.length > 0 && Object.keys(usageCounts).length > 0 && (
          <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Rules applied (last {orderDays} days)</h4>
            <div className="flex flex-wrap gap-3">
              {profiles
                .filter((p) => usageCounts[p.id])
                .map((p) => (
                  <div key={p.id} className="flex items-center space-x-1.5 bg-white border border-gray-200 rounded-full px-3 py-1">
                    <span className="text-sm text-gray-700">{p.name}</span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {usageCounts[p.id]}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Success Message Banner */}
        {successMessage && (
          <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between animate-fade-in">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
              </svg>
              <span className="text-green-800 font-medium">{successMessage}</span>
            </div>
            <button
              onClick={() => setSuccessMessage(null)}
              className="text-green-600 hover:text-green-800"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        )}

        {ordersLoading ? (
          <div className="text-center py-8 text-gray-600">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <p className="text-yellow-800">No orders found. Sync your Shopify data to see orders here.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Order #</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subtotal</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shipping Charged</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Est. Cost</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Difference</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {orders.map((order) => {
                  const diff = order.shipping_cost_estimated !== null && order.shipping_cost_estimated !== undefined
                    ? order.shipping_charged - order.shipping_cost_estimated
                    : null;

                  return (
                    <tr key={order.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">#{order.order_number}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{order.order_date}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${order.subtotal.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${order.shipping_charged.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {order.shipping_cost_estimated !== null && order.shipping_cost_estimated !== undefined
                          ? `$${order.shipping_cost_estimated.toFixed(2)}`
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {diff !== null ? (
                          <span className={diff >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ${diff.toFixed(2)}
                          </span>
                        ) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <button
                          onClick={() => handleCalculateOrder(order.id)}
                          disabled={calculating === order.id}
                          className="text-blue-600 hover:text-blue-900 disabled:text-gray-400"
                        >
                          {calculating === order.id ? 'Calculating...' : 'Calculate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
