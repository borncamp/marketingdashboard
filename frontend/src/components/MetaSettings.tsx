import { useState, useEffect } from 'react';

interface MetaSettingsProps {
  onBack: () => void;
}

// Helper function to get auth headers
const getAuthHeaders = (): HeadersInit => {
  const credentials = sessionStorage.getItem('authCredentials');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (credentials) {
    headers['Authorization'] = `Basic ${credentials}`;
  }
  return headers;
};

export default function MetaSettings({ onBack }: MetaSettingsProps) {
  const isEmbedded = !onBack || onBack.toString() === '(() => {})';
  const [accessToken, setAccessToken] = useState('');
  const [adAccountId, setAdAccountId] = useState('');
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSaved, setIsSaved] = useState(false);
  const [accountInfo, setAccountInfo] = useState<any>(null);

  useEffect(() => {
    loadSavedCredentials();
  }, []);

  const loadSavedCredentials = async () => {
    try {
      const response = await fetch('/api/meta/credentials', {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        if (data.configured) {
          setAdAccountId(data.ad_account_id || '');
          setAccessToken('••••••••••••••••');
          setIsSaved(true);
          if (data.account_name) {
            setAccountInfo({
              name: data.account_name,
              currency: data.currency
            });
          }
          return;
        }
      }
    } catch (e) {
      console.error('Failed to load credentials from backend', e);
    }
  };

  const saveCredentials = async () => {
    if (!accessToken || accessToken === '••••••••••••••••') {
      alert('Please enter your access token');
      return;
    }

    if (!adAccountId) {
      alert('Please enter your Ad Account ID');
      return;
    }

    try {
      const response = await fetch('/api/meta/credentials', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          access_token: accessToken,
          ad_account_id: adAccountId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save credentials');
      }

      setIsSaved(true);
      setAccessToken('••••••••••••••••');
      alert('Meta credentials saved securely! Click "Test Connection" to verify.');
    } catch (error) {
      console.error('Error saving credentials:', error);
      alert('Failed to save credentials. Please try again.');
    }
  };

  const testConnection = async () => {
    setConnectionStatus('testing');
    setErrorMessage('');
    setAccountInfo(null);

    try {
      const response = await fetch('/api/meta/verify-connection', {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Connection failed');
      }

      const data = await response.json();
      setAccountInfo(data);
      setConnectionStatus('success');

      setTimeout(() => {
        setConnectionStatus('idle');
      }, 3000);
    } catch (error: any) {
      setConnectionStatus('error');
      setErrorMessage(error.message || 'Connection test failed');
      console.error('Connection test error:', error);
    }
  };

  const content = (
    <div className={isEmbedded ? '' : 'max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
      {/* Setup Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-blue-900 mb-3">📝 Setup Instructions</h2>
        <ol className="space-y-2 text-sm text-blue-800">
          <li>1. Go to <a href="https://developers.facebook.com/apps/" target="_blank" rel="noopener noreferrer" className="underline font-semibold">Meta for Developers</a></li>
          <li>2. Click <strong>Create App</strong> → Choose <strong>Business</strong> type</li>
          <li>3. Name it "Marketing Dashboard" and click <strong>Create App</strong></li>
          <li>4. In the app dashboard, add <strong>Marketing API</strong> product</li>
          <li>5. Go to <strong>Tools</strong> → <strong>Graph API Explorer</strong> (top menu)</li>
          <li>6. In Graph API Explorer:
            <ul className="ml-4 mt-1 space-y-1">
              <li>• Select your app from the <strong>Meta App</strong> dropdown (top right)</li>
              <li>• Click <strong>Generate Access Token</strong> button</li>
              <li>• In the permissions popup, search for and add:</li>
              <li className="ml-4">- <strong>ads_read</strong> (required)</li>
              <li className="ml-4">- <strong>ads_management</strong> (optional, for insights)</li>
              <li>• Click <strong>Generate Access Token</strong> in the popup</li>
              <li>• Approve the permissions when prompted</li>
              <li>• Copy the token from the <strong>Access Token</strong> field</li>
            </ul>
          </li>
          <li>7. Get your Ad Account ID:
            <ul className="ml-4 mt-1 space-y-1">
              <li>• Go to <a href="https://business.facebook.com/settings/ad-accounts" target="_blank" rel="noopener noreferrer" className="underline font-semibold">Meta Business Settings</a></li>
              <li>• Click on your ad account name</li>
              <li>• Copy the <strong>Ad Account ID</strong> (format: act_1234567890)</li>
            </ul>
          </li>
          <li>8. Paste both values in the form below</li>
        </ol>
        <div className="mt-4 p-3 bg-yellow-100 border border-yellow-300 rounded">
          <p className="text-xs text-yellow-900 mb-2">
            <strong>Note:</strong> Use <strong>ads_read</strong> for basic testing. The <strong>ads_management</strong> permission provides access to insights data but may require additional setup.
          </p>
          <p className="text-xs text-yellow-900">
            If you can't find these permissions, make sure your app has the Marketing API product added and you're logged into the Meta account that owns the ad account.
          </p>
        </div>
      </div>

      {/* Credentials Form */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-6">Meta Ads Credentials</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Ad Account ID
            </label>
            <input
              type="text"
              value={adAccountId}
              onChange={(e) => setAdAccountId(e.target.value)}
              placeholder="act_1234567890"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Found in Meta Business Suite → Ad Accounts (starts with "act_")
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Access Token
            </label>
            <input
              type="password"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="EAAxxxxxxxxxxxxxxxxx"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Generated from Graph API Explorer - saved securely encrypted in database
            </p>
          </div>

          <button
            onClick={saveCredentials}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            💾 Save Credentials
          </button>
        </div>
      </div>

      {/* Connection Test */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Connection Test</h2>

        {accountInfo && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-800">
              <strong>Account Name:</strong> {accountInfo.name}
            </p>
            <p className="text-sm text-green-800">
              <strong>Currency:</strong> {accountInfo.currency}
            </p>
          </div>
        )}

        <button
          onClick={testConnection}
          disabled={!isSaved || connectionStatus === 'testing'}
          className={`w-full px-6 py-3 rounded-lg font-medium transition-colors ${
            !isSaved
              ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
              : connectionStatus === 'testing'
              ? 'bg-blue-400 text-white cursor-wait'
              : connectionStatus === 'success'
              ? 'bg-green-600 text-white'
              : connectionStatus === 'error'
              ? 'bg-red-600 text-white'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {connectionStatus === 'idle' && '🔌 Test Connection'}
          {connectionStatus === 'testing' && '⏳ Testing...'}
          {connectionStatus === 'success' && '✅ Connection Successful!'}
          {connectionStatus === 'error' && '❌ Connection Failed'}
        </button>

        {errorMessage && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">
              <strong>Error:</strong> {errorMessage}
            </p>
          </div>
        )}

        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">💡 Tips</h3>
          <ul className="text-xs text-gray-600 space-y-1">
            <li>• Access tokens typically expire in 60 days - you'll need to regenerate them</li>
            <li>• For long-lived tokens, consider upgrading to System User tokens</li>
            <li>• Make sure your Meta app has Marketing API enabled</li>
            <li>• Grant your app access to your ad account in Business Settings</li>
          </ul>
        </div>
      </div>

      {/* Security Notice */}
      <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <h3 className="text-sm font-semibold text-yellow-900 mb-2">🔒 Security Note</h3>
        <p className="text-xs text-yellow-800">
          Your Meta access token is securely stored encrypted in the database.
          Your token is encrypted using industry-standard encryption before storage and can only be accessed with your login credentials.
        </p>
      </div>
    </div>
  );

  if (isEmbedded) {
    return content;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Meta Ads Integration</h1>
              <p className="mt-1 text-sm text-gray-500">
                Connect your Meta advertising account to track campaign performance
              </p>
            </div>
            <button
              onClick={onBack}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              ← Back
            </button>
          </div>
        </div>
      </header>

      <main>
        {content}
      </main>
    </div>
  );
}
