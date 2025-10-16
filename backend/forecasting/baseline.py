"""Baseline forecasting models for The Oracle."""

import uuid
import warnings
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy.orm import Session
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.exponential_smoothing import ExponentialSmoothing

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


class BaselineForecaster:
    """Baseline forecasting using ARIMA and Exponential Smoothing."""

    def __init__(self, min_data_points: int = 14):
        self.min_data_points = min_data_points
        self.surge_score_weights = settings.surge_score_weights
        self.forecast_horizons = settings.forecast_horizons

    def forecast_all_topics(self, force_rebuild: bool = False) -> dict[str, dict[str, int]]:
        """Forecast for all topics."""
        logger.info("Starting forecast generation for all topics")

        results = {}

        with get_db() as db:
            topics = db.query(Topic).all()

            for topic in topics:
                try:
                    topic_results = {}
                    for horizon in self.forecast_horizons:
                        count = self._forecast_topic_horizon(
                            db, topic.id, horizon, force_rebuild
                        )
                        topic_results[f"horizon_{horizon}d"] = count

                    results[topic.name] = topic_results
                    logger.info(f"Generated forecasts for topic: {topic.name}")

                except Exception as e:
                    logger.error(f"Error forecasting topic {topic.name}: {e}")
                    results[topic.name] = {"error": str(e)}

        total_forecasts = sum(
            sum(topic_results.values()) if isinstance(topic_results, dict) else 0
            for topic_results in results.values()
            if isinstance(topic_results, dict) and "error" not in topic_results
        )

        logger.info(f"Forecast generation completed. Total forecasts: {total_forecasts}")
        return results

    def _forecast_topic_horizon(self, db: Session, topic_id: str, horizon_days: int,
                              force_rebuild: bool) -> int:
        """Generate forecast for a specific topic and horizon."""
        # Check if forecast already exists
        existing_forecast = db.query(TopicForecast).filter(
            TopicForecast.topic_id == topic_id,
            TopicForecast.horizon_days == horizon_days
        ).first()

        if existing_forecast and not force_rebuild:
            logger.info(f"Forecast already exists for topic {topic_id}, horizon {horizon_days}d")
            return 1

        # Get feature data for the topic
        features_data = self._get_topic_features_data(db, topic_id)

        if len(features_data) < self.min_data_points:
            logger.warning(f"Insufficient data for topic {topic_id}: {len(features_data)} points")
            return 0

        # Generate forecast
        forecast_result = self._generate_forecast(features_data, horizon_days)

        if not forecast_result:
            logger.warning(f"Failed to generate forecast for topic {topic_id}")
            return 0

        # Calculate surge score
        surge_score = self._calculate_surge_score(features_data, forecast_result)

        # Store forecast
        forecast_record = TopicForecast(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            horizon_days=horizon_days,
            forecast_curve=forecast_result["forecast_curve"],
            surge_score=surge_score,
            confidence_score=forecast_result["confidence_score"],
            model_type=forecast_result["model_type"],
            model_params=forecast_result["model_params"],
            model_metrics=forecast_result["model_metrics"]
        )

        if existing_forecast:
            # Update existing forecast
            existing_forecast.forecast_curve = forecast_record.forecast_curve
            existing_forecast.surge_score = forecast_record.surge_score
            existing_forecast.confidence_score = forecast_record.confidence_score
            existing_forecast.model_type = forecast_record.model_type
            existing_forecast.model_params = forecast_record.model_params
            existing_forecast.model_metrics = forecast_record.model_metrics
            existing_forecast.updated_at = datetime.utcnow()
        else:
            # Add new forecast
            db.add(forecast_record)

        try:
            db.commit()
            logger.info(f"Stored forecast for topic {topic_id}, horizon {horizon_days}d")
            return 1
        except Exception as e:
            logger.error(f"Error storing forecast for topic {topic_id}: {e}")
            db.rollback()
            raise

    def _get_topic_features_data(self, db: Session, topic_id: str) -> pd.DataFrame:
        """Get feature data for a topic as pandas DataFrame."""
        # Get features for the last 90 days
        start_date = date.today() - timedelta(days=90)

        features = db.query(TopicFeatures).filter(
            TopicFeatures.topic_id == topic_id,
            TopicFeatures.date >= start_date
        ).order_by(TopicFeatures.date.asc()).all()

        if not features:
            return pd.DataFrame()

        # Convert to DataFrame
        data = []
        for feature in features:
            data.append({
                "date": feature.date,
                "velocity": feature.velocity,
                "acceleration": feature.acceleration,
                "z_spike": feature.z_spike,
                "convergence": feature.convergence,
                "mention_count_total": feature.mention_count_total
            })

        df = pd.DataFrame(data)
        df.set_index("date", inplace=True)

        return df

    def _generate_forecast(self, features_data: pd.DataFrame, horizon_days: int) -> dict | None:
        """Generate forecast using multiple models and select the best one."""
        if features_data.empty:
            return None

        # Use velocity as the primary time series for forecasting
        velocity_series = features_data["velocity"].fillna(0)

        # Try multiple models and select the best one
        models = {
            "ARIMA": self._fit_arima_model,
            "ExponentialSmoothing": self._fit_exponential_smoothing_model,
            "Simple": self._fit_simple_trend_model
        }

        best_model = None
        best_score = float('inf')

        for model_name, fit_func in models.items():
            try:
                result = fit_func(velocity_series, horizon_days)
                if result and result["model_metrics"]["mae"] < best_score:
                    best_model = result
                    best_score = result["model_metrics"]["mae"]
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue

        if not best_model:
            logger.error("All forecasting models failed")
            return None

        return best_model

    def _fit_arima_model(self, series: pd.Series, horizon_days: int) -> dict | None:
        """Fit ARIMA model to time series."""
        try:
            # Auto-select ARIMA parameters using simple grid search
            best_params = None
            best_aic = float('inf')

            # Simple parameter grid
            p_values = [0, 1, 2]
            d_values = [0, 1]
            q_values = [0, 1, 2]

            for p in p_values:
                for d in d_values:
                    for q in q_values:
                        try:
                            model = ARIMA(series, order=(p, d, q))
                            fitted_model = model.fit()

                            if fitted_model.aic < best_aic:
                                best_aic = fitted_model.aic
                                best_params = (p, d, q)
                        except:
                            continue

            if best_params is None:
                # Fallback to simple parameters
                best_params = (1, 1, 1)

            # Fit final model
            model = ARIMA(series, order=best_params)
            fitted_model = model.fit()

            # Generate forecast
            forecast = fitted_model.forecast(steps=horizon_days)
            conf_int = fitted_model.get_forecast(steps=horizon_days).conf_int()

            # Create forecast curve
            forecast_curve = []
            start_date = series.index[-1] + timedelta(days=1)

            for i in range(horizon_days):
                forecast_date = start_date + timedelta(days=i)
                forecast_curve.append(ForecastPoint(
                    date=forecast_date.strftime("%Y-%m-%d"),
                    yhat=float(forecast.iloc[i]),
                    yhat_lower=float(conf_int.iloc[i, 0]),
                    yhat_upper=float(conf_int.iloc[i, 1])
                ).dict())

            # Calculate model metrics
            fitted_values = fitted_model.fittedvalues
            mae = mean_absolute_error(series, fitted_values)
            mse = mean_squared_error(series, fitted_values)

            return {
                "forecast_curve": forecast_curve,
                "confidence_score": max(0, 1 - mae / series.std()) if series.std() > 0 else 0,
                "model_type": "ARIMA",
                "model_params": {"order": best_params, "aic": best_aic},
                "model_metrics": {"mae": mae, "mse": mse}
            }

        except Exception as e:
            logger.error(f"ARIMA model failed: {e}")
            return None

    def _fit_exponential_smoothing_model(self, series: pd.Series, horizon_days: int) -> dict | None:
        """Fit Exponential Smoothing model to time series."""
        try:
            # Fit exponential smoothing model
            model = ExponentialSmoothing(series, trend='add', seasonal=None)
            fitted_model = model.fit()

            # Generate forecast
            forecast = fitted_model.forecast(steps=horizon_days)

            # Create forecast curve (no confidence intervals for simplicity)
            forecast_curve = []
            start_date = series.index[-1] + timedelta(days=1)

            for i in range(horizon_days):
                forecast_date = start_date + timedelta(days=i)
                forecast_curve.append(ForecastPoint(
                    date=forecast_date.strftime("%Y-%m-%d"),
                    yhat=float(forecast.iloc[i])
                ).dict())

            # Calculate model metrics
            fitted_values = fitted_model.fittedvalues
            mae = mean_absolute_error(series, fitted_values)
            mse = mean_squared_error(series, fitted_values)

            return {
                "forecast_curve": forecast_curve,
                "confidence_score": max(0, 1 - mae / series.std()) if series.std() > 0 else 0,
                "model_type": "ExponentialSmoothing",
                "model_params": {"alpha": fitted_model.params.get("smoothing_level", 0.3)},
                "model_metrics": {"mae": mae, "mse": mse}
            }

        except Exception as e:
            logger.error(f"Exponential Smoothing model failed: {e}")
            return None

    def _fit_simple_trend_model(self, series: pd.Series, horizon_days: int) -> dict | None:
        """Fit simple linear trend model."""
        try:
            # Simple linear trend
            x = np.arange(len(series))
            y = series.values

            # Fit linear regression
            slope, intercept = np.polyfit(x, y, 1)

            # Generate forecast
            forecast_curve = []
            start_date = series.index[-1] + timedelta(days=1)

            for i in range(horizon_days):
                forecast_date = start_date + timedelta(days=i)
                forecast_value = intercept + slope * (len(series) + i)
                forecast_curve.append(ForecastPoint(
                    date=forecast_date.strftime("%Y-%m-%d"),
                    yhat=max(0, forecast_value)  # Ensure non-negative
                ).dict())

            # Calculate model metrics
            fitted_values = intercept + slope * x
            mae = mean_absolute_error(y, fitted_values)
            mse = mean_squared_error(y, fitted_values)

            return {
                "forecast_curve": forecast_curve,
                "confidence_score": max(0, 1 - mae / series.std()) if series.std() > 0 else 0,
                "model_type": "LinearTrend",
                "model_params": {"slope": slope, "intercept": intercept},
                "model_metrics": {"mae": mae, "mse": mse}
            }

        except Exception as e:
            logger.error(f"Simple trend model failed: {e}")
            return None

    def _calculate_surge_score(self, features_data: pd.DataFrame, forecast_result: dict) -> float:
        """Calculate surge score based on forecast and features."""
        try:
            # Get recent features
            recent_features = features_data.tail(7)  # Last week

            if recent_features.empty:
                return 0.0

            # Calculate components
            forecast_curve = forecast_result["forecast_curve"]

            # 1. Forecasted velocity growth (30 days)
            current_velocity = recent_features["velocity"].iloc[-1]
            future_velocity = forecast_curve[29]["yhat"] if len(forecast_curve) > 29 else current_velocity
            velocity_growth = (future_velocity - current_velocity) / max(current_velocity, 0.001)

            # 2. Recent momentum (acceleration)
            avg_acceleration = recent_features["acceleration"].mean()
            momentum = max(0, avg_acceleration)  # Only positive momentum

            # 3. Z-score spike
            max_z_spike = recent_features["z_spike"].max()
            z_spike = max(0, max_z_spike - 2)  # Only significant spikes

            # 4. Convergence
            avg_convergence = recent_features["convergence"].mean()

            # Apply weights
            surge_score = (
                self.surge_score_weights["velocity_growth"] * velocity_growth +
                self.surge_score_weights["momentum"] * momentum +
                self.surge_score_weights["z_spike"] * z_spike +
                self.surge_score_weights["convergence"] * avg_convergence
            )

            # Apply convergence boost
            if avg_convergence > 0.5:  # High convergence
                surge_score *= 1.2

            # Normalize to 0-1 range
            surge_score = max(0, min(1, surge_score))

            return surge_score

        except Exception as e:
            logger.error(f"Error calculating surge score: {e}")
            return 0.0

    def get_forecast_summary(self, topic_id: str) -> dict:
        """Get forecast summary for a topic."""
        with get_db() as db:
            forecasts = db.query(TopicForecast).filter(
                TopicForecast.topic_id == topic_id
            ).all()

            if not forecasts:
                return {}

            summary = {}
            for forecast in forecasts:
                horizon_key = f"horizon_{forecast.horizon_days}d"
                summary[horizon_key] = {
                    "surge_score": forecast.surge_score,
                    "confidence": forecast.confidence_score,
                    "model_type": forecast.model_type,
                    "growth_rate": forecast.forecast_growth_rate
                }

            return summary

    def cleanup_old_forecasts(self, days: int = 30) -> int:
        """Clean up old forecasts."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with get_db() as db:
            try:
                old_forecasts = db.query(TopicForecast).filter(
                    TopicForecast.updated_at < cutoff_date
                )

                count = old_forecasts.count()
                old_forecasts.delete(synchronize_session=False)
                db.commit()

                logger.info(f"Cleaned up {count} old forecasts")
                return count

            except Exception as e:
                logger.error(f"Error cleaning up old forecasts: {e}")
                db.rollback()
                raise


def main():
    """Main function for running forecasting from command line."""
    import typer

    app = typer.Typer()

    @app.command()
    def forecast_all(force: bool = False):
        """Generate forecasts for all topics."""
        forecaster = BaselineForecaster()
        results = forecaster.forecast_all_topics(force_rebuild=force)

        print("Forecast Generation Results:")
        for topic, topic_results in results.items():
            if isinstance(topic_results, dict) and "error" not in topic_results:
                print(f"  {topic}:")
                for horizon, count in topic_results.items():
                    print(f"    {horizon}: {count} forecasts")
            else:
                print(f"  {topic}: {topic_results}")

    @app.command()
    def forecast_topic(topic_id: str, horizon: int = 30, force: bool = False):
        """Generate forecast for specific topic and horizon."""
        forecaster = BaselineForecaster()

        with get_db() as db:
            count = forecaster._forecast_topic_horizon(db, topic_id, horizon, force)
            print(f"Generated {count} forecasts for topic {topic_id}, horizon {horizon}d")

    @app.command()
    def summary(topic_id: str):
        """Get forecast summary for topic."""
        forecaster = BaselineForecaster()
        summary_data = forecaster.get_forecast_summary(topic_id)

        print(f"Forecast Summary for {topic_id}:")
        for horizon, data in summary_data.items():
            print(f"  {horizon}:")
            for key, value in data.items():
                print(f"    {key}: {value}")

    @app.command()
    def cleanup(days: int = 30):
        """Clean up old forecasts."""
        forecaster = BaselineForecaster()
        count = forecaster.cleanup_old_forecasts(days=days)
        print(f"Cleaned up {count} old forecasts")

    app()


if __name__ == "__main__":
    main()
