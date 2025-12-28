import { useState, useEffect } from 'react';
import CampaignList from './components/CampaignList';
import Onboarding from './components/Onboarding';
import SetupInstructions from './components/SetupInstructions';
import Settings from './components/Settings';
import ShopifyAnalytics from './components/ShopifyAnalytics';
import Products from './components/Products';
import MetaAnalytics from './components/MetaAnalytics';
import Login from './components/Login';
import { AuthProvider, useAuth } from './contexts/AuthContext';

function AppContent() {
  const { isAuthenticated, login, logout } = useAuth();
  const [hasData, setHasData] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize page from URL hash
  const getInitialPage = () => {
    const hash = window.location.hash.slice(1); // Remove the '#'
    // Extract just the page name, ignoring query parameters
    const pageName = hash.split('?')[0];
    return pageName || 'dashboard';
  };

  const [currentPage, setCurrentPage] = useState(getInitialPage());

  // Update URL when page changes
  const navigateToPage = (page: string) => {
    window.location.hash = page;
    setCurrentPage(page);
  };

  // Reusable navigation buttons component
  const NavigationButtons = () => (
    <div className="flex items-center space-x-2">
      <button
        onClick={() => navigateToPage('dashboard')}
        className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
          currentPage === 'dashboard'
            ? 'bg-blue-100 text-blue-800'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }`}
        title="Google Ads Dashboard"
      >
        Google Ads
      </button>
      <button
        onClick={() => window.location.reload()}
        className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold hover:bg-gray-200 transition-colors"
        title="Refresh data"
      >
        🔄 Refresh
      </button>
      <button
        onClick={() => navigateToPage('products')}
        className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
          currentPage === 'products'
            ? 'bg-purple-100 text-purple-800'
            : 'bg-purple-50 text-purple-700 hover:bg-purple-100'
        }`}
        title="Shopping Products"
      >
        🏷️ Products
      </button>
      <button
        onClick={() => navigateToPage('meta')}
        className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
          currentPage === 'meta'
            ? 'bg-blue-100 text-blue-800'
            : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
        }`}
        title="Meta Ads"
      >
        📘 Meta Ads
      </button>
      <button
        onClick={() => navigateToPage('shopify')}
        className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
          currentPage === 'shopify'
            ? 'bg-green-100 text-green-800'
            : 'bg-green-50 text-green-700 hover:bg-green-100'
        }`}
        title="Shopify Integration"
      >
        🛍️ Shopify
      </button>
      <button
        onClick={() => navigateToPage('settings')}
        className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold hover:bg-gray-200 transition-colors"
        title="Settings"
      >
        ⚙️ Settings
      </button>
      <button
        onClick={logout}
        className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold hover:bg-red-200 transition-colors"
        title="Logout"
      >
        🚪 Logout
      </button>
    </div>
  );

  // Listen for hash changes (back/forward buttons)
  useEffect(() => {
    const handleHashChange = () => {
      setCurrentPage(getInitialPage());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

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

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <Login onLoginSuccess={login} />;
  }

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

  // Show settings page if requested
  if (currentPage === 'settings') {
    return <Settings onBack={() => navigateToPage('dashboard')} />;
  }

  // Show Shopify analytics page if requested
  if (currentPage === 'shopify') {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Shopify Analytics</h1>
                <p className="mt-1 text-sm text-gray-500">
                  Revenue, orders, and shipping metrics from your Shopify store
                </p>
              </div>
              <NavigationButtons />
            </div>
          </div>
        </header>
        <main>
          <ShopifyAnalytics />
        </main>
      </div>
    );
  }

  // Show Products page if requested
  if (currentPage === 'products') {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Shopping Products</h1>
                <p className="mt-1 text-sm text-gray-500">
                  Product-level performance from Google Shopping campaigns
                </p>
              </div>
              <NavigationButtons />
            </div>
          </div>
        </header>
        <main>
          <Products />
        </main>
      </div>
    );
  }

  // Show Meta analytics page if requested
  if (currentPage === 'meta') {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Meta Ads Analytics</h1>
                <p className="mt-1 text-sm text-gray-500">
                  Campaign performance from your Meta advertising account
                </p>
              </div>
              <NavigationButtons />
            </div>
          </div>
        </header>
        <main>
          <MetaAnalytics />
        </main>
      </div>
    );
  }

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
              <NavigationButtons />
            </div>
          </div>
        </header>

        <main>
          <CampaignList />
        </main>

        <footer className="bg-white border-t mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-gray-500 text-sm">
              Marketing Campaign Tracker - Real-time campaign monitoring
            </p>
          </div>
        </footer>
      </div>
    );
  }

  if (hasData === false) {
    return <SetupInstructions onComplete={() => setHasData(true)} />;
  }

  return <Onboarding onComplete={() => window.location.reload()} />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
