#!/usr/bin/env python3
"""Deterministic seed script for The Oracle with rich mock data."""

import os, json, random, datetime as dt
from pathlib import Path
import sqlite3

random.seed(42)

ROOT = Path(__file__).resolve().parents[0]
TOPICS = json.loads(Path("data/topic_keywords.json").read_text(encoding="utf-8"))

START = dt.date.today() - dt.timedelta(days=120)
END = dt.date.today() - dt.timedelta(days=1)
SOURCES = ["arxiv","github","jobs","funding"]

def daterange(start, end):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)

def connect():
    # If you have DATABASE_URL Postgres, you can adapt—this is the quick SQLite path.
    return sqlite3.connect("oracle.db")

def reset_db(c):
    c.executescript("""
    PRAGMA foreign_keys=OFF;
    DELETE FROM signal_events;
    DELETE FROM topic_features;
    DELETE FROM topic_forecasts;
    DELETE FROM topics;
    PRAGMA foreign_keys=ON;
    """)

def ensure_topics(c, conn):
    for t in TOPICS["topics"][:20]:  # take 20; we need ≥12
        c.execute("INSERT OR IGNORE INTO topics (id, name, keywords) VALUES (?, ?, ?)", 
                 (t["id"], t["name"], json.dumps(t["keywords"])))
    conn.commit()

def topic_ids(c):
    return [r[0] for r in c.execute("SELECT id FROM topics").fetchall()]

def insert_event(c, topic_id, d, source, mag, title, event_num):
    c.execute("""
      INSERT INTO signal_events (id, topic_id, source, ts, title, magnitude, meta, url)
      VALUES (?, ?, ?, ?, ?, ?, '{}', '')
    """, (f"{source}_{topic_id}_{d}_{event_num}", topic_id, source, f"{d}T12:00:00Z", title, mag))

def seed_events(c, conn):
    ids = topic_ids(c)
    for tid in ids:
        base = random.uniform(0.5, 1.5)
        for d in daterange(START, END):
            # 5–15 events/day distributed across sources with trend + noise
            num = random.randint(5,15)
            for i in range(num):
                source = random.choice(SOURCES)
                trend = 1.0 + 0.005 * ((d-START).days)  # gentle uptrend
                season = 1.0 + 0.2 * (1 if d.weekday()<5 else -0.5)  # weekdays higher
                mag = round(max(0.1, random.gauss(base*trend*season, 0.3)), 2)
                insert_event(c, tid, d, source, mag, f"{source} signal {d} t{tid}", i)
    conn.commit()

def build_features(c, conn):
    """Build mock features for all topics."""
    ids = topic_ids(c)
    for tid in ids:
        for d in daterange(START, END):
            # Mock feature data with realistic trends
            velocity = 1.0 + 0.01 * ((d-START).days) + random.gauss(0, 0.1)
            acceleration = 0.01 + random.gauss(0, 0.005)
            convergence = 0.5 + 0.005 * ((d-START).days) + random.gauss(0, 0.05)
            mention_count = int(10 + 0.1 * ((d-START).days) + random.gauss(0, 3))
            
            c.execute("""
            INSERT OR REPLACE INTO topic_features 
            (id, topic_id, date, velocity, acceleration, convergence, mention_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (f"feature_{tid}_{d}", tid, d.isoformat(), velocity, acceleration, convergence, mention_count))
    conn.commit()

def build_forecasts(c, conn):
    """Build mock forecasts for all topics."""
    ids = topic_ids(c)
    for tid in ids:
        # Create forecast for 30-day horizon
        forecast_curve = []
        for i in range(30):
            future_date = END + dt.timedelta(days=i+1)
            base_value = 2.0 + (i * 0.05)
            forecast_curve.append({
                "date": future_date.isoformat(),
                "yhat": base_value,
                "yhat_lower": base_value - 0.3,
                "yhat_upper": base_value + 0.3
            })
        
        # Calculate surge score components
        pct_increase_30d = random.uniform(0.1, 0.3)  # 10-30% growth
        z_spike_recent = random.uniform(0.5, 2.0)    # Recent spike
        convergence_30d = random.uniform(0.6, 1.0)   # Cross-source convergence
        uncertainty_width_norm = random.uniform(0.1, 0.3)  # Uncertainty
        
        # Surge score calculation (0-100%)
        w1, w2, w3, w4 = 0.9, 0.5, 0.4, 0.6
        raw = (w1 * pct_increase_30d + w2 * z_spike_recent + w3 * convergence_30d - w4 * uncertainty_width_norm)
        surge_score_pct = round(100 * (1.0 / (1.0 + (2.71828 ** -raw))), 1)
        
        c.execute("""
        INSERT INTO topic_forecasts 
        (id, topic_id, horizon_days, model_type, growth_rate, confidence, forecast_curve, surge_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"forecast_{tid}_30d",
            tid,
            30,
            "ARIMA",
            pct_increase_30d,
            0.75,
            json.dumps(forecast_curve),
            surge_score_pct / 100.0  # Store as 0-1 for backward compatibility
        ))
    conn.commit()

def build_features_and_forecasts(c, conn):
    """Build features and forecasts for all topics."""
    build_features(c, conn)
    build_forecasts(c, conn)

if __name__ == "__main__":
    print("Creating deterministic mock data...")
    with connect() as con:
        cur = con.cursor()
        reset_db(cur)
        ensure_topics(cur, con)
        seed_events(cur, con)
        build_features_and_forecasts(cur, con)
    
    print("Seed complete: >=12 topics, 120 days of events.")
    print("Visit http://localhost:5173 for the dashboard")