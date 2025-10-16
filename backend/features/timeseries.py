"""Time series analysis and feature extraction for The Oracle."""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

from ..core.logging import get_logger
from ..db.session import get_db
from ..models.topic import Topic
from ..models.signal_event import SignalEvent
from ..models.features import TopicFeatures

logger = get_logger(__name__)


class TimeSeriesAnalyzer:
    """Time series analysis for topic features."""
    
    def __init__(self, window_size: int = 7, alpha: float = 0.3):
        self.window_size = window_size
        self.alpha = alpha  # For exponential weighted moving average
    
    def calculate_velocity(self, values: List[float]) -> List[float]:
        """Calculate velocity (rate of change) using exponential weighted moving average."""
        if len(values) < 2:
            return [0.0] * len(values)
        
        # Convert to pandas Series for EWMA calculation
        series = pd.Series(values)
        
        # Calculate EWMA
        ewma = series.ewm(alpha=self.alpha, adjust=False).mean()
        
        # Calculate velocity as difference from previous value
        velocity = [0.0]  # First value has no velocity
        for i in range(1, len(ewma)):
            vel = ewma.iloc[i] - ewma.iloc[i-1]
            velocity.append(vel)
        
        return velocity
    
    def calculate_acceleration(self, velocity: List[float]) -> List[float]:
        """Calculate acceleration (rate of change of velocity)."""
        if len(velocity) < 2:
            return [0.0] * len(velocity)
        
        acceleration = [0.0]  # First value has no acceleration
        for i in range(1, len(velocity)):
            acc = velocity[i] - velocity[i-1]
            acceleration.append(acc)
        
        return acceleration
    
    def calculate_z_score_spike(self, values: List[float], window: int = 7) -> List[float]:
        """Calculate z-score spikes for anomaly detection."""
        if len(values) < window:
            return [0.0] * len(values)
        
        z_scores = []
        
        for i in range(len(values)):
            if i < window:
                z_scores.append(0.0)
            else:
                # Get window of values
                window_values = values[i-window:i]
                
                # Calculate mean and std
                mean_val = np.mean(window_values)
                std_val = np.std(window_values)
                
                if std_val == 0:
                    z_score = 0.0
                else:
                    z_score = (values[i] - mean_val) / std_val
                
                z_scores.append(z_score)
        
        return z_scores
    
    def calculate_convergence(self, source_counts: Dict[str, List[int]]) -> List[float]:
        """Calculate convergence score based on multiple sources."""
        if not source_counts:
            return []
        
        # Get the minimum length across all sources
        min_length = min(len(counts) for counts in source_counts.values())
        
        convergence_scores = []
        total_sources = len(source_counts)
        
        for i in range(min_length):
            active_sources = 0
            
            for source, counts in source_counts.items():
                if counts[i] > 0:
                    active_sources += 1
            
            # Normalize by total number of sources
            convergence = active_sources / total_sources if total_sources > 0 else 0.0
            convergence_scores.append(convergence)
        
        return convergence_scores
    
    def detect_change_points(self, values: List[float], threshold: float = 2.0) -> List[int]:
        """Detect significant change points in time series."""
        if len(values) < 3:
            return []
        
        change_points = []
        z_scores = self.calculate_z_score_spike(values)
        
        for i, z_score in enumerate(z_scores):
            if abs(z_score) > threshold:
                change_points.append(i)
        
        return change_points
    
    def smooth_series(self, values: List[float], window: int = 3) -> List[float]:
        """Apply moving average smoothing to time series."""
        if len(values) < window:
            return values
        
        smoothed = []
        
        for i in range(len(values)):
            if i < window - 1:
                # Use available values for beginning
                smoothed.append(np.mean(values[:i+1]))
            else:
                # Use full window
                smoothed.append(np.mean(values[i-window+1:i+1]))
        
        return smoothed
    
    def calculate_trend_strength(self, values: List[float]) -> float:
        """Calculate trend strength using linear regression."""
        if len(values) < 2:
            return 0.0
        
        # Create time index
        x = np.arange(len(values))
        y = np.array(values)
        
        # Calculate linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate R-squared for trend strength
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        
        if ss_tot == 0:
            r_squared = 0.0
        else:
            r_squared = 1 - (ss_res / ss_tot)
        
        return r_squared
    
    def calculate_volatility(self, values: List[float], window: int = 7) -> List[float]:
        """Calculate rolling volatility (standard deviation)."""
        if len(values) < window:
            return [0.0] * len(values)
        
        volatility = []
        
        for i in range(len(values)):
            if i < window - 1:
                volatility.append(0.0)
            else:
                window_values = values[i-window+1:i+1]
                vol = np.std(window_values)
                volatility.append(vol)
        
        return volatility
    
    def analyze_topic_timeseries(self, topic_id: str, days: int = 90) -> Dict[str, List[float]]:
        """Analyze time series for a specific topic."""
        with get_db() as db:
            # Get events for topic in date range
            start_date = date.today() - timedelta(days=days)
            
            events = db.query(SignalEvent).filter(
                SignalEvent.topic_id == topic_id,
                SignalEvent.timestamp >= start_date
            ).order_by(SignalEvent.timestamp.asc()).all()
            
            if not events:
                return {}
            
            # Group events by date
            daily_events = {}
            for event in events:
                event_date = event.timestamp.date()
                if event_date not in daily_events:
                    daily_events[event_date] = []
                daily_events[event_date].append(event)
            
            # Create time series data
            dates = sorted(daily_events.keys())
            values = []
            
            for event_date in dates:
                events_on_date = daily_events[event_date]
                # Sum magnitudes for the day
                daily_value = sum(event.magnitude for event in events_on_date)
                values.append(daily_value)
            
            if len(values) < 2:
                return {}
            
            # Calculate features
            velocity = self.calculate_velocity(values)
            acceleration = self.calculate_acceleration(velocity)
            z_spikes = self.calculate_z_score_spike(values)
            smoothed = self.smooth_series(values)
            volatility = self.calculate_volatility(values)
            trend_strength = self.calculate_trend_strength(values)
            
            return {
                "dates": [d.isoformat() for d in dates],
                "values": values,
                "velocity": velocity,
                "acceleration": acceleration,
                "z_spikes": z_spikes,
                "smoothed": smoothed,
                "volatility": volatility,
                "trend_strength": trend_strength,
                "change_points": self.detect_change_points(values)
            }
    
    def get_topic_summary_stats(self, topic_id: str, days: int = 30) -> Dict[str, float]:
        """Get summary statistics for a topic."""
        analysis = self.analyze_topic_timeseries(topic_id, days)
        
        if not analysis or not analysis.get("values"):
            return {}
        
        values = analysis["values"]
        velocity = analysis["velocity"]
        acceleration = analysis["acceleration"]
        
        return {
            "total_events": sum(values),
            "avg_daily_events": np.mean(values) if values else 0,
            "max_daily_events": max(values) if values else 0,
            "current_velocity": velocity[-1] if velocity else 0,
            "avg_velocity": np.mean(velocity) if velocity else 0,
            "current_acceleration": acceleration[-1] if acceleration else 0,
            "trend_strength": analysis.get("trend_strength", 0),
            "volatility": np.mean(analysis.get("volatility", [0])) if analysis.get("volatility") else 0
        }
