import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TimeSeriesData } from '../types/campaign';

interface MetricsChartProps {
  data: TimeSeriesData;
  color?: string;
}

export default function MetricsChart({ data, color = '#3b82f6' }: MetricsChartProps) {
  // Fill in missing dates with zero values
  const fillMissingDates = (dataPoints: typeof data.data_points) => {
    if (dataPoints.length === 0) return [];

    // Create a map of existing data points
    const dataMap = new Map(dataPoints.map(p => [p.date, p.value]));

    // Find the date range from the actual data
    const dates = dataPoints.map(p => new Date(p.date));
    const minDate = new Date(Math.min(...dates.map(d => d.getTime())));
    const maxDate = new Date(Math.max(...dates.map(d => d.getTime())));

    // Generate all dates in the range
    const filledData = [];
    const currentDate = new Date(minDate);

    while (currentDate <= maxDate) {
      const dateStr = currentDate.toISOString().split('T')[0];

      filledData.push({
        date: dateStr,
        value: dataMap.get(dateStr) || 0,
        unit: data.unit
      });

      currentDate.setDate(currentDate.getDate() + 1);
    }

    return filledData;
  };

  const filledDataPoints = fillMissingDates(data.data_points);

  const chartData = filledDataPoints.map(point => ({
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
          margin={{ top: 5, right: 70, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            angle={-45}
            textAnchor="end"
            height={80}
            interval={0}
          />
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
