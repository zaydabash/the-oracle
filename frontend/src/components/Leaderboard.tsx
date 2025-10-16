import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, Zap, Activity, ArrowUpRight } from 'lucide-react';
import { topicsApi, formatPercentage, getSurgeScoreColor } from '../lib/api';
import { TopicLeaderboardItem } from '../types';
import Sparkline from './Sparkline';

const Leaderboard: React.FC = () => {
  const { data: leaderboard, isLoading, error } = useQuery({
    queryKey: ['leaderboard'],
    queryFn: () => topicsApi.getLeaderboard(30, 20),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="card p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="space-y-3">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <div className="w-8 h-8 bg-gray-200 rounded"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6">
        <div className="text-center text-red-600">
          Failed to load leaderboard. Please try again.
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Top Trending Topics</h2>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <Activity className="w-4 h-4" />
          <span>30-day forecast</span>
        </div>
      </div>

      <div className="space-y-4">
        {leaderboard?.data?.map((item: TopicLeaderboardItem) => (
          <div
            key={item.topic.id}
            className="topic-card p-4 border border-gray-200 rounded-lg hover:border-primary-300 transition-all duration-200"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4 flex-1">
                {/* Rank */}
                <div className="flex items-center justify-center w-8 h-8 bg-primary-100 text-primary-800 rounded-full font-bold text-sm">
                  {item.rank}
                </div>

                {/* Topic Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 truncate">
                    {item.topic.name}
                  </h3>
                  <div className="flex items-center space-x-4 mt-1">
                    <div className="flex items-center space-x-1 text-sm text-gray-500">
                      <TrendingUp className="w-4 h-4" />
                      <span>{formatPercentage(item.velocity)} velocity</span>
                    </div>
                    <div className="flex items-center space-x-1 text-sm text-gray-500">
                      <Zap className="w-4 h-4" />
                      <span>{item.mention_count_30d} mentions</span>
                    </div>
                  </div>
                </div>

                {/* Sparkline */}
                <div className="hidden sm:block">
                  <Sparkline data={item.sparkline_data} />
                </div>
              </div>

              {/* Surge Score */}
              <div className="flex flex-col items-end space-y-1 ml-4">
                <div className={`px-3 py-1 rounded-full text-sm font-medium ${getSurgeScoreColor(item.surge_score)}`}>
                  <span className="font-semibold">{item.surge_score_pct?.toFixed(1) || formatPercentage(item.surge_score)}%</span>
                  <span className="ml-2 text-xs opacity-70" title={
                    item.surge_score_breakdown ? 
                    `Δ30d:${item.surge_score_breakdown.velocity_growth?.toFixed(2)}, ` +
                    `Z:${item.surge_score_breakdown.z_spike?.toFixed(2)}, ` +
                    `Conv:${item.surge_score_breakdown.convergence?.toFixed(2)}, ` +
                    `Unc:${item.surge_score_breakdown.uncertainty_penalty?.toFixed(2)}` :
                    "Surge score breakdown"
                  }>
                    (why?)
                  </span>
                </div>
                <div className="flex items-center space-x-1 text-xs text-gray-500">
                  <ArrowUpRight className="w-3 h-3" />
                  <span>{formatPercentage(item.acceleration)}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {leaderboard?.data?.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No trending topics found. Run the ETL pipeline to generate forecasts.
        </div>
      )}
    </div>
  );
};

export default Leaderboard;
