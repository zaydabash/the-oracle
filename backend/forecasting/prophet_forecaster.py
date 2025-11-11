"""Prophet forecasting model for The Oracle."""

import uuid
import warnings
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy.orm import Session

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    Prophet = None

from ..core.config import settings
from ..core.logging import get_logger
from ..db.session import get_db
from ..models.features import TopicFeatures
from ..models.forecast import TopicForecast
from ..models.topic import Topic
from ..schemas.forecast import ForecastPoint

logger = get_logger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")


class ProphetForecaster:
    """
    Prophet-based forecasting for time series with seasonality.
    
    Prophet is particularly good at handling:
    - Seasonal patterns (daily, weekly, yearly)
    - Holiday effects
    - Changepoints in trends
    - Missing data and outliers
    """

    def __init__(self, min_data_points: int = 14):
        """
        Initialize the Prophet forecaster.
        
        Args:
            min_data_points: Minimum number of data points required for forecasting
        """
        if not PROPHET_AVAILABLE:
            raise ImportError(
                "Prophet is not available. Install it with: pip install prophet"
            )
        self.min_data_points = min_data_points
        self.forecast_horizons = settings.forecast_horizons

    def forecast_topic(
        self,
        db: Session,
        topic_id: str,
        horizon_days: int = 30,
        force_rebuild: bool = False
    ) -> dict | None:
        """
        Generate forecast for a specific topic using Prophet.
        
        Args:
            db: Database session
            topic_id: Topic identifier
            horizon_days: Forecast horizon in days
            force_rebuild: Force regeneration even if forecast exists
            
        Returns:
            Dictionary with forecast results or None if forecasting fails
        """
        logger.info(f"Generating Prophet forecast for topic {topic_id} (horizon: {horizon_days}d)")

        # Check if forecast already exists
        if not force_rebuild:
            existing = db.query(TopicForecast).filter(
                TopicForecast.topic_id == topic_id,
                TopicForecast.horizon_days == horizon_days,
                TopicForecast.model_type == "Prophet"
            ).first()

            if existing:
                logger.info(f"Forecast already exists for topic {topic_id}")
                return {
                    "forecast_id": existing.id,
                    "existing": True
                }

        # Get topic features
        features = db.query(TopicFeatures).filter(
            TopicFeatures.topic_id == topic_id
        ).order_by(TopicFeatures.date.asc()).all()

        if len(features) < self.min_data_points:
            logger.warning(
                f"Insufficient data points for topic {topic_id}: "
                f"{len(features)} < {self.min_data_points}"
            )
            return None

        # Prepare time series data
        dates = [f.date for f in features]
        values = [f.velocity for f in features]

        # Create Prophet-compatible DataFrame
        df = pd.DataFrame({
            'ds': pd.to_datetime(dates),
            'y': values
        })

        try:
            # Fit Prophet model
            model = Prophet(
                yearly_seasonality=False,  # Disable yearly if < 1 year of data
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.05,  # Regularization
                seasonality_prior_scale=10.0,
                interval_width=0.80  # 80% confidence interval
            )

            # Add weekly seasonality if we have enough data
            if len(df) >= 14:
                model.add_seasonality(name='weekly', period=7, fourier_order=3)

            model.fit(df)

            # Generate forecast
            future = model.make_future_dataframe(periods=horizon_days)
            forecast = model.predict(future)

            # Extract forecast points
            forecast_points = []
            forecast_start_idx = len(df)

            for i in range(forecast_start_idx, len(forecast)):
                row = forecast.iloc[i]
                forecast_points.append({
                    'date': row['ds'].date().isoformat(),
                    'yhat': float(row['yhat']),
                    'yhat_lower': float(row['yhat_lower']),
                    'yhat_upper': float(row['yhat_upper'])
                })

            # Calculate confidence score based on prediction interval width
            avg_interval_width = np.mean([
                p['yhat_upper'] - p['yhat_lower'] for p in forecast_points
            ])
            avg_value = np.mean([p['yhat'] for p in forecast_points])
            confidence_score = max(0.0, min(1.0, 1.0 - (avg_interval_width / (avg_value + 1.0))))

            # Calculate growth rate
            if len(forecast_points) > 1:
                initial_value = forecast_points[0]['yhat']
                final_value = forecast_points[-1]['yhat']
                growth_rate = (final_value - initial_value) / (initial_value + 1e-6)
            else:
                growth_rate = 0.0

            # Calculate surge score components from recent features
            recent_features = features[-30:] if len(features) >= 30 else features
            velocity_growth = self._calculate_velocity_growth(recent_features)
            z_spike = self._calculate_z_spike(recent_features)
            convergence = self._calculate_convergence(db, topic_id)

            # Calculate surge score
            surge_score = self._calculate_surge_score(
                velocity_growth, z_spike, convergence, confidence_score
            )

            # Create forecast record
            forecast_id = str(uuid.uuid4())
            forecast_record = TopicForecast(
                id=forecast_id,
                topic_id=topic_id,
                horizon_days=horizon_days,
                model_type="Prophet",
                growth_rate=growth_rate,
                confidence_score=confidence_score,
                forecast_curve=forecast_points,
                surge_score=surge_score,
                created_at=datetime.utcnow()
            )

            db.add(forecast_record)
            db.commit()

            logger.info(
                f"Prophet forecast generated for topic {topic_id}: "
                f"surge_score={surge_score:.3f}, confidence={confidence_score:.3f}"
            )

            return {
                "forecast_id": forecast_id,
                "forecast_curve": forecast_points,
                "confidence_score": confidence_score,
                "growth_rate": growth_rate,
                "surge_score": surge_score,
                "model_type": "Prophet"
            }

        except Exception as e:
            logger.error(f"Error generating Prophet forecast for topic {topic_id}: {e}")
            return None

    def _calculate_velocity_growth(self, features: list[TopicFeatures]) -> float:
        """Calculate velocity growth rate from recent features."""
        if len(features) < 2:
            return 0.0

        recent_velocity = features[-1].velocity
        earlier_velocity = features[0].velocity

        if earlier_velocity == 0:
            return 0.0

        return (recent_velocity - earlier_velocity) / earlier_velocity

    def _calculate_z_spike(self, features: list[TopicFeatures]) -> float:
        """Calculate z-score spike for anomaly detection."""
        if len(features) < 3:
            return 0.0

        velocities = [f.velocity for f in features]
        mean_vel = np.mean(velocities)
        std_vel = np.std(velocities)

        if std_vel == 0:
            return 0.0

        latest_velocity = velocities[-1]
        z_score = (latest_velocity - mean_vel) / std_vel

        # Return normalized z-spike (0-1 scale)
        return min(1.0, max(0.0, (z_score + 2) / 4))

    def _calculate_convergence(self, db: Session, topic_id: str) -> float:
        """Calculate signal convergence across sources."""
        # This would query signal_events and calculate convergence
        # For now, return a mock value
        return 0.7

    def _calculate_surge_score(
        self,
        velocity_growth: float,
        z_spike: float,
        convergence: float,
        confidence: float
    ) -> float:
        """
        Calculate surge score using sigmoid function.
        
        Args:
            velocity_growth: Recent velocity growth rate
            z_spike: Z-score anomaly detection
            convergence: Signal alignment across sources
            confidence: Forecast confidence (higher is better)
            
        Returns:
            Surge score between 0 and 1
        """
        # Get weights from settings
        weights = settings.surge_score_weights

        # Calculate weighted sum
        weighted_sum = (
            weights.get("velocity_growth", 0.4) * velocity_growth +
            weights.get("z_spike", 0.3) * z_spike +
            weights.get("convergence", 0.2) * convergence +
            weights.get("confidence", 0.1) * confidence
        )

        # Apply sigmoid function to normalize to 0-1
        import math
        surge_score = 1 / (1 + math.exp(-weighted_sum * 5))

        return surge_score

    def forecast_all_topics(self, force_rebuild: bool = False) -> dict[str, dict[str, int]]:
        """Forecast for all topics using Prophet."""
        logger.info("Starting Prophet forecast generation for all topics")

        results = {}

        with get_db() as db:
            topics = db.query(Topic).all()

            for topic in topics:
                try:
                    topic_results = {}
                    for horizon in self.forecast_horizons:
                        result = self.forecast_topic(db, topic.id, horizon, force_rebuild)
                        if result:
                            topic_results[f"horizon_{horizon}d"] = 1
                        else:
                            topic_results[f"horizon_{horizon}d"] = 0

                    results[topic.id] = topic_results

                except Exception as e:
                    logger.error(f"Error forecasting topic {topic.id}: {e}")
                    results[topic.id] = {"error": str(e)}

        logger.info(f"Prophet forecast generation complete: {len(results)} topics processed")
        return results

