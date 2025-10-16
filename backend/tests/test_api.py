"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ..models.topic import Topic
from ..models.signal_event import SignalEvent


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "database" in data


def test_topics_list(client: TestClient, test_db: Session, sample_topic):
    """Test topics list endpoint."""
    # Create a test topic
    topic = Topic(**sample_topic)
    test_db.add(topic)
    test_db.commit()
    
    response = client.get("/topics")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == sample_topic["id"]
    assert data[0]["name"] == sample_topic["name"]


def test_topics_leaderboard_empty(client: TestClient):
    """Test topics leaderboard with no data."""
    response = client.get("/topics/leaderboard")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 0


def test_signals_list(client: TestClient, test_db: Session, sample_signal_event):
    """Test signals list endpoint."""
    # Create a test signal event
    event = SignalEvent(**sample_signal_event)
    test_db.add(event)
    test_db.commit()
    
    response = client.get("/signals")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["id"] == sample_signal_event["id"]


def test_signals_filter_by_source(client: TestClient, test_db: Session, sample_signal_event):
    """Test signals filtering by source."""
    # Create a test signal event
    event = SignalEvent(**sample_signal_event)
    test_db.add(event)
    test_db.commit()
    
    response = client.get("/signals?source=arxiv")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    
    # Test with non-matching source
    response = client.get("/signals?source=github")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 0


def test_topic_not_found(client: TestClient):
    """Test topic detail for non-existent topic."""
    response = client.get("/topics/non-existent-topic")
    assert response.status_code == 404
    
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_signals_search(client: TestClient, test_db: Session, sample_signal_event):
    """Test signals search endpoint."""
    # Create a test signal event
    event = SignalEvent(**sample_signal_event)
    test_db.add(event)
    test_db.commit()
    
    response = client.get("/signals/search?query=test")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_found"] == 1
    assert len(data["results"]) == 1


def test_forecasts_leaderboard_empty(client: TestClient):
    """Test forecasts leaderboard with no data."""
    response = client.get("/forecasts/leaderboard")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 0
    assert len(data["forecasts"]) == 0
