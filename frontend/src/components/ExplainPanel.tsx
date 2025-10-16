import React from 'react';
import { TrendingUp, Zap, Activity, BarChart3, ExternalLink } from 'lucide-react';
import { formatPercentage, getSourceIcon, getSourceColor } from '../lib/api';

interface ExplainPanelProps {
  surgeScore: number;
  confidence: number;
  velocity: number;
  acceleration: number;
  convergence: number;
  contributingSources: Record<string, number>;
  growthRate?: number;
}

const ExplainPanel: React.FC<ExplainPanelProps> = ({
  surgeScore,
  confidence,
  velocity,
  acceleration,
  convergence,
  contributingSources,
  growthRate
}) => {
  const getScoreColor = (score: number, type: 'score' | 'confidence' = 'score') => {
    if (type === 'confidence') {
      if (score >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
      if (score >= 0.6) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      return 'text-red-600 bg-red-50 border-red-200';
    }
    
    if (score >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 0.6) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (score >= 0.4) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const getScoreExplanation = (score: number) => {
    if (score >= 0.8) return 'Exceptional momentum - breakout potential very high';
    if (score >= 0.6) return 'Strong growth potential - significant upward trend';
    if (score >= 0.4) return 'Moderate interest - steady development';
    return 'Limited momentum - early stage or declining interest';
  };

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
        <BarChart3 className="w-5 h-5" />
        <span>Forecast Explanation</span>
      </h3>

      <div className="space-y-6">
        {/* Surge Score */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-primary-100 rounded-lg">
              <TrendingUp className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h4 className="font-medium text-gray-900">Surge Score</h4>
              <p className="text-sm text-gray-500">Predicted breakout probability</p>
            </div>
          </div>
          <div className={`px-3 py-1 rounded-full border text-sm font-medium ${getScoreColor(surgeScore)}`}>
            {formatPercentage(surgeScore)}
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-sm text-gray-700">
            {getScoreExplanation(surgeScore)}
          </p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-gray-700">Velocity</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{velocity.toFixed(2)}</p>
            <p className="text-xs text-gray-500">Recent activity rate</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Zap className="w-4 h-4 text-yellow-600" />
              <span className="text-sm font-medium text-gray-700">Acceleration</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{acceleration.toFixed(2)}</p>
            <p className="text-xs text-gray-500">Rate of change</p>
          </div>
        </div>

        {/* Confidence Score */}
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Model Confidence</h4>
            <p className="text-sm text-gray-500">Forecast reliability</p>
          </div>
          <div className={`px-3 py-1 rounded-full border text-sm font-medium ${getScoreColor(confidence, 'confidence')}`}>
            {formatPercentage(confidence)}
          </div>
        </div>

        {/* Growth Rate */}
        {growthRate !== undefined && (
          <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-primary-900">Projected Growth</h4>
                <p className="text-sm text-primary-700">Expected change over forecast horizon</p>
              </div>
              <div className="text-2xl font-bold text-primary-900">
                {formatPercentage(growthRate)}
              </div>
            </div>
          </div>
        )}

        {/* Contributing Sources */}
        <div>
          <h4 className="font-medium text-gray-900 mb-3">Contributing Signals</h4>
          <div className="space-y-2">
            {Object.entries(contributingSources).map(([source, count]) => (
              <div key={source} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">{getSourceIcon(source)}</span>
                  <span className="text-sm font-medium text-gray-700 capitalize">
                    {source}
                  </span>
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${getSourceColor(source)}`}>
                  {count} events
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-3 bg-gray-50 rounded-lg p-3">
            <p className="text-sm text-gray-600">
              <strong>Convergence:</strong> {formatPercentage(convergence)} of data sources active
              {convergence > 0.7 && ' - High cross-source validation'}
              {convergence > 0.4 && convergence <= 0.7 && ' - Moderate validation'}
              {convergence <= 0.4 && ' - Limited validation'}
            </p>
          </div>
        </div>

        {/* Algorithm Info */}
        <div className="border-t border-gray-200 pt-4">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>Forecast Algorithm</span>
            <div className="flex items-center space-x-1">
              <span>ARIMA + Ensemble</span>
              <ExternalLink className="w-3 h-3" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExplainPanel;
