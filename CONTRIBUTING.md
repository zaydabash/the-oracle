# Contributing to The Oracle

Thank you for your interest in contributing to The Oracle! This document provides guidelines for setting up the development environment and contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (optional, for full stack)
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/the-oracle.git
   cd the-oracle
   ```

2. **Backend Setup**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Set up environment
   cp .env.example .env
   
   # Run with SQLite (quick start)
   python3 simple_seed.py  # Seed mock data
   python3 simple_api.py   # Start API server
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Full Stack with Docker**
   ```bash
   # Copy environment file
   cp .env.example .env
   
   # Start all services
   docker compose up -d --build
   
   # Seed data
   make seed
   ```

### Environment Variables

Key environment variables in `.env`:

```bash
# Database
DATABASE_URL=sqlite:///oracle.db  # or postgresql://user:pass@localhost/db

# Mode
ORACLE_MODE=mock  # or 'live' for real data sources

# API Keys (for live mode)
GITHUB_TOKEN=your_github_token
ARXIV_API_KEY=optional
CRUNCHBASE_API_KEY=optional

# Admin
ORACLE_ADMIN_KEY=dev123
```

## Data Seeding

The project includes deterministic mock data for development:

```bash
# Seed mock data (120 days, 20 topics, 5-15 events/day)
python3 simple_seed.py

# Or via Makefile
make seed
```

This creates:
- 20 topics with keywords
- 120 days of signal events across 4 sources
- Mock features and forecasts
- Surge scores and breakdowns

## API Development

### Running the API

```bash
# Development server
python3 simple_api.py

# Or with uvicorn
uvicorn simple_api:app --reload --host 0.0.0.0 --port 8000
```

### Key Endpoints

- `GET /health` - Health check
- `GET /topics` - Topic leaderboard
- `GET /topics/{id}` - Topic details with forecast
- `GET /signals` - Signal events
- `POST /admin/rebuild` - Rebuild database (dev only)

### Testing

```bash
# Run backend tests
pytest backend/tests/

# Run with coverage
pytest --cov=backend backend/tests/

# Frontend tests
cd frontend && npm test
```

## Code Quality

### Python

```bash
# Format code
black .
ruff check . --fix

# Type checking
mypy backend/
```

### Frontend

```bash
cd frontend

# Format code
npm run format

# Lint
npm run lint

# Type check
npm run type-check
```

## Project Structure

```
the-oracle/
├── backend/           # FastAPI backend
│   ├── api/          # API routes
│   ├── core/         # Core utilities
│   ├── features/     # Feature extraction
│   ├── forecasting/  # ML forecasting
│   ├── ingestion/    # Data ingestion
│   ├── models/       # Database models
│   ├── narratives/   # Narrative generation
│   └── tests/        # Backend tests
├── frontend/         # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
│   └── public/
├── data/             # Mock data files
├── scripts/          # Utility scripts
└── docs/             # Documentation
```

## Pull Request Process

1. **Fork and branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Follow existing code style
   - Add tests for new features
   - Update documentation

3. **Test locally**
   ```bash
   # Backend tests
   pytest backend/tests/
   
   # Frontend tests
   cd frontend && npm test
   
   # Integration test
   python3 simple_seed.py && python3 simple_api.py
   curl http://localhost:8000/health
   ```

4. **Submit PR**
   - Clear description of changes
   - Reference any related issues
   - Ensure CI passes

## Architecture Notes

### Data Flow

1. **Ingestion**: External APIs → SignalEvents
2. **Features**: SignalEvents → TopicFeatures (velocity, acceleration, etc.)
3. **Forecasting**: TopicFeatures → TopicForecasts (ARIMA/Prophet)
4. **Ranking**: TopicForecasts → Surge scores
5. **API**: Serve data to frontend
6. **UI**: Visualize trends and forecasts

### Key Components

- **Signal Events**: Raw data from arXiv, GitHub, jobs, funding
- **Topic Features**: Aggregated metrics (velocity, acceleration, convergence)
- **Forecasts**: 30-day predictions with confidence bands
- **Surge Scores**: Explainable 0-100% ranking with breakdown
- **Narratives**: Auto-generated summaries with citations

## Troubleshooting

### Common Issues

**API won't start**
```bash
# Check if port 8000 is free
lsof -i :8000

# Kill existing processes
pkill -f simple_api
```

**Database locked (SQLite)**
```bash
# Remove lock file
rm -f oracle.db-wal oracle.db-shm
```

**Frontend can't reach API**
```bash
# Check CORS settings in .env
ORIGIN=http://localhost:5173
```

**No data showing**
```bash
# Re-seed database
python3 simple_seed.py
```

## Questions?

- Check existing issues on GitHub
- Join our discussions
- Create a new issue with the "question" label

Thank you for contributing to The Oracle!
