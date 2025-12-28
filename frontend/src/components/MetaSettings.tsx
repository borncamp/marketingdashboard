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
  const [tokenInfo, setTokenInfo] = useState<{
    type?: string;
    expiresInDays?: number;
    expired?: boolean;
  }>({});
  const [appConfigured, setAppConfigured] = useState(false);
  const [savedAppId, setSavedAppId] = useState('');
  const [metaAppId, setMetaAppId] = useState('');
  const [metaAppSecret, setMetaAppSecret] = useState('');

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
          // Set token expiry info
          setTokenInfo({
            type: data.token_type,
            expiresInDays: data.token_expires_in_days,
            expired: data.token_expired
          });
          setAppConfigured(data.app_configured || false);
          setSavedAppId(data.app_id || '');
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

      const result = await response.json();

      setIsSaved(true);
      setAccessToken('••••••••••••••••');

      // Reload credentials to get updated token info
      await loadSavedCredentials();

      alert(result.message || 'Meta credentials saved securely! Click "Test Connection" to verify.');
    } catch (error) {
      console.error('Error saving credentials:', error);
      alert('Failed to save credentials. Please try again.');
    }
  };

  const saveAppCredentials = async () => {
    if (!metaAppId || !metaAppSecret) {
      alert('Please enter both App ID and App Secret');
      return;
    }

    try {
      const response = await fetch('/api/meta/app-credentials', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          app_id: metaAppId,
          app_secret: metaAppSecret
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save app credentials');
      }

      const result = await response.json();

      // Reload credentials to get the saved app ID
      await loadSavedCredentials();

      setMetaAppId('');
      setMetaAppSecret('');
      alert(result.message || 'App credentials saved! Now save your access token to get a 60-day token.');
    } catch (error) {
      console.error('Error saving app credentials:', error);
      alert('Failed to save app credentials. Please try again.');
    }
  };

  const checkTokenStatus = async () => {
    try {
      const response = await fetch('/api/meta/token-status', {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to check token status');
      }

      const data = await response.json();

      let statusMessage = `Token Type: ${data.token_type}\n`;
      statusMessage += `App Credentials: ${data.app_credentials_configured ? 'Configured ✅' : 'Not Configured ❌'}\n\n`;

      if (data.expiry_info) {
        statusMessage += `Expiry Date: ${new Date(data.expiry_info.expiry_date).toLocaleString()}\n`;
        statusMessage += `Time Remaining: ${data.expiry_info.days_remaining} days, ${data.expiry_info.hours_remaining} hours\n`;
        statusMessage += `Status: ${data.expiry_info.expired ? 'EXPIRED ❌' : 'Active ✅'}`;
      } else {
        statusMessage += 'No expiry information available (token may not have been exchanged)';
      }

      alert(statusMessage);
    } catch (error) {
      console.error('Error checking token status:', error);
      alert('Failed to check token status. Please try again.');
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
      {/* Step 1: App Configuration */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Step 1: App Configuration</h2>
            <p className="text-sm text-gray-600 mt-1">Required for 60-day token lifetime</p>
          </div>
          <div className="flex items-center gap-2">
            {appConfigured && (
              <>
                <span className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                  ✓ Configured
                </span>
                <button
                  onClick={() => {
                    setAppConfigured(false);
                    setMetaAppId(savedAppId);
                    setMetaAppSecret('');
                  }}
                  className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors font-medium"
                >
                  ✏️ Edit
                </button>
              </>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Meta App ID
            </label>
            <input
              type="text"
              value={appConfigured ? savedAppId : metaAppId}
              onChange={(e) => setMetaAppId(e.target.value)}
              placeholder="1234567890123456"
              disabled={appConfigured}
              className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                appConfigured ? 'bg-gray-50 text-gray-500' : 'border-gray-300'
              }`}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Meta App Secret
            </label>
            <input
              type="password"
              value={metaAppSecret}
              onChange={(e) => setMetaAppSecret(e.target.value)}
              placeholder={appConfigured ? "••••••••••••••••" : "abcdef1234567890abcdef1234567890"}
              disabled={appConfigured}
              className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                appConfigured ? 'bg-gray-50 text-gray-500' : 'border-gray-300'
              }`}
            />
          </div>

          {!appConfigured && (
            <>
              <button
                onClick={saveAppCredentials}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                💾 Save App Credentials
              </button>

              <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                <p className="text-xs text-blue-900">
                  <strong>Where to find:</strong> <a href="https://developers.facebook.com/apps/" target="_blank" rel="noopener noreferrer" className="underline">Meta for Developers</a> → Your App → Settings → Basic
                </p>
              </div>
            </>
          )}

          {appConfigured && (
            <div className="p-3 bg-green-50 border border-green-200 rounded">
              <p className="text-sm text-green-900">
                ✅ App configured! Access tokens will be automatically extended to 60 days.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Step 2: Access Token */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Step 2: Access Token</h2>
            <p className="text-sm text-gray-600 mt-1">Generate from Graph API Explorer</p>
          </div>
          {isSaved && (
            <span className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
              ✓ Saved
            </span>
          )}
        </div>

        {/* Token Expiry Warning */}
        {tokenInfo.expired && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <h3 className="text-sm font-semibold text-red-900 mb-1">⚠️ Token Expired</h3>
            <p className="text-xs text-red-800">
              Your Meta access token has expired. Please generate a new token and save it below to continue accessing Meta Ads data.
            </p>
          </div>
        )}

        {tokenInfo.expiresInDays !== undefined && !tokenInfo.expired && tokenInfo.expiresInDays < 7 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <h3 className="text-sm font-semibold text-yellow-900 mb-1">⏰ Token Expiring Soon</h3>
            <p className="text-xs text-yellow-800">
              Your Meta access token will expire in <strong>{tokenInfo.expiresInDays} day{tokenInfo.expiresInDays !== 1 ? 's' : ''}</strong>.
              {tokenInfo.type === 'short-lived' && ' Consider generating a new token to avoid disruption.'}
            </p>
          </div>
        )}

        {/* Token Status Display */}
        {tokenInfo.type && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-900">
                  <strong>Token Status:</strong> {tokenInfo.type === 'long-lived' ? '✅ Long-lived token' : '⚠️ Short-lived token'}
                  {tokenInfo.expiresInDays !== undefined && !tokenInfo.expired && (
                    <span> • Expires in <strong>{tokenInfo.expiresInDays} days</strong></span>
                  )}
                </p>
                {tokenInfo.type === 'short-lived' && !appConfigured && (
                  <p className="text-xs text-blue-800 mt-1">
                    💡 Tip: Configure your Meta App credentials above to automatically get 60-day tokens instead of 1-2 hour tokens.
                  </p>
                )}
              </div>
              <button
                onClick={checkTokenStatus}
                className="ml-4 px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors font-medium whitespace-nowrap"
              >
                🔍 Check Details
              </button>
            </div>
          </div>
        )}

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
              Get from <a href="https://developers.facebook.com/tools/explorer/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Graph API Explorer</a> with ads_read permission
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

      {/* Step 3: Connection Test */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-gray-900">Step 3: Test Connection</h2>
          <p className="text-sm text-gray-600 mt-1">Verify your credentials are working</p>
        </div>

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
      </div>

      {/* Help & Instructions */}
      <div className="space-y-4">
        {/* Initial Setup Guide */}
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="text-sm font-semibold text-blue-900 mb-3">📋 Initial Setup Instructions</h3>
          <ol className="text-xs text-blue-900 space-y-2 list-decimal list-inside">
            <li>
              <strong>Create a Meta App:</strong> Go to <a href="https://developers.facebook.com/apps/" target="_blank" rel="noopener noreferrer" className="underline font-medium">Meta for Developers</a> and create a new app (or use an existing one)
            </li>
            <li>
              <strong>Get App Credentials:</strong> In your app, go to Settings → Basic and copy your <strong>App ID</strong> and <strong>App Secret</strong>
            </li>
            <li>
              <strong>Configure Above:</strong> Paste your App ID and Secret in Step 1 above and save them
            </li>
            <li>
              <strong>Generate User Token:</strong> Go to <a href="https://developers.facebook.com/tools/explorer/" target="_blank" rel="noopener noreferrer" className="underline font-medium">Graph API Explorer</a>, select your app, and generate a user access token with <strong>ads_read</strong> permission
            </li>
            <li>
              <strong>Save Token:</strong> Paste the token in Step 2 above. It will automatically be exchanged for a 60-day token
            </li>
            <li>
              <strong>Grant Access:</strong> In <a href="https://business.facebook.com/settings/ad-accounts" target="_blank" rel="noopener noreferrer" className="underline font-medium">Meta Business Settings</a>, grant your app access to your ad account
            </li>
          </ol>
        </div>

        {/* Token Renewal Guide */}
        <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <h3 className="text-sm font-semibold text-purple-900 mb-3">🔄 Token Renewal (When Token Expires)</h3>
          <ol className="text-xs text-purple-900 space-y-2 list-decimal list-inside">
            <li>
              <strong>When to renew:</strong> You'll see a warning when your token has &lt;7 days remaining or has expired
            </li>
            <li>
              <strong>Generate new token:</strong> Go to <a href="https://developers.facebook.com/tools/explorer/" target="_blank" rel="noopener noreferrer" className="underline font-medium">Graph API Explorer</a> and generate a fresh user token (same as initial setup)
            </li>
            <li>
              <strong>Save new token:</strong> Paste it in Step 2 above and click Save. No need to reconfigure App credentials - they're already saved
            </li>
            <li>
              <strong>Verify:</strong> Click "Test Connection" in Step 3 to confirm the new token works
            </li>
          </ol>
          <p className="text-xs text-purple-800 mt-3 italic">
            💡 Tip: With App credentials configured, tokens automatically extend to 60 days instead of 1-2 hours
          </p>
        </div>

        {/* Troubleshooting */}
        <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
          <h3 className="text-sm font-semibold text-orange-900 mb-2">🔧 Troubleshooting</h3>
          <ul className="text-xs text-orange-900 space-y-1">
            <li>• <strong>Token still short-lived?</strong> Make sure App credentials are configured BEFORE saving the token</li>
            <li>• <strong>Connection test fails?</strong> Verify your app has access to the ad account in Business Settings</li>
            <li>• <strong>Need to change app?</strong> Click "Edit" in Step 1 to update your App ID/Secret</li>
            <li>• <strong>Token expired?</strong> Follow the Token Renewal steps above to get a fresh token</li>
          </ul>
        </div>

        {/* Security Notice */}
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h3 className="text-sm font-semibold text-yellow-900 mb-2">🔒 Security & Privacy</h3>
          <p className="text-xs text-yellow-800">
            All credentials (access token and app secret) are encrypted using industry-standard encryption before storage and can only be accessed with your login credentials. Your App ID is stored unencrypted as it's not sensitive.
          </p>
        </div>
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
