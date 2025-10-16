import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ExternalLink, TrendingUp, Activity } from 'lucide-react';
import { topicsApi, formatPercentage, formatNumber } from '../lib/api';
import { TopicDetail as TopicDetailType } from '../types';
import TopicChart from '../components/TopicChart';
import ExplainPanel from '../components/ExplainPanel';

const TopicDetail: React.FC = () => {
  const { topicId } = useParams<{ topicId: string }>();

  const { data: topicDetail, isLoading, error } = useQuery({
    queryKey: ['topic-detail', topicId],
    queryFn: () => topicsApi.getDetail(topicId!),
    enabled: !!topicId,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-96 bg-gray-200 rounded"></div>
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !topicDetail) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">Failed to load topic details</div>
        <Link to="/" className="btn-primary">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const data = topicDetail.data as TopicDetailType;

  // Prepare chart data
  const chartData = data.velocity_trend.map((velocity, index) => ({
    date: new Date(Date.now() - (data.velocity_trend.length - index) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    velocity,
    acceleration: data.acceleration_trend[index] || 0,
  }));

  // Get forecast data for 30-day horizon
  const forecastData = data.forecast_curves[30] || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="btn-ghost">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{data.name}</h1>
            <p className="text-gray-600 mt-1">{data.description}</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <Activity className="w-4 h-4" />
            <span>{formatNumber(data.recent_events_count)} events</span>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
              <TrendingUp className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Recent Velocity</p>
              <p className="text-xl font-bold text-gray-900">
                {data.velocity_trend[data.velocity_trend.length - 1]?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-green-100 rounded-lg">
              <Activity className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Acceleration</p>
              <p className="text-xl font-bold text-gray-900">
                {data.acceleration_trend[data.acceleration_trend.length - 1]?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg">
              <ExternalLink className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Active Sources</p>
              <p className="text-xl font-bold text-gray-900">
                {Object.values(data.contributing_sources).filter(count => count > 0).length}/4
              </p>
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-yellow-100 rounded-lg">
              <TrendingUp className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Convergence</p>
              <p className="text-xl font-bold text-gray-900">
                {formatPercentage(Object.values(data.contributing_sources).filter(count => count > 0).length / 4)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Chart */}
        <div className="lg:col-span-1">
          <TopicChart
            data={chartData}
            forecastData={forecastData}
            title={`${data.name} - Velocity Trend & Forecast`}
          />
        </div>

        {/* Explanation Panel */}
        <div className="lg:col-span-1">
          <ExplainPanel
            surgeScore={0.75} // This would come from forecast data
            confidence={0.82}
            velocity={data.velocity_trend[data.velocity_trend.length - 1] || 0}
            acceleration={data.acceleration_trend[data.acceleration_trend.length - 1] || 0}
            convergence={Object.values(data.contributing_sources).filter(count => count > 0).length / 4}
            contributingSources={data.contributing_sources}
            growthRate={0.15} // This would come from forecast data
          />
        </div>
      </div>

      {/* Keywords */}
      {data.keywords && data.keywords.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Topic Keywords</h3>
          <div className="flex flex-wrap gap-2">
            {data.keywords.map((keyword, index) => (
              <span
                key={index}
                className="badge-primary"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Copy Digest Button */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Export Digest</h3>
        <button 
          onClick={() => {
            const t = data;
            const n = data.narrative || "No narrative available";
            const lines = [
              `Topic: ${t.name}`,
              `Surge: ${t.surge_score_pct || (t.surge_score * 100).toFixed(1)}%`,
              `Narrative: ${n}`
            ];
            navigator.clipboard.writeText(lines.join("\n"));
            alert("Digest copied to clipboard!");
          }} 
          className="px-4 py-2 bg-primary-600 text-white rounded-md shadow hover:bg-primary-700 transition-colors"
        >
          Copy Digest
        </button>
      </div>

      {/* Contributing Sources Detail */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Contributing Sources (Last 30 Days)</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(data.contributing_sources).map(([source, count]) => (
          <div key={source} className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl mb-2">
              {source === 'arxiv' && 'Papers'}
              {source === 'github' && 'Code'}
              {source === 'jobs' && 'Jobs'}
              {source === 'funding' && 'Funding'}
            </div>
            <div className="text-sm font-medium text-gray-600 capitalize mb-1">
              {source}
            </div>
            <div className="text-xl font-bold text-gray-900">
              {count}
            </div>
          </div>
        ))}
        </div>
      </div>
    </div>
  );
};

export default TopicDetail;
