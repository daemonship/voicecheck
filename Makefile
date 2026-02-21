.PHONY: help install dev test lint format clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies
	@echo "Installing Python dependencies..."
	pip install -e ".[dev]"
	@echo "Installing Node dependencies..."
	cd frontend && npm install

dev: ## Run development servers
	@echo "Starting backend..."
	python -m uvicorn backend.app.main:app --reload --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev

test: ## Run all tests
	@echo "Running Python tests..."
	python -m pytest -q
	@echo "Running Playwright tests..."
	cd frontend && npm test

test-backend: ## Run backend tests only
	python -m pytest -q

test-e2e: ## Run E2E tests only
	cd frontend && npm test

lint: ## Run linters
	@echo "Running ruff..."
	ruff check backend/
	@echo "Running frontend lint..."
	cd frontend && npm run lint

format: ## Format code
	@echo "Formatting Python code..."
	ruff format backend/
	@echo "Formatting frontend code..."
	cd frontend && npm run lint -- --fix

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mutmut-cache/
	rm -rf htmlcov/
	rm -rf frontend/node_modules/
	rm -rf frontend/dist/
	rm -rf playwright-report/
	rm -rf test-results/

setup-pre-commit: ## Install pre-commit hooks
	pre-commit install
