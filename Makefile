.PHONY: help up down seed etl features forecast test test-coverage lint type-check fmt clean dev-seed rebuild

help: ## Show this help message
	@echo "Oracle - Multi-Domain Forecast Engine"
	@echo "====================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker-compose up --build -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs for all services
	docker-compose logs -f

seed: ## Load mock data and generate initial forecasts
	python simple_seed.py

etl: ## Run data ingestion pipeline
	docker-compose exec backend python -m ingestion.etl_runner

features: ## Rebuild feature matrix
	docker-compose exec backend python -m features.build_feature_matrix

forecast: ## Regenerate forecasts
	docker-compose exec backend python -m forecasting.baseline

rebuild: ## Run full pipeline: etl -> features -> forecast
	docker-compose exec backend python -c "from ingestion.etl_runner import main; from features.build_feature_matrix import main as build_features; from forecasting.baseline import main as forecast; main(); build_features(); forecast()"

test: ## Run all tests
	docker-compose exec backend python -m pytest tests/ -v

test-coverage: ## Run tests with coverage report
	docker-compose exec backend python -m pytest tests/ --cov=. --cov-report=term-missing

lint: ## Run linting checks
	docker-compose exec backend ruff check .
	docker-compose exec backend black --check .

type-check: ## Run type checking
	docker-compose exec backend mypy .

fmt: ## Format code
	docker-compose exec backend ruff check --fix .
	docker-compose exec backend black .

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

dev-seed: ## Quick development seed (local only)
	cd backend && python scripts/dev_seed.py

# Local development shortcuts
local-up: ## Start only database locally
	docker-compose up db -d

local-backend: ## Run backend locally (requires local-up)
	cd backend && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

local-frontend: ## Run frontend locally
	cd frontend && npm run dev

# Database management
db-shell: ## Connect to database shell
	docker-compose exec db psql -U oracle -d oracle

db-reset: ## Reset database (WARNING: destroys all data)
	docker-compose exec db psql -U oracle -d oracle -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	docker-compose exec backend python -m alembic upgrade head

# Monitoring
status: ## Show service status
	docker-compose ps

health: ## Check service health
	curl -f http://localhost:8000/health || echo "Backend not ready"
	curl -f http://localhost:5173 || echo "Frontend not ready"
