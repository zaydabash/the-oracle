#!/usr/bin/env python3
"""Simple FastAPI server for testing The Oracle."""

import json
import os
import sqlite3
import subprocess
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="The Oracle API", version="0.1.0")
ADMIN_KEY = os.getenv("ORACLE_ADMIN_KEY", "dev123")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect("oracle.db")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/topics")
async def get_topics():
    """Get all topics with surge scores."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get topics with their latest forecast
    cursor.execute('''
    SELECT 
        t.id, 
        t.name, 
        tf.surge_score,
        tf.confidence,
        tf.growth_rate,
        tf.created_at
    FROM topics t
    LEFT JOIN topic_forecasts tf ON t.id = tf.topic_id
    WHERE tf.horizon_days = 30
    ORDER BY tf.surge_score DESC
    ''')

    topics = []
    for row in cursor.fetchall():
        surge_score = row[2] or 0.0
        surge_score_pct = round(surge_score * 100, 1)

        # Mock breakdown for now - in real implementation this would come from the ranker
        surge_score_breakdown = {
            "velocity_growth": round(0.4 + (surge_score - 0.5) * 0.6, 3),
            "z_spike": round(0.2 + (surge_score - 0.5) * 0.4, 3),
            "convergence": round(0.3 + (surge_score - 0.5) * 0.3, 3),
            "uncertainty_penalty": round(-0.1 + (surge_score - 0.5) * -0.2, 3)
        }

        topics.append({
            "id": row[0],
            "name": row[1],
            "surge_score": surge_score,
            "surge_score_pct": surge_score_pct,
            "surge_score_breakdown": surge_score_breakdown,
            "forecast_available": True,
            "confidence": row[3] or 0.0,
            "growth_rate": row[4] or 0.0,
            "updated_at": row[5]
        })

    conn.close()
    return topics

@app.get("/topics/{topic_id}")
async def get_topic_detail(topic_id: str):
    """Get detailed topic information."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get topic info
    cursor.execute('SELECT id, name, keywords FROM topics WHERE id = ?', (topic_id,))
    topic_row = cursor.fetchone()
    if not topic_row:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic = {
        "id": topic_row[0],
        "name": topic_row[1],
        "keywords": json.loads(topic_row[2])
    }

    # Get latest features
    cursor.execute('''
    SELECT velocity, acceleration, convergence, mention_count, date
    FROM topic_features 
    WHERE topic_id = ? 
    ORDER BY date DESC 
    LIMIT 1
    ''', (topic_id,))
    feature_row = cursor.fetchone()

    if feature_row:
        topic["metrics"] = {
            "velocity": feature_row[0],
            "acceleration": feature_row[1],
            "convergence": feature_row[2],
            "mention_count": feature_row[3],
            "date": feature_row[4]
        }

    # Get forecast
    cursor.execute('''
    SELECT growth_rate, confidence, forecast_curve, surge_score
    FROM topic_forecasts 
    WHERE topic_id = ? AND horizon_days = 30
    ORDER BY created_at DESC 
    LIMIT 1
    ''', (topic_id,))
    forecast_row = cursor.fetchone()

    if forecast_row:
        topic["forecast"] = {
            "growth_rate": forecast_row[0],
            "confidence": forecast_row[1],
            "forecast_curve": json.loads(forecast_row[2]),
            "surge_score": forecast_row[3]
        }

    # Get recent signals
    cursor.execute('''
    SELECT source, title, ts, magnitude
    FROM signal_events 
    WHERE topic_id = ? 
    ORDER BY ts DESC 
    LIMIT 10
    ''', (topic_id,))
    signals = []
    for row in cursor.fetchall():
        signals.append({
            "source": row[0],
            "title": row[1],
            "ts": row[2],
            "magnitude": row[3]
        })

    topic["recent_signals"] = signals

    # Generate simple narrative
    if forecast_row:
        topic["narrative"] = f"{topic['name']} shows {forecast_row[3]:.1%} surge potential with {forecast_row[1]:.1%} confidence. Recent growth rate: {forecast_row[0]:.1%}."

    conn.close()
    return topic

@app.get("/signals")
async def get_signals(topic_id: str = None, start: str = None, end: str = None):
    """Get signal events."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, source, title, url, ts, magnitude, meta FROM signal_events"
    params = []

    conditions = []
    if topic_id:
        conditions.append("topic_id = ?")
        params.append(topic_id)
    if start:
        conditions.append("ts >= ?")
        params.append(start)
    if end:
        conditions.append("ts <= ?")
        params.append(end)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY ts DESC LIMIT 100"

    cursor.execute(query, params)
    signals = []
    for row in cursor.fetchall():
        signals.append({
            "id": row[0],
            "source": row[1],
            "title": row[2],
            "url": row[3],
            "ts": row[4],
            "magnitude": row[5],
            "meta": json.loads(row[6]) if row[6] else {}
        })

    conn.close()
    return signals

@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM topics")
    total_topics = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM signal_events")
    total_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM topic_features")
    total_features = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM topic_forecasts")
    total_forecasts = cursor.fetchone()[0]

    conn.close()

    return {
        "total_topics": total_topics,
        "total_events": total_events,
        "total_features": total_features,
        "total_forecasts": total_forecasts,
        "last_updated": datetime.now().isoformat()
    }

@app.post("/admin/rebuild")
def admin_rebuild(x_api_key: str = Header(None)):
    """Rebuild database with fresh deterministic mock data."""
    if x_api_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Clear + reseed + recompute
        result = subprocess.run(["python3", "simple_seed.py"], check=True, capture_output=True, text=True)
        return {"status": "ok", "message": "Rebuilt with deterministic mock data", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": f"Rebuild failed: {e}", "stderr": e.stderr, "stdout": e.stdout}

@app.get("/status/sources")
def sources_status():
    """Get status of data sources."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get counts per source
    cursor.execute("SELECT source, COUNT(*) FROM signal_events GROUP BY source")
    source_counts = dict(cursor.fetchall())

    # Get latest event per source
    cursor.execute("SELECT source, MAX(ts) FROM signal_events GROUP BY source")
    latest_events = dict(cursor.fetchall())

    conn.close()

    return {
        "arxiv": {
            "last_success": latest_events.get("arxiv", "2025-10-15T10:00:00Z"),
            "events_count": source_counts.get("arxiv", 450)
        },
        "github": {
            "last_success": latest_events.get("github", "2025-10-15T09:30:00Z"),
            "events_count": source_counts.get("github", 320)
        },
        "jobs": {
            "last_success": latest_events.get("jobs", "2025-10-15T08:00:00Z"),
            "events_count": source_counts.get("jobs", 180)
        },
        "funding": {
            "status": "mock",
            "events_count": source_counts.get("funding", 90)
        }
    }

if __name__ == "__main__":
    print("Starting The Oracle API server...")
    print("Visit http://localhost:8000/docs for API documentation")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
