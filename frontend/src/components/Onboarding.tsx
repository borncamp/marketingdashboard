import { useState } from 'react';

interface OnboardingProps {
  onComplete: () => void;
}

type Step = 'welcome' | 'credentials' | 'oauth' | 'validate' | 'complete';

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

export default function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState<Step>('welcome');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [developerToken, setDeveloperToken] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [customerId, setCustomerId] = useState('');
  const [authCode, setAuthCode] = useState('');
  const [refreshToken, setRefreshToken] = useState('');
  const [oauthUrl, setOauthUrl] = useState('');

  const handleGetOAuthUrl = async () => {
    if (!clientId) {
      setError('Please enter Client ID first');
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
      const response = await fetch(`/api/settings/oauth-url?client_id=${encodeURIComponent(clientId)}`, { headers });
      const data = await response.json();
      setOauthUrl(data.url);
      setStep('oauth');
    } catch (err) {
      setError('Failed to generate OAuth URL');
    } finally {
      setLoading(false);
    }
  };

  const handleExchangeCode = async () => {
    if (!authCode || !clientId || !clientSecret) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/settings/exchange-code', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          code: authCode,
          client_id: clientId,
          client_secret: clientSecret
        })
      });

      const data = await response.json();

      if (data.success && data.refresh_token) {
        setRefreshToken(data.refresh_token);
        setStep('validate');
      } else {
        setError('Failed to get refresh token');
      }
    } catch (err) {
      setError('Failed to exchange authorization code');
    } finally {
      setLoading(false);
    }
  };

  const handleValidateAndSave = async () => {
    if (!developerToken || !clientId || !clientSecret || !refreshToken || !customerId) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // First validate
      const validateResponse = await fetch('/api/settings/validate', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          developer_token: developerToken,
          client_id: clientId,
          client_secret: clientSecret,
          refresh_token: refreshToken,
          customer_id: customerId
        })
      });

      const validateData = await validateResponse.json();

      if (!validateData.valid) {
        setError(`Validation failed: ${validateData.message}`);
        setLoading(false);
        return;
      }

      // Then save
      const saveResponse = await fetch('/api/settings', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          google_ads: {
            developer_token: developerToken,
            client_id: clientId,
            client_secret: clientSecret,
            refresh_token: refreshToken,
            customer_id: customerId
          }
        })
      });

      const saveData = await saveResponse.json();

      if (saveData.success) {
        setStep('complete');
        setTimeout(() => {
          onComplete();
        }, 2000);
      } else {
        setError('Failed to save settings');
      }
    } catch (err) {
      setError('An error occurred during setup');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-white rounded-lg shadow-lg p-8">
        {/* Welcome Step */}
        {step === 'welcome' && (
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">Welcome to Marketing Campaign Tracker!</h1>
            <p className="text-gray-600 mb-6">
              Let's get you set up with Google Ads. This wizard will guide you through connecting your Google Ads account in a few simple steps.
            </p>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
              <h3 className="font-semibold text-blue-900 mb-3">📋 What you'll need:</h3>
              <div className="space-y-2 text-blue-800 text-sm">
                <div className="flex items-start">
                  <span className="font-mono bg-blue-100 px-2 py-0.5 rounded mr-2 text-xs">1</span>
                  <div>
                    <strong>Developer Token</strong> - from <a href="https://ads.google.com/aw/apicenter" target="_blank" rel="noopener noreferrer" className="underline">Google Ads API Center</a>
                  </div>
                </div>
                <div className="flex items-start">
                  <span className="font-mono bg-blue-100 px-2 py-0.5 rounded mr-2 text-xs">2</span>
                  <div>
                    <strong>OAuth2 Credentials</strong> - from <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="underline">Google Cloud Console</a>
                  </div>
                </div>
                <div className="flex items-start">
                  <span className="font-mono bg-blue-100 px-2 py-0.5 rounded mr-2 text-xs">3</span>
                  <div>
                    <strong>Customer ID</strong> - from your <a href="https://ads.google.com/" target="_blank" rel="noopener noreferrer" className="underline">Google Ads account</a>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
              <h3 className="font-semibold text-yellow-900 mb-2">⏱️ Time estimate: 10-15 minutes</h3>
              <p className="text-yellow-800 text-sm">
                Each step includes direct links and step-by-step instructions. You can open the links in new tabs and come back to enter the values.
              </p>
            </div>

            <button
              onClick={() => setStep('credentials')}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Get Started
            </button>

            <div className="mt-6 text-sm text-gray-600 bg-gray-50 rounded-lg p-4 border border-gray-200">
              <p className="font-semibold mb-2">💡 First time with Google Ads API?</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>You'll need a <a href="https://ads.google.com/home/tools/manager-accounts/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Manager Account</a> (free) to access the API Center</li>
                <li>Use a <a href="https://developers.google.com/google-ads/api/docs/first-call/dev-token#test_accounts" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">test account</a> for instant developer token approval</li>
                <li>Production tokens can take 24-48 hours for Google to approve</li>
                <li>All credentials are stored encrypted and never shared</li>
              </ul>
            </div>
          </div>
        )}

        {/* Credentials Step */}
        {step === 'credentials' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Enter Your Credentials</h2>
            <p className="text-gray-600 mb-6">
              Enter your Google Ads API credentials. These will be stored securely and encrypted.
            </p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <div className="space-y-6">
              {/* Developer Token */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Developer Token *
                </label>
                <input
                  type="text"
                  value={developerToken}
                  onChange={(e) => setDeveloperToken(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Your developer token"
                />
                <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-3 border border-gray-200">
                  <p className="font-semibold mb-1">
                    📍 <a href="https://ads.google.com/aw/apicenter" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">How to get it →</a>
                  </p>
                  <div className="bg-yellow-50 border border-yellow-200 rounded p-2 mb-2">
                    <p className="text-yellow-800 font-semibold text-xs">⚠️ Requires Manager Account</p>
                    <p className="text-yellow-700 text-xs">API Center only available for Google Ads Manager accounts.</p>
                  </div>
                  <ol className="list-decimal list-inside space-y-0.5 ml-1">
                    <li>Create or use a <a href="https://ads.google.com/home/tools/manager-accounts/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Manager Account</a> (free)</li>
                    <li>Go to <a href="https://ads.google.com/aw/apicenter" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google Ads API Center</a></li>
                    <li>Sign in and apply for developer token</li>
                    <li>For testing: Use test account for instant approval</li>
                    <li>For production: Wait 24-48hrs for Google approval</li>
                  </ol>
                </div>
              </div>

              {/* OAuth Client ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  OAuth Client ID *
                </label>
                <input
                  type="text"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="123456789.apps.googleusercontent.com"
                />
                <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-3 border border-gray-200">
                  <p className="font-semibold mb-1">
                    📍 <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">How to get it →</a>
                  </p>
                  <ol className="list-decimal list-inside space-y-0.5 ml-1">
                    <li>Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google Cloud Console - Credentials</a></li>
                    <li>Create a new project or select existing</li>
                    <li>Enable "Google Ads API" from API Library</li>
                    <li>Click "Create Credentials" → "OAuth client ID"</li>
                    <li>Choose "Desktop app" as application type</li>
                    <li>Copy the Client ID (ends with .apps.googleusercontent.com)</li>
                  </ol>
                </div>
              </div>

              {/* OAuth Client Secret */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  OAuth Client Secret *
                </label>
                <input
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Your client secret"
                />
                <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-3 border border-gray-200">
                  <p className="font-semibold mb-1">
                    📍 <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">How to get it →</a>
                  </p>
                  <ol className="list-decimal list-inside space-y-0.5 ml-1">
                    <li>Same page as Client ID (Google Cloud Console Credentials)</li>
                    <li>Click on your OAuth 2.0 Client ID</li>
                    <li>Copy the "Client secret" value</li>
                    <li>(It's shown alongside the Client ID)</li>
                  </ol>
                </div>
              </div>

              {/* Customer ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Customer ID * (without hyphens)
                </label>
                <input
                  type="text"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value.replace(/-/g, ''))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="1234567890"
                />
                <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-3 border border-gray-200">
                  <p className="font-semibold mb-1">
                    📍 <a href="https://ads.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">How to get it →</a>
                  </p>
                  <ol className="list-decimal list-inside space-y-0.5 ml-1">
                    <li>Go to <a href="https://ads.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google Ads</a></li>
                    <li>Look at the top right corner of the page</li>
                    <li>Find your Customer ID (10 digits, like "123-456-7890")</li>
                    <li>Remove the hyphens: 123-456-7890 → 1234567890</li>
                  </ol>
                </div>
              </div>
            </div>

            <div className="flex space-x-4 mt-6">
              <button
                onClick={() => setStep('welcome')}
                className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              >
                Back
              </button>
              <button
                onClick={handleGetOAuthUrl}
                disabled={loading || !clientId}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Loading...' : 'Continue to Authorization'}
              </button>
            </div>
          </div>
        )}

        {/* OAuth Step */}
        {step === 'oauth' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Authorize Google Ads Access</h2>
            <p className="text-gray-600 mb-6">
              Follow these steps to authorize the application:
            </p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
              <ol className="list-decimal list-inside space-y-2 text-gray-700">
                <li>Click the button below to open Google's authorization page</li>
                <li>Sign in with your Google Ads account</li>
                <li>Grant the requested permissions</li>
                <li>Copy the authorization code Google provides</li>
                <li>Paste it in the box below</li>
              </ol>
            </div>

            <a
              href={oauthUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full px-6 py-3 bg-red-600 text-white text-center rounded-lg hover:bg-red-700 transition-colors font-medium mb-6"
            >
              Open Google Authorization Page →
            </a>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Authorization Code *
              </label>
              <textarea
                value={authCode}
                onChange={(e) => setAuthCode(e.target.value)}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                placeholder="Paste the authorization code here"
              />
            </div>

            <div className="flex space-x-4 mt-6">
              <button
                onClick={() => setStep('credentials')}
                className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              >
                Back
              </button>
              <button
                onClick={handleExchangeCode}
                disabled={loading || !authCode}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Exchanging Code...' : 'Continue'}
              </button>
            </div>
          </div>
        )}

        {/* Validate Step */}
        {step === 'validate' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Ready to Connect!</h2>
            <p className="text-gray-600 mb-6">
              We've obtained your refresh token. Let's validate your credentials and save them.
            </p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-green-700">
                    Refresh token obtained successfully! Click below to validate and save your credentials.
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={handleValidateAndSave}
              disabled={loading}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? 'Validating and Saving...' : 'Validate & Save Settings'}
            </button>
          </div>
        )}

        {/* Complete Step */}
        {step === 'complete' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">All Set!</h2>
            <p className="text-gray-600 mb-6">
              Your Google Ads account is now connected. Loading your campaigns...
            </p>
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          </div>
        )}
      </div>
    </div>
  );
}
