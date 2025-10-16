import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { formatDate } from '../lib/api';

interface TopicChartProps {
  data: Array<{
    date: string;
    velocity: number;
    acceleration?: number;
  }>;
  forecastData?: Array<{
    date: string;
    yhat: number;
    yhat_lower?: number;
    yhat_upper?: number;
  }>;
  title?: string;
  height?: number;
}

const TopicChart: React.FC<TopicChartProps> = ({
  data,
  forecastData = [],
  title = "Velocity Trend",
  height = 300
}) => {
  // Combine historical and forecast data
  const allData = [...data, ...forecastData.map(point => ({
    date: point.date,
    velocity: point.yhat,
    isForecast: true,
    forecast_lower: point.yhat_lower,
    forecast_upper: point.yhat_upper,
  }))];

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={allData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(value) => formatDate(value)}
              stroke="#6b7280"
              fontSize={12}
            />
            <YAxis stroke="#6b7280" fontSize={12} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
                      <p className="text-sm text-gray-600 mb-1">
                        {formatDate(label)}
                      </p>
                      <p className="text-sm font-medium">
                        Velocity: {payload[0].value?.toFixed(2)}
                      </p>
                      {data.isForecast && (
                        <p className="text-xs text-blue-600 mt-1">
                          Forecast
                        </p>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />
            
            {/* Forecast confidence band */}
            {forecastData.length > 0 && (
              <Area
                type="monotone"
                dataKey="forecast_upper"
                stroke="none"
                fill="#3b82f6"
                fillOpacity={0.1}
              />
            )}
            
            {/* Main line */}
            <Line
              type="monotone"
              dataKey="velocity"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3, fill: '#3b82f6' }}
              activeDot={{ r: 5, fill: '#1d4ed8' }}
            />
            
            {/* Forecast line */}
            {forecastData.length > 0 && (
              <Line
                type="monotone"
                dataKey="velocity"
                stroke="#1d4ed8"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                connectNulls={false}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      
      <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-primary-600 rounded-full"></div>
            <span>Historical</span>
          </div>
          {forecastData.length > 0 && (
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-primary-600 rounded-full" style={{ background: 'repeating-linear-gradient(45deg, #3b82f6, #3b82f6 2px, transparent 2px, transparent 4px)' }}></div>
              <span>Forecast</span>
            </div>
          )}
        </div>
        <div className="text-xs">
          {data.length} data points
        </div>
      </div>
    </div>
  );
};

export default TopicChart;
