import axios from 'axios';
import { Campaign, TimeSeriesData } from '../types/campaign';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Add request interceptor to include auth credentials from sessionStorage
apiClient.interceptors.request.use(
  (config) => {
    const credentials = sessionStorage.getItem('authCredentials');
    if (credentials) {
      config.headers.Authorization = `Basic ${credentials}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear invalid credentials and reload to login page
      sessionStorage.removeItem('authCredentials');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const campaignApi = {
  async getCampaigns(): Promise<Campaign[]> {
    const response = await apiClient.get<Campaign[]>('/api/campaigns');
    return response.data;
  },

  async getCampaignMetrics(
    campaignId: string,
    metricName: string,
    days: number = 7
  ): Promise<TimeSeriesData> {
    const response = await apiClient.get<TimeSeriesData>(
      `/api/campaigns/${campaignId}/metrics/${metricName}`,
      { params: { days } }
    );
    return response.data;
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/api/settings/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};

export default apiClient;
