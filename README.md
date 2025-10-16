# The Oracle — Quant Intelligence Engine

> **A quantitative intelligence platform that fuses weak signals from multiple data sources to forecast emerging technology trends**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-70%25%2B-blue)
![Tech](https://img.shields.io/badge/stack-FastAPI%20%7C%20React%20%7C%20Postgres-informational)

## Project Overview

The Oracle is a signal intelligence platform that ingests data from research publications, code repositories, job markets, and funding flows to predict which technologies are about to experience explosive growth. Think of it as a quantitative alpha engine for innovation trends.

### Key Features

- **Multi-Source Signal Ingestion**: arXiv papers, GitHub activity, job postings, funding rounds
- **Topic Mapping & Feature Engineering**: Automated categorization with velocity/acceleration metrics
- **Forecasting Engine**: ARIMA/Prophet models with confidence intervals
- **Surge Ranking**: Probability scores for breakout potential
- **Interactive Dashboard**: Real-time leaderboard with detailed analytics
- **Narrative Intelligence**: Executive summaries with citations

## Quick Start (60 seconds)

```bash
# Clone and start in mock mode
git clone <repo-url>
cd the-oracle
cp .env.example .env
make up && make seed

# Visit dashboard at http://localhost:5173
# API docs at http://localhost:8000/docs
```

### Demo Screenshots & GIFs

To create demo assets for presentations:

```bash
# macOS quick GIF of the flow (Dashboard -> Topic Detail)
# 1) Cmd+Shift+5 to record a region (10s), saves to ./artifacts/demo.mov
ffmpeg -y -i artifacts/demo.mov -vf "fps=12,scale=1200:-1:flags=lanczos" artifacts/demo.gif

# Generate weekly digest
python3 scripts/export_digest.py
```

Embed in README: `![Demo](artifacts/demo.gif)`

### Production Run Options

**Local Postgres (compose)**
```bash
cp .env.example .env && make up && make seed
```

**SQLite quick try**
```bash
# Set DATABASE_URL=sqlite:///oracle.db → make up && make seed
```

**Live mode**
```bash
# ORACLE_MODE=live + GITHUB_TOKEN (optional)
make etl && make features && make forecast
```

### Why This Won't Break

**Deterministic mocks** ensure great charts even offline.  
**Explainable scoring** (0–100% + breakdown) → auditable.  
**Graceful degradation**: missing API keys or rate limits don't crash the pipeline.  
**Separation of concerns**: ingestion → features → forecast → rank → API → UI.

## Architecture

```mermaid
flowchart LR
A["Ingestion: arXiv/GitHub/Jobs/Funding"] --> B["Normalize SignalEvents"]
B --> C["Feature Builder: velocity/accel/z-spike/convergence"]
C --> D["Forecast: ARIMA/Prophet"]
D --> E["Ranker: surge_score_pct + breakdown"]
E --> F["API /topics /topics/id"]
F --> G["Dashboard: Leaderboard + Topic Detail"]
```

## Data Model

```mermaid
erDiagram
    Topic ||--o{ SignalEvent : contains
    Topic ||--o{ TopicFeatures : generates
    Topic ||--o{ TopicForecast : predicts
    
    Topic {
        string id PK
        string name
        json keywords
        datetime created_at
    }
    
    SignalEvent {
        string id PK
        string source
        string topic_id FK
        string title
        string url
        datetime ts
        float magnitude
        json meta
    }
    
    TopicFeatures {
        string id PK
        string topic_id FK
        date date
        int mention_count_total
        float velocity
        float acceleration
        float z_spike
        float convergence
    }
    
    TopicForecast {
        string id PK
        string topic_id FK
        int horizon_days
        json forecast_curve
        float surge_score
        datetime updated_at
    }
```

## Usage

### Mock Mode (Default)
Perfect for development and demos - uses pre-generated realistic data:

```bash
make up        # Start all services
make seed      # Load mock data and generate forecasts
```

### Live Mode
Connect to real data sources:

```bash
# Set environment variables
export ORACLE_MODE=live
export GITHUB_TOKEN=your_token
export CRUNCHBASE_API_KEY=your_key

make etl       # Run data ingestion
make features  # Rebuild features
make forecast  # Regenerate predictions
```

## How Surge Scoring Works

The surge score combines multiple signals to predict breakout probability (0-100%):

```
surge_score_pct = 100 * sigmoid(
    velocity_growth * 0.9 +
    z_spike * 0.5 +
    convergence * 0.4 -
    uncertainty_penalty * 0.6
)
```

**Components:**
- **Velocity Growth**: 30-day percentage change in mention velocity
- **Z-Spike**: Statistical anomaly detection for sudden activity bursts  
- **Convergence**: Cross-source signal strength (arXiv + GitHub + Jobs + Funding)
- **Uncertainty Penalty**: Model confidence adjustment

Hover over "(why?)" in the leaderboard to see component breakdown.

## Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose

### Local Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -e .
make test

# Frontend  
cd frontend
npm install
npm run dev

# Full stack
make up
```

### Testing
```bash
make test              # Run all tests
make test-coverage     # Generate coverage report
make lint              # Check code quality
make type-check        # Type checking
```

## API Reference

### Core Endpoints

- `GET /topics` - List all topics with surge scores
- `GET /topics/{id}` - Topic details with forecasts
- `GET /signals` - Raw signal events with filtering
- `POST /rebuild` - Trigger full pipeline rebuild
- `GET /health` - System health check

### Example Response

```json
{
  "topics": [
    {
      "id": "multimodal-agents",
      "name": "Multimodal Retrieval Agents",
      "surge_score": 0.78,
      "velocity": 2.34,
      "acceleration": 0.45,
      "forecast": {
        "horizon_30d": 0.82,
        "horizon_90d": 0.76,
        "confidence": 0.68
      }
    }
  ]
}
```

## Sample Output

> **"Multimodal retrieval agents show elevated momentum (+134% publications, +62% GitHub stars WoW). Convergence across arXiv+GitHub+jobs suggests early inflection. 78% surge probability over next quarter (model: ARIMA, MAE=0.12)."**

## Security

- **Local Development Only**: No authentication required for MVP
- **Environment Variables**: All sensitive data via `.env`
- **CORS Protection**: Restricted to localhost in development
- **Input Validation**: All API inputs validated with Pydantic

## Roadmap

### Phase 2: Advanced Intelligence
- [ ] Transformer-based forecasting with uncertainty bands
- [ ] Interactive knowledge graph of trend clusters
- [ ] Model fine-tuning and backtesting framework
- [ ] PDF digest generation and email subscriptions

### Phase 3: Strategic Weapon
- [ ] Dozens of live signal sources (patents, social media, news)
- [ ] User authentication and personalized watchlists
- [ ] Real-time streaming updates
- [ ] Advanced explainable AI for signal attribution

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For questions or issues:
- Create an issue in the GitHub repository
- Check the [documentation](docs/)
- Review the [API documentation](http://localhost:8000/docs)

**Built for the future of quantitative intelligence**
