import { useState, useEffect } from 'react';
import { TimeSeriesData } from '../types/campaign';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const CAMPAIGN_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
];

interface AllCampaignsChartProps {
  metricName: string;
  days?: number;
}

export default function AllCampaignsChart({ metricName, days = 30 }: AllCampaignsChartProps) {
  const [campaignsData, setCampaignsData] = useState<TimeSeriesData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [metricName, days]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/campaigns/all/metrics/${metricName}?days=${days}`);
      if (!response.ok) {
        throw new Error('Failed to fetch data');
      }
      const data: TimeSeriesData[] = await response.json();
      setCampaignsData(data);
    } catch (err) {
      setError('Failed to load chart data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    );
  }

  if (campaignsData.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
        No data available for this metric
      </div>
    );
  }

  // Transform data for recharts - combine all campaigns by date
  const dateMap = new Map<string, any>();

  campaignsData.forEach((campaignData) => {
    campaignData.data_points.forEach(point => {
      if (!dateMap.has(point.date)) {
        dateMap.set(point.date, { date: point.date });
      }
      const dateEntry = dateMap.get(point.date);
      dateEntry[campaignData.campaign_name] = point.value;
    });
  });

  const chartData = Array.from(dateMap.values()).sort((a, b) =>
    a.date.localeCompare(b.date)
  );

  // Get unit from first campaign
  const unit = campaignsData[0]?.unit || '';

  // Format value based on unit
  const formatValue = (value: number) => {
    if (unit === 'USD') {
      return `$${value.toFixed(2)}`;
    } else if (unit === '%') {
      return `${value.toFixed(2)}%`;
    }
    return value.toFixed(0);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="mb-4">
        <h3 className="text-xl font-bold text-gray-900 capitalize">
          All Campaigns - {metricName}
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Comparing {campaignsData.length} campaign{campaignsData.length !== 1 ? 's' : ''} over {days} days
        </p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            stroke="#6b7280"
            tick={{ fontSize: 12 }}
          />
          <YAxis
            stroke="#6b7280"
            tick={{ fontSize: 12 }}
            tickFormatter={formatValue}
          />
          <Tooltip
            formatter={(value: number) => formatValue(value)}
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px' }}
            iconType="line"
          />
          {campaignsData.map((campaignData, index) => (
            <Line
              key={campaignData.campaign_id}
              type="monotone"
              dataKey={campaignData.campaign_name}
              stroke={CAMPAIGN_COLORS[index % CAMPAIGN_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
