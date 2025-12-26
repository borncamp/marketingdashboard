import { useState, useEffect } from 'react';
import CampaignList from './components/CampaignList';
import Onboarding from './components/Onboarding';
import SetupInstructions from './components/SetupInstructions';

function App() {
  const [hasData, setHasData] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkDataStatus();
  }, []);

  const checkDataStatus = async () => {
    try {
      const response = await fetch('/api/sync/status');
      const data = await response.json();
      setHasData(data.has_data);
    } catch (error) {
      console.error('Failed to check data status:', error);
      setHasData(false);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // If we have data, show the dashboard regardless of configuration
  // (data could come from scripts OR direct API)
  if (hasData === true) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Marketing Campaign Tracker</h1>
                <p className="mt-1 text-sm text-gray-500">
                  Monitor and analyze your advertising campaigns
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
                  Google Ads
                </span>
                <button
                  onClick={() => window.location.reload()}
                  className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold hover:bg-gray-200 transition-colors"
                  title="Refresh data"
                >
                  🔄 Refresh
                </button>
              </div>
            </div>
          </div>
        </header>

        <main>
          <CampaignList />
        </main>

        <footer className="bg-white border-t mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-gray-500 text-sm">
              Marketing Campaign Tracker - Real-time campaign monitoring for Google Ads, Meta Ads, and Reddit Ads
            </p>
          </div>
        </footer>
      </div>
    );
  }

  // No data yet - show setup instructions
  if (hasData === false) {
    return <SetupInstructions onComplete={() => setHasData(true)} />;
  }

  // Fallback: show onboarding for direct API setup
  return <Onboarding onComplete={() => window.location.reload()} />;
}

export default App;
