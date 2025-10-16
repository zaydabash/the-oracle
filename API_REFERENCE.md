# API Reference

The Oracle API provides endpoints for accessing forecast data, topics, and signal events.

## Base URL

- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Authentication

Most endpoints are public. Admin endpoints require an API key:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/admin/rebuild
```

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Response:**
```json
{
  "status": "ok"
}
```

---

### Topics

#### GET /topics

Get the topic leaderboard with surge scores.

**Query Parameters:**
- `limit` (optional): Number of topics to return (default: 20)

**Response:**
```json
[
  {
    "id": "1",
    "name": "multimodal retrieval agents",
    "surge_score": 0.85,
    "surge_score_pct": 85.0,
    "surge_score_breakdown": {
      "velocity_growth": 0.12,
      "z_spike": 0.8,
      "convergence": 0.9,
      "uncertainty_penalty": -0.2
    },
    "sparkline": [1.2, 1.4, 1.6, 1.8, 2.0],
    "forecast_available": true,
    "narrative": "Strong growth in multimodal retrieval research...",
    "evidence": ["arXiv: 15 new papers", "GitHub: 8 repositories"]
  }
]
```

#### GET /topics/{topic_id}

Get detailed information for a specific topic.

**Path Parameters:**
- `topic_id`: Topic identifier

**Response:**
```json
{
  "id": "1",
  "name": "multimodal retrieval agents",
  "narrative": "Detailed narrative about the topic...",
  "evidence": [
    "arXiv: 15 new papers in the last 30 days",
    "GitHub: 8 new repositories with significant stars",
    "Jobs: 5 new job postings related to this topic",
    "Funding: 1 new funding round announced"
  ],
  "keywords": ["multimodal", "retrieval", "agents"],
  "forecast": {
    "forecast_curve": [
      {
        "date": "2025-01-15",
        "yhat": 2.1,
        "yhat_lower": 1.8,
        "yhat_upper": 2.4
      }
    ],
    "horizon_days": 30
  },
  "velocity_trend": [1.0, 1.1, 1.2, 1.3, 1.4],
  "acceleration_trend": [0.05, 0.06, 0.07, 0.08, 0.09],
  "contributing_sources": {
    "arxiv": 15,
    "github": 8,
    "jobs": 5,
    "funding": 1
  },
  "surge_score_pct": 85.0,
  "surge_score_breakdown": {
    "velocity_growth": 0.12,
    "z_spike": 0.8,
    "convergence": 0.9,
    "uncertainty_penalty": -0.2
  }
}
```

---

### Signals

#### GET /signals

Get signal events (raw data points).

**Query Parameters:**
- `topic_id` (optional): Filter by topic ID
- `start` (optional): Start date (ISO format)
- `end` (optional): End date (ISO format)
- `source` (optional): Filter by source (arxiv, github, jobs, funding)
- `limit` (optional): Number of results (default: 100)

**Response:**
```json
[
  {
    "source": "arxiv",
    "ts": "2025-01-10T12:00:00Z",
    "title": "Scaling Multimodal Retrieval Agents with Structured Memory",
    "magnitude": 1.0,
    "topic_id": "1",
    "meta": {
      "primary_category": "cs.CL"
    },
    "url": "https://arxiv.org/abs/2501.001"
  }
]
```

---

### Statistics

#### GET /stats

Get system statistics.

**Response:**
```json
{
  "total_topics": 20,
  "total_events": 23952,
  "last_updated": "2025-01-10T12:00:00Z",
  "sources": {
    "arxiv": {
      "events": 8000,
      "last_success": "2025-01-10T12:00:00Z"
    },
    "github": {
      "events": 12000,
      "last_success": "2025-01-10T12:00:00Z"
    },
    "jobs": {
      "events": 3000,
      "last_success": "2025-01-10T12:00:00Z"
    },
    "funding": {
      "events": 952,
      "last_success": "2025-01-10T12:00:00Z"
    }
  }
}
```

#### GET /status/sources

Get detailed status of data sources.

**Response:**
```json
{
  "arxiv": {
    "last_success": "2025-01-10T12:00:00Z",
    "events_count": 8000,
    "status": "healthy"
  },
  "github": {
    "last_success": "2025-01-10T12:00:00Z",
    "events_count": 12000,
    "status": "healthy"
  },
  "jobs": {
    "last_success": "2025-01-10T12:00:00Z",
    "events_count": 3000,
    "status": "healthy"
  },
  "funding": {
    "last_success": "2025-01-10T12:00:00Z",
    "events_count": 952,
    "status": "mock"
  }
}
```

---

### Admin (Development Only)

#### POST /admin/rebuild

Rebuild the database with fresh deterministic mock data.

**Headers:**
- `X-API-Key`: Admin API key

**Response:**
```json
{
  "status": "ok",
  "message": "Rebuilt with deterministic mock data"
}
```

---

## Data Models

### Topic

```typescript
interface Topic {
  id: string;
  name: string;
  surge_score: number;           // 0-1 scale
  surge_score_pct: number;       // 0-100% scale
  surge_score_breakdown: {
    velocity_growth: number;     // Recent growth rate
    z_spike: number;            // Statistical anomaly
    convergence: number;        // Signal alignment
    uncertainty_penalty: number; // Forecast uncertainty
  };
  sparkline: number[];          // Last 30 days of velocity
  forecast_available: boolean;
  narrative: string;
  evidence: string[];
}
```

### Forecast

```typescript
interface Forecast {
  forecast_curve: Array<{
    date: string;               // ISO date
    yhat: number;              // Predicted value
    yhat_lower: number;        // Lower confidence bound
    yhat_upper: number;        // Upper confidence bound
  }>;
  horizon_days: number;        // Forecast horizon (typically 30)
}
```

### Signal Event

```typescript
interface SignalEvent {
  id: string;
  source: 'arxiv' | 'github' | 'jobs' | 'funding';
  ts: string;                  // ISO timestamp
  title: string;
  magnitude: number;           // Signal strength
  topic_id: string;
  meta: Record<string, any>;   // Source-specific metadata
  url: string;                 // Link to original source
}
```

## Error Responses

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

Error response format:
```json
{
  "detail": "Error message"
}
```

## Rate Limits

- Public endpoints: 100 requests/minute
- Admin endpoints: 10 requests/minute

## Examples

### Get Top 5 Topics

```bash
curl "http://localhost:8000/topics?limit=5"
```

### Get Topic Details

```bash
curl "http://localhost:8000/topics/1"
```

### Get Recent Signals

```bash
curl "http://localhost:8000/signals?start=2025-01-01&end=2025-01-10&limit=10"
```

### Rebuild Database

```bash
curl -X POST \
  -H "X-API-Key: dev123" \
  "http://localhost:8000/admin/rebuild"
```

## SDK Examples

### Python

```python
import requests

# Get topics
response = requests.get("http://localhost:8000/topics")
topics = response.json()

# Get topic details
topic_id = topics[0]["id"]
response = requests.get(f"http://localhost:8000/topics/{topic_id}")
details = response.json()
```

### JavaScript

```javascript
// Get topics
const response = await fetch('http://localhost:8000/topics');
const topics = await response.json();

// Get topic details
const topicId = topics[0].id;
const detailResponse = await fetch(`http://localhost:8000/topics/${topicId}`);
const details = await detailResponse.json();
```

## WebSocket (Future)

Real-time updates will be available via WebSocket at `/ws` for live forecast updates and new signal notifications.
