import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TimeSeriesData } from '../types/campaign';

interface CombinationChartProps {
  spendData: TimeSeriesData | null;
  ctrData: TimeSeriesData | null;
  cpcData: TimeSeriesData | null;
}

export default function CombinationChart({ spendData, ctrData, cpcData }: CombinationChartProps) {
  // Get all unique dates from all three datasets
  const getAllDates = () => {
    const dates = new Set<string>();

    if (spendData) {
      spendData.data_points.forEach(p => dates.add(p.date));
    }
    if (ctrData) {
      ctrData.data_points.forEach(p => dates.add(p.date));
    }
    if (cpcData) {
      cpcData.data_points.forEach(p => dates.add(p.date));
    }

    return Array.from(dates).sort();
  };

  // Create a map for quick lookups
  const createDataMap = (data: TimeSeriesData | null) => {
    if (!data) return new Map();
    return new Map(data.data_points.map(p => [p.date, p.value]));
  };

  const spendMap = createDataMap(spendData);
  const ctrMap = createDataMap(ctrData);
  const cpcMap = createDataMap(cpcData);

  const allDates = getAllDates();

  // Combine all data by date
  const chartData = allDates.map(date => ({
    date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    spend: spendMap.get(date) || 0,
    ctr: ctrMap.get(date) || 0,
    cpc: cpcMap.get(date) || 0,
  }));

  const formatTooltip = (value: number, name: string) => {
    if (name === 'spend' || name === 'cpc') {
      return `$${value.toFixed(2)}`;
    } else if (name === 'ctr') {
      return `${value.toFixed(2)}%`;
    }
    return value.toString();
  };

  if (allDates.length === 0) {
    return (
      <div className="w-full h-64 flex items-center justify-center text-gray-500">
        No data available
      </div>
    );
  }

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip formatter={formatTooltip} />
          <Legend />
          {spendData && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="spend"
              stroke="#3b82f6"
              strokeWidth={2}
              name="Spend ($)"
              activeDot={{ r: 6 }}
            />
          )}
          {cpcData && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="cpc"
              stroke="#ec4899"
              strokeWidth={2}
              name="CPC ($)"
              activeDot={{ r: 6 }}
            />
          )}
          {ctrData && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="ctr"
              stroke="#10b981"
              strokeWidth={2}
              name="CTR (%)"
              activeDot={{ r: 6 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
