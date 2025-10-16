import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, TrendingUp, BarChart3, Clock } from 'lucide-react';
import { healthApi, formatNumber } from '../lib/api';
import Leaderboard from '../components/Leaderboard';

const Dashboard: React.FC = () => {
  const { data: healthData } = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.check(),
    refetchInterval: 30000,
  });

  const stats = healthData?.data?.statistics;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Oracle Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time intelligence on emerging technology trends
          </p>
        </div>
        
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span>System Online</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Topics</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(stats?.total_topics || 0)}
              </p>
            </div>
            <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg">
              <BarChart3 className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Signal Events</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(stats?.total_events || 0)}
              </p>
            </div>
            <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg">
              <Activity className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Active Forecasts</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(stats?.total_forecasts || 0)}
              </p>
            </div>
            <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Last Updated</p>
              <p className="text-2xl font-bold text-gray-900">
                <Clock className="w-6 h-6 inline mr-1" />
                Now
              </p>
            </div>
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-lg">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Leaderboard */}
        <div className="lg:col-span-1">
          <Leaderboard />
        </div>

        {/* Quick Stats & Info */}
        <div className="lg:col-span-1 space-y-6">
          {/* System Status */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Database</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span className="text-sm text-green-600">Connected</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">ETL Pipeline</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span className="text-sm text-green-600">Running</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Forecast Engine</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span className="text-sm text-green-600">Active</span>
                </div>
              </div>
            </div>
          </div>

          {/* Data Sources */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Sources</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-lg text-blue-600">Papers</span>
                  <span className="text-sm text-gray-600">arXiv Papers</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span className="text-sm text-green-600">Live</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-lg text-gray-600">Code</span>
                  <span className="text-sm text-gray-600">GitHub Activity</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span className="text-sm text-green-600">Live</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-lg text-green-600">Jobs</span>
                  <span className="text-sm text-gray-600">Job Postings</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span className="text-sm text-green-600">Live</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-lg text-yellow-600">Funding</span>
                  <span className="text-sm text-gray-600">Funding Data</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                  <span className="text-sm text-yellow-600">Mock</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-3">
              <button className="w-full btn-primary text-left">
                Generate New Forecasts
              </button>
              <button className="w-full btn-secondary text-left">
                Run Data Pipeline
              </button>
              <button className="w-full btn-ghost text-left">
                Export Weekly Report
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="card p-6 bg-gradient-to-r from-primary-50 to-blue-50 border-primary-200">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-primary-900 mb-2">
            The Oracle Forecast Engine
          </h3>
          <p className="text-primary-700 mb-4">
            Powered by advanced machine learning algorithms and real-time data fusion
          </p>
          <div className="flex justify-center space-x-6 text-sm text-primary-600">
            <span>ARIMA Forecasting</span>
            <span>•</span>
            <span>Signal Convergence</span>
            <span>•</span>
            <span>Surge Detection</span>
            <span>•</span>
            <span>Confidence Scoring</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
