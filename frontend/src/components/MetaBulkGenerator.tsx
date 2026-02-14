import { useState } from 'react';

interface Product {
  title: string;
  link: string;
  price: string;
  ad_set_budget: number;
  bid_amount: number;
  body_text: string;
  link_description: string;
}

interface PreviewResponse {
  success: boolean;
  total_products: number;
  total_daily_budget: number;
  budget_per_product: number;
  products: Product[];
}

interface ImageUploadStatus {
  job_id: string;
  status: string;
  total_images: number;
  uploaded_images: number;
  failed_images: number;
  progress_percent: number;
}

export default function MetaBulkGenerator() {
  const [feedUrl, setFeedUrl] = useState<string>('');
  const [totalBudget, setTotalBudget] = useState<number>(5);
  const [targetCpc, setTargetCpc] = useState<number>(0.50);
  const [bodyTemplate, setBodyTemplate] = useState<string>('{title} For Sale');
  const [linkDescription, setLinkDescription] = useState<string>('Prices range from $2.25-$5.00 per plant');
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<ImageUploadStatus | null>(null);

  const fetchPreview = async () => {
    if (!feedUrl.trim()) {
      setError('Please enter a feed URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const credentials = sessionStorage.getItem('authCredentials');
      const headers: HeadersInit = {};
      if (credentials) {
        headers['Authorization'] = `Basic ${credentials}`;
      }

      const params = new URLSearchParams({
        feed_url: feedUrl,
        total_budget: totalBudget.toString(),
        target_cpc: targetCpc.toString(),
        body_template: bodyTemplate,
        link_description: linkDescription,
      });

      const response = await fetch(
        `/api/meta-bulk-generator/preview?${params}`,
        { headers }
      );

      if (!response.ok) {
        // Try to parse as JSON first, fall back to text
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Failed to fetch preview';

        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } else {
          const errorText = await response.text();
          errorMessage = errorText || errorMessage;
        }

        throw new Error(errorMessage);
      }

      const data: PreviewResponse = await response.json();
      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setPreview(null);
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = async () => {
    if (!feedUrl.trim()) {
      setError('Please enter a feed URL');
      return;
    }

    try {
      const credentials = sessionStorage.getItem('authCredentials');
      const headers: HeadersInit = {};
      if (credentials) {
        headers['Authorization'] = `Basic ${credentials}`;
      }

      const params = new URLSearchParams({
        feed_url: feedUrl,
        total_budget: totalBudget.toString(),
        target_cpc: targetCpc.toString(),
        body_template: bodyTemplate,
        link_description: linkDescription,
      });

      const response = await fetch(
        `/api/meta-bulk-generator/generate-csv?${params}`,
        { headers }
      );

      if (!response.ok) {
        // Try to parse as JSON first, fall back to text
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Failed to generate CSV';

        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } else {
          const errorText = await response.text();
          errorMessage = errorText || errorMessage;
        }

        throw new Error(errorMessage);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'meta_ads_bulk_import.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download CSV');
    }
  };

  const startImageUpload = async () => {
    if (!feedUrl.trim()) {
      setError('Please enter a feed URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const credentials = sessionStorage.getItem('authCredentials');
      const headers: HeadersInit = {};
      if (credentials) {
        headers['Authorization'] = `Basic ${credentials}`;
      }

      const params = new URLSearchParams({
        feed_url: feedUrl,
      });

      const response = await fetch(
        `/api/meta-bulk-generator/upload-images?${params}`,
        {
          method: 'POST',
          headers
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start image upload');
      }

      const result = await response.json();

      // Start polling for status
      pollUploadStatus(result.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start upload');
    } finally {
      setLoading(false);
    }
  };

  const pollUploadStatus = async (jobId: string) => {
    const credentials = sessionStorage.getItem('authCredentials');
    const headers: HeadersInit = {};
    if (credentials) {
      headers['Authorization'] = `Basic ${credentials}`;
    }

    const poll = async () => {
      try {
        const response = await fetch(
          `/api/meta-bulk-generator/upload-status/${jobId}`,
          { headers }
        );

        if (response.ok) {
          const status: ImageUploadStatus = await response.json();
          setUploadStatus(status);

          // Continue polling if not completed or failed
          if (status.status === 'processing' || status.status === 'pending') {
            setTimeout(poll, 2000); // Poll every 2 seconds
          }
        }
      } catch (err) {
        console.error('Failed to poll upload status:', err);
      }
    };

    poll();
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Meta Ads Bulk Generator</h2>
        <p className="text-gray-600">
          Generate a CSV file to bulk import ads into Meta Ads Manager from your Google Shopping feed.
          Each product becomes one ad with equal budget allocation.
        </p>
      </div>

      {/* Input Section */}
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Feed Configuration</h3>

        <div className="space-y-4">
          {/* Feed URL Input */}
          <div>
            <label htmlFor="feedUrl" className="block text-sm font-medium text-gray-700 mb-2">
              Google Shopping Feed URL (TSV format)
            </label>
            <input
              type="text"
              id="feedUrl"
              value={feedUrl}
              onChange={(e) => setFeedUrl(e.target.value)}
              placeholder="https://example.com/feed.tsv"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Budget Input */}
          <div>
            <label htmlFor="totalBudget" className="block text-sm font-medium text-gray-700 mb-2">
              Total Daily Budget ($)
            </label>
            <input
              type="number"
              id="totalBudget"
              value={totalBudget}
              onChange={(e) => setTotalBudget(parseFloat(e.target.value) || 5)}
              min="1"
              step="1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              Budget will be split equally across all products
            </p>
          </div>

          {/* Target CPC Input */}
          <div>
            <label htmlFor="targetCpc" className="block text-sm font-medium text-gray-700 mb-2">
              Target CPC - Cost Per Click ($)
            </label>
            <input
              type="number"
              id="targetCpc"
              value={targetCpc}
              onChange={(e) => setTargetCpc(parseFloat(e.target.value) || 0.50)}
              min="0.01"
              step="0.01"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              Bid amount for each ad (default: $0.50)
            </p>
          </div>

          {/* Body Template Input */}
          <div>
            <label htmlFor="bodyTemplate" className="block text-sm font-medium text-gray-700 mb-2">
              Body Text Template
            </label>
            <input
              type="text"
              id="bodyTemplate"
              value={bodyTemplate}
              onChange={(e) => setBodyTemplate(e.target.value)}
              placeholder="{title} For Sale"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              Use {'{title}'} as placeholder - clean product name will be extracted automatically
            </p>
          </div>

          {/* Link Description Input */}
          <div>
            <label htmlFor="linkDescription" className="block text-sm font-medium text-gray-700 mb-2">
              Link Description
            </label>
            <input
              type="text"
              id="linkDescription"
              value={linkDescription}
              onChange={(e) => setLinkDescription(e.target.value)}
              placeholder="Prices range from $2.25-$5.00 per plant"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              Same description for all ads
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              onClick={fetchPreview}
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-400"
            >
              {loading ? 'Loading...' : 'Preview Products'}
            </button>
            {preview && (
              <>
                <button
                  onClick={startImageUpload}
                  disabled={loading || (uploadStatus?.status === 'processing')}
                  className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors disabled:bg-gray-400"
                >
                  {uploadStatus?.status === 'processing' ? 'Uploading Images...' : '📸 Upload Images to Meta'}
                </button>
                <button
                  onClick={downloadCSV}
                  className="px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors"
                >
                  📥 Download CSV {uploadStatus?.status === 'completed' ? '(with images)' : ''}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Image Upload Status */}
      {uploadStatus && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">Image Upload Status</h3>

          <div className="mb-4">
            <div className="flex justify-between text-sm text-blue-800 mb-1">
              <span>Progress: {uploadStatus.uploaded_images + uploadStatus.failed_images} / {uploadStatus.total_images}</span>
              <span>{uploadStatus.progress_percent}%</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-4">
              <div
                className="bg-blue-600 h-4 rounded-full transition-all duration-300"
                style={{ width: `${uploadStatus.progress_percent}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-blue-600">Status:</span>
              <span className="ml-2 font-semibold capitalize">{uploadStatus.status}</span>
            </div>
            <div>
              <span className="text-green-600">Uploaded:</span>
              <span className="ml-2 font-semibold text-green-700">{uploadStatus.uploaded_images}</span>
            </div>
            <div>
              <span className="text-red-600">Failed:</span>
              <span className="ml-2 font-semibold text-red-700">{uploadStatus.failed_images}</span>
            </div>
          </div>

          {uploadStatus.status === 'completed' && (
            <div className="mt-4 p-3 bg-green-100 border border-green-300 rounded">
              <p className="text-green-800 font-semibold">✓ Images uploaded successfully! Download the CSV now to get the version with image hashes.</p>
            </div>
          )}

          {uploadStatus.status === 'failed' && (
            <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded">
              <p className="text-red-800 font-semibold">✗ Image upload failed. You can still download the CSV without images.</p>
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Preview Section */}
      {preview && (
        <>
          {/* Summary Card */}
          <div className="bg-white shadow-md rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Preview Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm mb-4">
              <div>
                <span className="text-gray-600">Total Products:</span>
                <span className="ml-2 font-semibold">{preview.total_products}</span>
              </div>
              <div>
                <span className="text-gray-600">Total Daily Budget:</span>
                <span className="ml-2 font-semibold">{formatCurrency(preview.total_daily_budget)}</span>
              </div>
              <div>
                <span className="text-gray-600">Budget Per Product:</span>
                <span className="ml-2 font-semibold">{formatCurrency(preview.budget_per_product)}/day</span>
              </div>
            </div>
            <div className="pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                <span className="font-semibold">Link Description (all ads):</span> {linkDescription}
              </p>
            </div>
          </div>

          {/* Products Table */}
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                Products Preview (showing first {Math.min(100, preview.products.length)} of {preview.total_products})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Product Title
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Body Text
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ad Budget
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      CPC Bid
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {preview.products.map((product, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs">
                        {product.title}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-md">
                        {product.body_text}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {product.price}
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-blue-600">
                        {formatCurrency(product.ad_set_budget)}/day
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-green-600">
                        {formatCurrency(product.bid_amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Instructions */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">How to Use</h3>
        <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
          <li>Paste your Google Shopping feed URL (must be TSV format)</li>
          <li>Set your total daily budget (will be split equally across all products)</li>
          <li>Click "Preview Products" to see what will be generated</li>
          <li>Click "Download CSV" to generate the Meta Ads Manager import file</li>
          <li>Go to Meta Ads Manager → Create → Import & Export → Import Ads</li>
          <li>Upload the CSV file and add product images manually</li>
          <li>Review and publish your ads</li>
        </ol>
      </div>
    </div>
  );
}
