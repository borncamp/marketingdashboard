from datetime import date as DateType
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CampaignStatus(str, Enum):
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"
    UNKNOWN = "UNKNOWN"


class Metric(BaseModel):
    name: str = Field(..., description="Metric name (e.g., 'spend', 'ctr', 'conversions')")
    value: float = Field(..., description="Current metric value")
    unit: str = Field(..., description="Unit of measurement (e.g., 'USD', '%', 'count')")


class DataPoint(BaseModel):
    date: DateType = Field(..., description="Date of the data point")
    value: float = Field(..., description="Metric value for this date")


class TimeSeriesData(BaseModel):
    campaign_id: str = Field(..., description="Campaign identifier")
    campaign_name: str = Field(..., description="Campaign name")
    metric_name: str = Field(..., description="Name of the metric (e.g., 'spend', 'ctr', 'conversions')")
    unit: str = Field(..., description="Unit of measurement")
    data_points: List[DataPoint] = Field(default_factory=list, description="Time series data points")


class Campaign(BaseModel):
    id: str = Field(..., description="Unique campaign identifier")
    name: str = Field(..., description="Campaign name")
    status: CampaignStatus = Field(..., description="Current campaign status")
    platform: str = Field(..., description="Ad platform (e.g., 'google_ads', 'meta_ads', 'reddit_ads')")
    metrics: List[Metric] = Field(default_factory=list, description="Current metrics snapshot")

    class Config:
        use_enum_values = True
