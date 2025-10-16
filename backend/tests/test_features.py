"""Feature engineering tests."""


from ..features.timeseries import TimeSeriesAnalyzer
from ..features.topic_mapping import TopicMapper


class TestTimeSeriesAnalyzer:
    """Test time series analyzer."""

    def test_calculate_velocity(self):
        """Test velocity calculation."""
        analyzer = TimeSeriesAnalyzer()

        # Test with increasing values
        values = [1, 2, 3, 4, 5]
        velocity = analyzer.calculate_velocity(values)

        assert len(velocity) == len(values)
        assert velocity[0] == 0.0  # First value has no velocity
        assert all(v >= 0 for v in velocity[1:])  # Should be positive for increasing values

    def test_calculate_acceleration(self):
        """Test acceleration calculation."""
        analyzer = TimeSeriesAnalyzer()

        # Test with constant velocity
        velocity = [0, 1, 1, 1, 1]
        acceleration = analyzer.calculate_acceleration(velocity)

        assert len(acceleration) == len(velocity)
        assert acceleration[0] == 0.0  # First value has no acceleration
        assert acceleration[1] == 1.0  # First acceleration
        assert all(a == 0 for a in acceleration[2:])  # Should be zero for constant velocity

    def test_calculate_z_score_spike(self):
        """Test z-score spike calculation."""
        analyzer = TimeSeriesAnalyzer()

        # Test with normal distribution and one outlier
        values = [1, 1, 1, 1, 1, 10]  # Outlier at the end
        z_scores = analyzer.calculate_z_score_spike(values, window=5)

        assert len(z_scores) == len(values)
        assert z_scores[0] == 0.0  # First value
        assert z_scores[-1] > 2.0  # Should detect the outlier

    def test_calculate_convergence(self):
        """Test convergence calculation."""
        analyzer = TimeSeriesAnalyzer()

        source_counts = {
            "arxiv": [1, 0, 1, 1],
            "github": [0, 1, 1, 1],
            "jobs": [0, 0, 0, 1],
            "funding": [0, 0, 0, 0]
        }

        convergence = analyzer.calculate_convergence(source_counts)

        assert len(convergence) == 4
        assert convergence[0] == 0.25  # 1/4 sources active
        assert convergence[1] == 0.25  # 1/4 sources active
        assert convergence[2] == 0.5   # 2/4 sources active
        assert convergence[3] == 0.75  # 3/4 sources active

    def test_smooth_series(self):
        """Test series smoothing."""
        analyzer = TimeSeriesAnalyzer()

        # Test with noisy data
        values = [1, 5, 2, 6, 3, 7, 4, 8, 5, 9]
        smoothed = analyzer.smooth_series(values, window=3)

        assert len(smoothed) == len(values)
        assert smoothed[0] == 1.0  # First value unchanged
        # Smoothed values should be less noisy
        assert abs(smoothed[1] - 3.0) < 1.0  # Approximate average

    def test_calculate_trend_strength(self):
        """Test trend strength calculation."""
        analyzer = TimeSeriesAnalyzer()

        # Test with strong upward trend
        values = [1, 2, 3, 4, 5]
        strength = analyzer.calculate_trend_strength(values)

        assert 0 <= strength <= 1
        assert strength > 0.8  # Should be high for strong trend

        # Test with no trend
        values = [1, 1, 1, 1, 1]
        strength = analyzer.calculate_trend_strength(values)

        assert strength == 0.0  # Should be zero for no trend

    def test_calculate_volatility(self):
        """Test volatility calculation."""
        analyzer = TimeSeriesAnalyzer()

        # Test with constant values
        values = [1, 1, 1, 1, 1, 1, 1]
        volatility = analyzer.calculate_volatility(values, window=5)

        assert len(volatility) == len(values)
        assert volatility[0] == 0.0  # First values
        assert volatility[-1] == 0.0  # Should be zero for constant values

        # Test with variable values
        values = [1, 2, 1, 3, 1, 4, 1]
        volatility = analyzer.calculate_volatility(values, window=3)

        assert volatility[-1] > 0  # Should be positive for variable values


class TestTopicMapper:
    """Test topic mapper."""

    def test_find_best_topic_match(self):
        """Test topic matching."""
        mapper = TopicMapper()

        # Mock topic keywords
        mapper.keyword_cache = {
            "ai": ["artificial intelligence", "machine learning", "ai"],
            "robotics": ["robots", "automation", "robotic"],
            "quantum": ["quantum computing", "quantum", "qubits"]
        }

        # Test AI content
        content = "This paper presents a new machine learning algorithm for artificial intelligence applications."
        topic_id = mapper._find_best_topic_match(content)

        assert topic_id == "ai"  # Should match AI topic

        # Test robotics content
        content = "We propose a new robotic system for automation tasks."
        topic_id = mapper._find_best_topic_match(content)

        assert topic_id == "robotics"  # Should match robotics topic

        # Test no match
        content = "This is about cooking recipes and food preparation."
        topic_id = mapper._find_best_topic_match(content)

        assert topic_id is None  # Should not match any topic

    def test_calculate_keyword_score(self):
        """Test keyword scoring."""
        mapper = TopicMapper()

        keywords = ["machine learning", "artificial intelligence", "ai"]

        # Test exact match
        content = "This paper is about machine learning and artificial intelligence."
        score = mapper._calculate_keyword_score(content, keywords)

        assert score > 0  # Should have positive score

        # Test partial match
        content = "This paper is about machine learning."
        score = mapper._calculate_keyword_score(content, keywords)

        assert score > 0  # Should have positive score
        assert score < 1.0  # But less than perfect match

        # Test no match
        content = "This paper is about cooking."
        score = mapper._calculate_keyword_score(content, keywords)

        assert score == 0  # Should have zero score
