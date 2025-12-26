import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TimeSeriesData } from '../types/campaign';

interface MetricsChartProps {
  data: TimeSeriesData;
  color?: string;
}

export default function MetricsChart({ data, color = '#3b82f6' }: MetricsChartProps) {
  const chartData = data.data_points.map(point => ({
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: point.value,
  }));

  const formatYAxis = (value: number) => {
    if (data.unit === 'USD') {
      return `$${value.toFixed(2)}`;
    } else if (data.unit === '%') {
      return `${value.toFixed(2)}%`;
    }
    return value.toString();
  };

  const formatTooltip = (value: number) => {
    if (data.unit === 'USD') {
      return `$${value.toFixed(2)}`;
    } else if (data.unit === '%') {
      return `${value.toFixed(2)}%`;
    }
    return value.toString();
  };

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis tickFormatter={formatYAxis} />
          <Tooltip formatter={formatTooltip} />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            name={data.metric_name}
            activeDot={{ r: 8 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
