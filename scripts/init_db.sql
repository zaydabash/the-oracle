-- Initialize Oracle database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_signal_events_topic_id ON signal_events(topic_id);
CREATE INDEX IF NOT EXISTS idx_signal_events_source ON signal_events(source);
CREATE INDEX IF NOT EXISTS idx_signal_events_timestamp ON signal_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_signal_events_magnitude ON signal_events(magnitude);

CREATE INDEX IF NOT EXISTS idx_topic_features_topic_id ON topic_features(topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_features_date ON topic_features(date);
CREATE INDEX IF NOT EXISTS idx_topic_features_velocity ON topic_features(velocity);

CREATE INDEX IF NOT EXISTS idx_topic_forecasts_topic_id ON topic_forecasts(topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_forecasts_horizon ON topic_forecasts(horizon_days);
CREATE INDEX IF NOT EXISTS idx_topic_forecasts_surge_score ON topic_forecasts(surge_score);

-- Create text search indexes
CREATE INDEX IF NOT EXISTS idx_topics_name_trgm ON topics USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_signal_events_title_trgm ON signal_events USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_signal_events_description_trgm ON signal_events USING gin (description gin_trgm_ops);
