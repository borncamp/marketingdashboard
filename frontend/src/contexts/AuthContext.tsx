import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if credentials exist in sessionStorage
    const credentials = sessionStorage.getItem('authCredentials');
    if (credentials) {
      // Verify credentials are still valid
      verifyCredentials(credentials);
    } else {
      setLoading(false);
    }
  }, []);

  const verifyCredentials = async (credentials: string) => {
    try {
      const response = await fetch('/api/campaigns', {
        headers: {
          'Authorization': `Basic ${credentials}`
        }
      });

      if (response.ok) {
        setIsAuthenticated(true);
      } else {
        sessionStorage.removeItem('authCredentials');
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Failed to verify credentials:', error);
      sessionStorage.removeItem('authCredentials');
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    setIsAuthenticated(true);
  };

  const logout = () => {
    sessionStorage.removeItem('authCredentials');
    setIsAuthenticated(false);
    window.location.hash = '';
    window.location.reload();
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

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
