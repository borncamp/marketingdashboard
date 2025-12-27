import { useState } from 'react';
import { campaignApi } from '../services/api';
import ShopifySettings from './ShopifySettings';

interface SettingsProps {
  onBack: () => void;
}

type SettingsTab = 'password' | 'shopify';

export default function Settings({ onBack }: SettingsProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>('password');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setMessage({ type: 'error', text: 'Please fill in all fields' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }

    if (newPassword.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters long' });
      return;
    }

    if (newPassword === currentPassword) {
      setMessage({ type: 'error', text: 'New password must be different from current password' });
      return;
    }

    setLoading(true);

    try {
      const response = await campaignApi.changePassword(currentPassword, newPassword);

      if (response.success) {
        setMessage({
          type: 'success',
          text: 'Password changed successfully! Please log in again with your new password.'
        });

        // Clear form
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');

        // Redirect to trigger re-authentication after 2 seconds
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to change password. Please try again.';
      setMessage({ type: 'error', text: errorMessage });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <button
              onClick={onBack}
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              ← Back to Dashboard
            </button>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('password')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'password'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🔒 Password
            </button>
            <button
              onClick={() => setActiveTab('shopify')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'shopify'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🛍️ Shopify Integration
            </button>
          </nav>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'password' && (
          <div>
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-5 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Change Password</h2>
            <p className="mt-1 text-sm text-gray-500">
              Update your account password. You'll need to log in again after changing it.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="px-6 py-6 space-y-6">
            {message && (
              <div
                className={`p-4 rounded-md ${
                  message.type === 'success'
                    ? 'bg-green-50 text-green-800 border border-green-200'
                    : 'bg-red-50 text-red-800 border border-red-200'
                }`}
              >
                <p className="text-sm font-medium">{message.text}</p>
              </div>
            )}

            <div>
              <label htmlFor="current-password" className="block text-sm font-medium text-gray-700 mb-2">
                Current Password
              </label>
              <input
                type="password"
                id="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                disabled={loading}
                autoComplete="current-password"
              />
            </div>

            <div>
              <label htmlFor="new-password" className="block text-sm font-medium text-gray-700 mb-2">
                New Password
              </label>
              <input
                type="password"
                id="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                disabled={loading}
                autoComplete="new-password"
              />
              <p className="mt-1 text-sm text-gray-500">Must be at least 8 characters long</p>
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm New Password
              </label>
              <input
                type="password"
                id="confirm-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                disabled={loading}
                autoComplete="new-password"
              />
            </div>

            <div className="flex items-center justify-end space-x-4 pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={onBack}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Changing Password...' : 'Change Password'}
              </button>
            </div>
          </form>
        </div>

        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg px-6 py-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">Security Tips</h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Use a strong password with a mix of letters, numbers, and symbols</li>
            <li>Don't reuse passwords from other accounts</li>
            <li>Change your password regularly (every 90 days recommended)</li>
            <li>Keep your password secure and don't share it with others</li>
          </ul>
        </div>
          </div>
        )}

        {activeTab === 'shopify' && (
          <ShopifySettings onBack={() => {}} />
        )}
      </main>
    </div>
  );
}
