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

  async getMonthlySpend(months: number = 12, startDate?: string): Promise<{ months: Array<{ month: string; spend: number }> }> {
    const params: any = { months };
    if (startDate) params.start_date = startDate;
    const response = await apiClient.get('/api/campaigns/monthly-spend', { params });
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

// Shipping Rules API
export const shippingApi = {
  async getProfiles(activeOnly: boolean = false): Promise<any[]> {
    const response = await apiClient.get('/api/shipping/profiles', {
      params: { active_only: activeOnly }
    });
    return response.data;
  },

  async createProfile(profile: any): Promise<any> {
    const response = await apiClient.post('/api/shipping/profiles', profile);
    return response.data;
  },

  async updateProfile(profileId: string, profile: any): Promise<any> {
    const response = await apiClient.put(`/api/shipping/profiles/${profileId}`, profile);
    return response.data;
  },

  async deleteProfile(profileId: string): Promise<any> {
    const response = await apiClient.delete(`/api/shipping/profiles/${profileId}`);
    return response.data;
  },

  async getProfileUsageCounts(days?: number): Promise<{ counts: Record<string, number> }> {
    const response = await apiClient.get('/api/shipping/profiles/usage-counts', {
      params: days !== undefined ? { days } : {}
    });
    return response.data;
  },

  async testProfile(profile: any, testData: any): Promise<any> {
    const response = await apiClient.post('/api/shipping/profiles/test', {
      profile,
      test_data: testData
    });
    return response.data;
  },
};

// Orders API
export const ordersApi = {
  async getOrders(days: number = 30, status?: string, limit: number = 100, offset: number = 0): Promise<any> {
    const response = await apiClient.get('/api/shopify/orders', {
      params: { days, status, limit, offset }
    });
    return response.data;
  },

  async getOrderDetail(orderId: string): Promise<any> {
    const response = await apiClient.get(`/api/shopify/orders/${orderId}`);
    return response.data;
  },

  async calculateShipping(orderIds: string[]): Promise<any> {
    const response = await apiClient.post('/api/shopify/orders/calculate-shipping', {
      order_ids: orderIds
    });
    return response.data;
  },

  async calculateSingleOrder(orderId: string): Promise<any> {
    const response = await apiClient.post(`/api/shopify/orders/${orderId}/calculate-shipping`);
    return response.data;
  },

  async getMonthlySummary(months: number = 12, startDate?: string): Promise<{ months: Array<{ month: string; revenue: number; shipping_revenue: number; shipping_cost: number; order_count: number }> }> {
    const params: any = { months };
    if (startDate) params.start_date = startDate;
    const response = await apiClient.get('/api/shopify/monthly-summary', { params });
    return response.data;
  },
};

export default apiClient;
