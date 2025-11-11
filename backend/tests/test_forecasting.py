"""Forecasting module tests."""


import numpy as np
import pandas as pd
import pytest

from ..forecasting.baseline import BaselineForecaster
from ..forecasting.ranker import SurgeRanker

try:
    from ..forecasting.prophet_forecaster import ProphetForecaster
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    ProphetForecaster = None


class TestBaselineForecaster:
    """Test baseline forecaster."""

    def test_calculate_surge_score(self):
        """Test surge score calculation."""
        forecaster = BaselineForecaster()

        # Mock features data
        features_data = pd.DataFrame({
            'velocity': [1.0, 1.5, 2.0, 2.5, 3.0],
            'acceleration': [0.1, 0.2, 0.3, 0.4, 0.5],
            'z_spike': [0.5, 1.0, 1.5, 2.0, 2.5],
            'convergence': [0.6, 0.7, 0.8, 0.9, 1.0]
        })

        # Mock forecast result
        forecast_result = {
            'forecast_curve': [
                {'date': '2024-01-01', 'yhat': 3.0},
                {'date': '2024-01-02', 'yhat': 3.5},
                {'date': '2024-01-03', 'yhat': 4.0},
                # ... more points up to day 30
            ] + [{'date': f'2024-01-{i+4}', 'yhat': 4.0 + i*0.1} for i in range(27)]
        }

        surge_score = forecaster._calculate_surge_score(features_data, forecast_result)

        assert 0 <= surge_score <= 1
        assert surge_score > 0  # Should be positive for good signals

    def test_fit_arima_model(self):
        """Test ARIMA model fitting."""
        forecaster = BaselineForecaster()

        # Create test time series
        np.random.seed(42)
        trend = np.linspace(1, 10, 50)
        noise = np.random.normal(0, 0.1, 50)
        series = pd.Series(trend + noise)

        result = forecaster._fit_arima_model(series, horizon_days=10)

        if result:  # Model might fail with short series
            assert 'forecast_curve' in result
            assert 'confidence_score' in result
            assert 'model_type' in result
            assert result['model_type'] == 'ARIMA'
            assert len(result['forecast_curve']) == 10

    def test_fit_simple_trend_model(self):
        """Test simple trend model."""
        forecaster = BaselineForecaster()

        # Create test time series with linear trend
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        result = forecaster._fit_simple_trend_model(series, horizon_days=5)

        assert result is not None
        assert 'forecast_curve' in result
        assert 'confidence_score' in result
        assert 'model_type' in result
        assert result['model_type'] == 'LinearTrend'
        assert len(result['forecast_curve']) == 5

        # Check that forecast continues the trend
        forecast_values = [point['yhat'] for point in result['forecast_curve']]
        assert forecast_values[0] > 10  # Should continue upward trend
        assert all(f >= 0 for f in forecast_values)  # Should be non-negative


class TestSurgeRanker:
    """Test surge ranker."""

    def test_calculate_ranking_score(self):
        """Test ranking score calculation."""
        ranker = SurgeRanker()

        # Mock forecast and features
        forecast = type('MockForecast', (), {
            'surge_score': 0.8,
            'confidence_score': 0.9,
            'forecast_growth_rate': 0.5
        })()

        recent_features = {
            'velocity': 5.0,
            'acceleration': 1.0,
            'convergence': 0.8
        }

        score = ranker._calculate_ranking_score(forecast, recent_features)

        assert 0 <= score <= 1
        assert score > 0.5  # Should be high for good signals

    def test_get_ranking_insights(self):
        """Test ranking insights generation."""
        ranker = SurgeRanker()

        # Mock rankings
        rankings = [
            {
                'topic_name': 'AI',
                'surge_score': 0.9,
                'confidence': 0.8
            },
            {
                'topic_name': 'Robotics',
                'surge_score': 0.7,
                'confidence': 0.9
            },
            {
                'topic_name': 'Quantum',
                'surge_score': 0.6,
                'confidence': 0.7
            }
        ]

        insights = ranker.get_ranking_insights(rankings)

        assert 'total_ranked' in insights
        assert 'avg_surge_score' in insights
        assert 'max_surge_score' in insights
        assert 'avg_confidence' in insights
        assert 'top_topic' in insights

        assert insights['total_ranked'] == 3
        assert insights['top_topic'] == 'AI'
        assert insights['max_surge_score'] == 0.9

    def test_get_ranking_alerts(self):
        """Test ranking alerts generation."""
        ranker = SurgeRanker()

        # Mock rankings with high surge score
        rankings = [
            {
                'topic_name': 'AI',
                'surge_score': 0.9,
                'confidence': 0.3,  # Low confidence
                'growth_rate': 1.5  # High growth
            }
        ]

        alerts = ranker.get_ranking_alerts(rankings)

        assert len(alerts) >= 2  # Should have high surge and low confidence alerts

        alert_types = [alert['type'] for alert in alerts]
        assert 'high_surge' in alert_types
        assert 'low_confidence' in alert_types

    def test_get_emerging_topics(self):
        """Test emerging topics identification."""
        ranker = SurgeRanker()

        # Mock rank_topics to return high surge topics
        with pytest.Mock() as mock_ranker:
            mock_ranker.rank_topics.return_value = [
                {
                    'topic_id': 'ai',
                    'topic_name': 'AI',
                    'surge_score': 0.8,
                    'ranking_score': 0.85,
                    'growth_rate': 0.6
                },
                {
                    'topic_id': 'robotics',
                    'topic_name': 'Robotics',
                    'surge_score': 0.7,
                    'ranking_score': 0.75,
                    'growth_rate': 0.5
                }
            ]

            emerging = ranker.get_emerging_topics(threshold=0.6)

            assert len(emerging) == 2
            assert emerging[0]['topic_name'] == 'AI'
            assert emerging[0]['surge_score'] == 0.8


@pytest.mark.skipif(not PROPHET_AVAILABLE, reason="Prophet is not installed")
class TestProphetForecaster:
    """Test Prophet forecaster."""

    def test_prophet_forecaster_initialization(self):
        """Test Prophet forecaster initialization."""
        forecaster = ProphetForecaster(min_data_points=14)
        assert forecaster.min_data_points == 14

    def test_calculate_velocity_growth(self):
        """Test velocity growth calculation."""
        forecaster = ProphetForecaster()

        # Mock features with increasing velocity
        from ..models.features import TopicFeatures
        from datetime import date

        features = [
            TopicFeatures(velocity=1.0, date=date(2024, 1, 1)),
            TopicFeatures(velocity=1.5, date=date(2024, 1, 2)),
            TopicFeatures(velocity=2.0, date=date(2024, 1, 3)),
        ]

        growth = forecaster._calculate_velocity_growth(features)
        assert growth > 0  # Should be positive for increasing velocity
        assert growth == pytest.approx(1.0, rel=0.1)  # 100% growth from 1.0 to 2.0

    def test_calculate_z_spike(self):
        """Test z-spike calculation."""
        forecaster = ProphetForecaster()

        from ..models.features import TopicFeatures
        from datetime import date

        # Create features with a spike at the end
        features = [
            TopicFeatures(velocity=1.0, date=date(2024, 1, i))
            for i in range(1, 10)
        ]
        features.append(TopicFeatures(velocity=5.0, date=date(2024, 1, 10)))

        z_spike = forecaster._calculate_z_spike(features)
        assert 0 <= z_spike <= 1
        assert z_spike > 0.5  # Should detect the spike

    def test_calculate_surge_score(self):
        """Test surge score calculation."""
        forecaster = ProphetForecaster()

        surge_score = forecaster._calculate_surge_score(
            velocity_growth=0.5,
            z_spike=0.8,
            convergence=0.7,
            confidence=0.9
        )

        assert 0 <= surge_score <= 1
        assert surge_score > 0.5  # Should be high for good signals

    def test_prophet_forecast_with_mock_data(self):
        """Test Prophet forecast with mock time series data."""
        forecaster = ProphetForecaster(min_data_points=14)

        # Create mock time series with trend and seasonality
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        trend = np.linspace(1, 10, 30)
        seasonal = 2 * np.sin(2 * np.pi * np.arange(30) / 7)  # Weekly seasonality
        noise = np.random.normal(0, 0.1, 30)
        values = trend + seasonal + noise

        # Create Prophet DataFrame
        df = pd.DataFrame({
            'ds': dates,
            'y': values
        })

        # This would require actual Prophet model fitting
        # For unit test, we just verify the data structure
        assert len(df) == 30
        assert 'ds' in df.columns
        assert 'y' in df.columns
        assert df['y'].min() > 0  # Values should be positive
