# ERPFTS Phase1 MVP Makefile
# Development and deployment automation

.PHONY: help install dev-install clean test lint format type-check pre-commit setup-dev
.PHONY: run-api run-ui run-dev init-db reset-db health-check build docker-build docker-run

# Default target
help:
	@echo "ERPFTS Phase1 MVP - Available Commands"
	@echo "====================================="
	@echo "Development:"
	@echo "  setup-dev     - Complete development environment setup"
	@echo "  install       - Install production dependencies"
	@echo "  dev-install   - Install development dependencies"
	@echo "  init-db       - Initialize database with default data"
	@echo "  reset-db      - Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Code Quality:"
	@echo "  test          - Run test suite"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code with black and isort"
	@echo "  type-check    - Run type checking with mypy"
	@echo "  pre-commit    - Run pre-commit hooks"
	@echo ""
	@echo "Server Management:"
	@echo "  run-api       - Start FastAPI server"
	@echo "  run-ui        - Start Streamlit UI"
	@echo "  run-dev       - Start both API and UI servers"
	@echo "  health-check  - Perform system health check"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  build         - Build distribution packages"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean temporary files and caches"

# Development setup
setup-dev: dev-install init-db
	@echo "✅ Development environment setup complete"
	@echo "   Run 'make run-dev' to start the development servers"

install:
	pip install -e .

dev-install:
	pip install -e .[dev]

# Database management
init-db:
	python -m erpfts.cli init-db

reset-db:
	python -m erpfts.cli reset-db --confirm

# TDD Development Workflow
test-tdd:
	pytest-watch --poll --clear --nobeep

test-fast:
	pytest tests/unit/ -x -v

test:
	pytest

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=85

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v

test-parallel:
	pytest -n auto

# TDD Phase-specific testing
test-red:
	pytest -m "red" --tb=short

test-green: 
	pytest -m "green" -x

test-refactor:
	pytest -m "refactor" --cov=src

# Code quality
lint:
	flake8 src tests
	black --check src tests
	isort --check-only src tests

format:
	black src tests
	isort src tests

type-check:
	mypy src

pre-commit:
	pre-commit run --all-files

# Server management
run-api:
	python -m erpfts.cli run-api

run-ui:
	python -m erpfts.cli run-ui

run-dev:
	python -m erpfts.cli dev-server

health-check:
	python -m erpfts.cli health-check

# Build and packaging
build:
	python -m build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

# Docker operations
docker-build:
	docker build -t erpfts-phase1:latest .

docker-run:
	docker run -p 8000:8000 -p 8501:8501 -v $(PWD)/data:/app/data erpfts-phase1:latest

# Development utilities
check-deps:
	pip-audit
	safety check

update-deps:
	pip-compile requirements.in
	pip-compile requirements-dev.in

# Quick development workflow
quick-start: clean setup-dev run-dev

# Production deployment checks
prod-check: lint type-check test
	@echo "✅ Production readiness checks passed"

# Documentation
docs-serve:
	mkdocs serve

docs-build:
	mkdocs build