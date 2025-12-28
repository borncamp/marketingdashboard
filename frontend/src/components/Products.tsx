import React, { useState, useEffect } from 'react';
import MetricsChart from './MetricsChart';

interface ProductMetric {
  name: string;
  value: number;
  unit: string;
}

interface Product {
  product_id: string;
  product_title: string;
  campaign_id: string;
  campaign_name: string;
  metrics: ProductMetric[];
  updated_at: string;
}

interface ProductsResponse {
  success: boolean;
  products: Product[];
  total_count: number;
}

// Helper functions for URL parameter management
const getUrlParams = () => {
  // Extract query params from after the hash (e.g., /#products?campaign=foo)
  const hashParts = window.location.hash.split('?');
  const queryString = hashParts.length > 1 ? hashParts[1] : '';
  const params = new URLSearchParams(queryString);
  return {
    campaign: params.get('campaign') || 'all',
    sortBy: (params.get('sortBy') as 'title' | 'clicks' | 'spend' | 'impressions' | 'ctr' | 'cpc' | 'conversions' | 'conversion_value') || 'clicks',
    sortDirection: (params.get('sortDirection') as 'asc' | 'desc') || 'desc'
  };
};

const updateUrlParams = (campaign: string, sortBy: string, sortDirection: string) => {
  const params = new URLSearchParams();
  if (campaign !== 'all') params.set('campaign', campaign);
  if (sortBy !== 'clicks') params.set('sortBy', sortBy);
  if (sortDirection !== 'desc') params.set('sortDirection', sortDirection);

  // Get the hash without any existing query params (e.g., #products)
  const hashBase = window.location.hash.split('?')[0];
  const newUrl = params.toString() ?
    `${window.location.pathname}${hashBase}?${params.toString()}` :
    `${window.location.pathname}${hashBase}`;
  window.history.pushState({}, '', newUrl);
};

export default function Products() {
  const urlParams = getUrlParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'title' | 'clicks' | 'spend' | 'impressions' | 'ctr' | 'cpc' | 'conversions' | 'conversion_value'>(urlParams.sortBy);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(urlParams.sortDirection);
  const [selectedCampaign, setSelectedCampaign] = useState<string>(urlParams.campaign);

  // Column resizing state
  const [columnWidths, setColumnWidths] = useState<{ [key: string]: number }>({
    button: 48,
    product: 200,
    campaign: 128,
    impressions: 96,
    clicks: 80,
    ctr: 80,
    cpc: 80,
    spend: 96,
    conversions: 80,
    conversion_value: 96
  });
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const [resizeStartX, setResizeStartX] = useState<number>(0);
  const [resizeStartWidth, setResizeStartWidth] = useState<number>(0);

  useEffect(() => {
    fetchProducts();

    // Listen for browser back/forward navigation
    const handlePopState = () => {
      const params = getUrlParams();
      setSelectedCampaign(params.campaign);
      setSortBy(params.sortBy);
      setSortDirection(params.sortDirection);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const fetchProducts = async () => {
    try {
      const credentials = sessionStorage.getItem('authCredentials');
      const headers: HeadersInit = {};
      if (credentials) {
        headers['Authorization'] = `Basic ${credentials}`;
      }

      const response = await fetch('/api/products/?days=30', { headers });

      if (!response.ok) {
        throw new Error('Failed to fetch products');
      }

      const data: ProductsResponse = await response.json();
      setProducts(data.products);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getMetricValue = (product: Product, metricName: string): number => {
    const metric = product.metrics.find(m => m.name === metricName);
    return metric ? metric.value : 0;
  };

  const calculateCPC = (product: Product): number => {
    const clicks = getMetricValue(product, 'clicks');
    const spend = getMetricValue(product, 'spend');
    return clicks > 0 ? spend / clicks : 0;
  };

  // Get unique campaigns for filter dropdown
  const campaigns = Array.from(new Set(products.map(p => p.campaign_name).filter(Boolean)))
    .sort();

  // Filter by selected campaign
  const filteredProducts = selectedCampaign === 'all'
    ? products
    : products.filter(p => p.campaign_name === selectedCampaign);

  // Sort filtered products
  const sortedProducts = [...filteredProducts].sort((a, b) => {
    let aValue: number | string;
    let bValue: number | string;

    if (sortBy === 'title') {
      aValue = a.product_title.toLowerCase();
      bValue = b.product_title.toLowerCase();
    } else if (sortBy === 'cpc') {
      aValue = calculateCPC(a);
      bValue = calculateCPC(b);
    } else {
      aValue = getMetricValue(a, sortBy);
      bValue = getMetricValue(b, sortBy);
    }

    const comparison = aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  const handleSort = (column: 'title' | 'clicks' | 'spend' | 'impressions' | 'ctr' | 'cpc' | 'conversions' | 'conversion_value') => {
    let newDirection: 'asc' | 'desc';
    if (sortBy === column) {
      newDirection = sortDirection === 'asc' ? 'desc' : 'asc';
      setSortDirection(newDirection);
    } else {
      setSortBy(column);
      newDirection = 'desc';
      setSortDirection(newDirection);
    }
    updateUrlParams(selectedCampaign, sortBy === column ? sortBy : column, newDirection);
  };

  const toggleExpand = async (productId: string) => {
    if (expandedProduct === productId) {
      setExpandedProduct(null);
    } else {
      setExpandedProduct(productId);
    }
  };

  // Column resizing handlers
  const handleResizeStart = (e: React.MouseEvent, columnName: string) => {
    e.preventDefault();
    setResizingColumn(columnName);
    setResizeStartX(e.clientX);
    setResizeStartWidth(columnWidths[columnName]);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (resizingColumn) {
        const diff = e.clientX - resizeStartX;
        const newWidth = Math.max(50, resizeStartWidth + diff); // Min width of 50px
        setColumnWidths((prev: { [key: string]: number }) => ({
          ...prev,
          [resizingColumn]: newWidth
        }));
      }
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
    };

    if (resizingColumn) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizingColumn, resizeStartX, resizeStartWidth]);

  const formatValue = (value: number, unit: string): string => {
    if (unit === 'USD') {
      return `$${value.toFixed(2)}`;
    } else if (unit === '%') {
      return `${value.toFixed(2)}%`;
    }
    return value.toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading products...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">No Shopping Products Found</h3>
          <p className="text-yellow-700">
            No Shopping campaign data has been synced yet. Make sure you have active Shopping campaigns
            and that the Google Ads script has run successfully.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" style={{ cursor: resizingColumn ? 'col-resize' : 'default' }}>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Shopping Products Performance</h2>
            <p className="text-gray-600">
              Showing {sortedProducts.length} of {products.length} products from Google Shopping campaigns (last 30 days)
            </p>
          </div>

          {campaigns.length > 0 && (
            <div className="flex items-center space-x-2">
              <label htmlFor="campaign-filter" className="text-sm font-medium text-gray-700">
                Campaign:
              </label>
              <select
                id="campaign-filter"
                value={selectedCampaign}
                onChange={(e) => {
                  const newCampaign = e.target.value;
                  setSelectedCampaign(newCampaign);
                  updateUrlParams(newCampaign, sortBy, sortDirection);
                }}
                className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Campaigns</option>
                {campaigns.map((campaign) => (
                  <option key={campaign} value={campaign}>
                    {campaign}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white shadow-md rounded-lg overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-2 py-2 relative" style={{ width: `${columnWidths.button}px` }}>
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => handleResizeStart(e, 'button')} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('title')}
                style={{ width: `${columnWidths.product}px` }}
              >
                Product {sortBy === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'product'); }} />
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative"
                  style={{ width: `${columnWidths.campaign}px` }}>
                Campaign
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => handleResizeStart(e, 'campaign')} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('impressions')}
                style={{ width: `${columnWidths.impressions}px` }}
              >
                Impr. {sortBy === 'impressions' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'impressions'); }} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('clicks')}
                style={{ width: `${columnWidths.clicks}px` }}
              >
                Clicks {sortBy === 'clicks' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'clicks'); }} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('ctr')}
                style={{ width: `${columnWidths.ctr}px` }}
              >
                CTR {sortBy === 'ctr' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'ctr'); }} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('cpc')}
                style={{ width: `${columnWidths.cpc}px` }}
              >
                CPC {sortBy === 'cpc' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'cpc'); }} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('spend')}
                style={{ width: `${columnWidths.spend}px` }}
              >
                Spend {sortBy === 'spend' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'spend'); }} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('conversions')}
                style={{ width: `${columnWidths.conversions}px` }}
              >
                Conv. {sortBy === 'conversions' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'conversions'); }} />
              </th>
              <th
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 relative"
                onClick={() => handleSort('conversion_value')}
                style={{ width: `${columnWidths.conversion_value}px` }}
              >
                Conv. Val. {sortBy === 'conversion_value' && (sortDirection === 'asc' ? '↑' : '↓')}
                <div className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500"
                     onMouseDown={(e) => { e.stopPropagation(); handleResizeStart(e, 'conversion_value'); }} />
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedProducts.map((product) => (
              <>
                <tr key={product.product_id} className="hover:bg-gray-50">
                  <td className="px-2 py-2 text-center">
                    <button
                      onClick={() => toggleExpand(product.product_id)}
                      className="text-blue-600 hover:text-blue-900 text-xs font-medium"
                    >
                      {expandedProduct === product.product_id ? '▼' : '▶'}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <div className="text-sm font-medium text-gray-900 truncate">{product.product_title}</div>
                    <div className="text-xs text-gray-500 truncate">ID: {product.product_id}</div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="text-sm text-gray-900 truncate">{product.campaign_name || 'N/A'}</div>
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {formatValue(getMetricValue(product, 'impressions'), 'count')}
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {formatValue(getMetricValue(product, 'clicks'), 'count')}
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {formatValue(getMetricValue(product, 'ctr'), '%')}
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {formatValue(calculateCPC(product), 'USD')}
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {formatValue(getMetricValue(product, 'spend'), 'USD')}
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {formatValue(getMetricValue(product, 'conversions'), 'count')}
                  </td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {formatValue(getMetricValue(product, 'conversion_value'), 'USD')}
                  </td>
                </tr>
                {expandedProduct === product.product_id && (
                  <tr>
                    <td colSpan={10} className="px-3 py-4 bg-gray-50">
                      <ProductCharts productId={product.product_id} campaignId={product.campaign_id} productTitle={product.product_title} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface ProductChartsProps {
  productId: string;
  campaignId: string;
  productTitle: string;
}

function ProductCharts({ productId, campaignId, productTitle }: ProductChartsProps) {
  const [timeSeriesData, setTimeSeriesData] = useState<{ [key: string]: any }>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAllTimeSeries();
  }, [productId, campaignId]);

  const fetchAllTimeSeries = async () => {
    setLoading(true);
    const metrics = ['clicks', 'spend', 'impressions', 'ctr', 'conversions'];

    const data: { [key: string]: any } = {};

    for (const metric of metrics) {
      try {
        const credentials = sessionStorage.getItem('authCredentials');
        const headers: HeadersInit = {};
        if (credentials) {
          headers['Authorization'] = `Basic ${credentials}`;
        }

        const response = await fetch(
          `/api/products/${productId}/${campaignId}/metrics/${metric}?days=30`,
          { headers }
        );

        if (response.ok) {
          const result = await response.json();
          data[metric] = result.time_series;
        }
      } catch (err) {
        console.error(`Failed to fetch ${metric}:`, err);
      }
    }

    setTimeSeriesData(data);
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Performance Over Time - {productTitle}
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {timeSeriesData.clicks && (
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Clicks</h4>
            <MetricsChart data={timeSeriesData.clicks} color="#3b82f6" />
          </div>
        )}

        {timeSeriesData.spend && (
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Spend</h4>
            <MetricsChart data={timeSeriesData.spend} color="#ef4444" />
          </div>
        )}

        {timeSeriesData.impressions && (
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Impressions</h4>
            <MetricsChart data={timeSeriesData.impressions} color="#8b5cf6" />
          </div>
        )}

        {timeSeriesData.ctr && (
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-2">CTR</h4>
            <MetricsChart data={timeSeriesData.ctr} color="#10b981" />
          </div>
        )}

        {timeSeriesData.conversions && (
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Conversions</h4>
            <MetricsChart data={timeSeriesData.conversions} color="#f59e0b" />
          </div>
        )}
      </div>
    </div>
  );
}
