import axios from 'axios';
import { Campaign, TimeSeriesData } from '../types/campaign';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // Enable HTTP Basic Auth
});

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
