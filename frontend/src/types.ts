// API Response Types
export interface Topic {
  id: string;
  name: string;
  description?: string;
  keywords: string[];
  created_at: string;
  updated_at: string;
}

export interface SignalEvent {
  id: string;
  source: 'arxiv' | 'github' | 'jobs' | 'funding';
  source_id: string;
  topic_id?: string;
  title: string;
  url?: string;
  description?: string;
  timestamp: string;
  magnitude: number;
  metadata: Record<string, any>;
  created_at: string;
}

export interface TopicFeatures {
  id: string;
  topic_id: string;
  date: string;
  mention_count_total: number;
  mention_count_arxiv: number;
  mention_count_github: number;
  mention_count_jobs: number;
  mention_count_funding: number;
  velocity: number;
  acceleration: number;
  z_spike: number;
  convergence: number;
  magnitude_sum: number;
  unique_sources: number;
  created_at: string;
  updated_at: string;
}

export interface ForecastPoint {
  date: string;
  yhat: number;
  yhat_lower?: number;
  yhat_upper?: number;
}

export interface TopicForecast {
  id: string;
  topic_id: string;
  horizon_days: number;
  forecast_curve: ForecastPoint[];
  surge_score: number;
  confidence_score: number;
  model_type: string;
  model_params: Record<string, any>;
  model_metrics: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// API Response Types
export interface TopicLeaderboardItem {
  rank: number;
  topic: Topic;
  surge_score: number;
  velocity: number;
  acceleration: number;
  mention_count_30d: number;
  sparkline_data: number[];
}

export interface TopicDetail extends Topic {
  recent_events_count: number;
  velocity_trend: number[];
  acceleration_trend: number[];
  forecast_curves: Record<number, ForecastPoint[]>;
  contributing_sources: Record<string, number>;
}

export interface ForecastSummary {
  topic_id: string;
  topic_name: string;
  horizon_30d?: number;
  horizon_90d?: number;
  horizon_180d?: number;
  surge_score: number;
  confidence: number;
  growth_rate?: number;
}

export interface ForecastLeaderboard {
  forecasts: ForecastSummary[];
  total: number;
  generated_at: string;
}

export interface SignalEventList {
  events: SignalEvent[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// UI State Types
export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

export interface DashboardStats {
  total_topics: number;
  total_events: number;
  total_forecasts: number;
  high_surge_topics: number;
}

// Chart Data Types
export interface ChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface SparklineData {
  data: ChartDataPoint[];
  color?: string;
}

// Filter Types
export interface TopicFilter {
  search?: string;
  source?: string;
  min_surge_score?: number;
  max_surge_score?: number;
}

export interface SignalEventFilter {
  topic_id?: string;
  source?: string;
  start_date?: string;
  end_date?: string;
  min_magnitude?: number;
}
