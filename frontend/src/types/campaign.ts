export enum CampaignStatus {
  ENABLED = "ENABLED",
  PAUSED = "PAUSED",
  REMOVED = "REMOVED",
  UNKNOWN = "UNKNOWN",
}

export interface Metric {
  name: string;
  value: number;
  unit: string;
}

export interface Campaign {
  id: string;
  name: string;
  status: CampaignStatus;
  platform: string;
  metrics: Metric[];
}

export interface DataPoint {
  date: string;
  value: number;
}

export interface TimeSeriesData {
  campaign_id: string;
  campaign_name: string;
  metric_name: string;
  unit: string;
  data_points: DataPoint[];
}
