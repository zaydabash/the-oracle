import React from 'react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';

interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
}

const Sparkline: React.FC<SparklineProps> = ({ 
  data, 
  color = '#3b82f6',
  height = 32 
}) => {
  // Convert data to chart format
  const chartData = data.map((value, index) => ({
    index,
    value,
  }));

  if (!chartData.length) {
    return (
      <div 
        className="flex items-center justify-center text-gray-300 text-xs"
        style={{ height }}
      >
        No data
      </div>
    );
  }

  return (
    <div style={{ height, width: 80 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 2 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="bg-gray-800 text-white text-xs px-2 py-1 rounded">
                    {payload[0].value?.toFixed(2)}
                  </div>
                );
              }
              return null;
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Sparkline;
