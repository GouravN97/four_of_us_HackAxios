.PHONY: help install test lint format clean dev

help:  ## Show this help message
	@echo "Patient Risk Classifier Backend - Development Commands"
	@echo "======================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

test:  ## Run all tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=src --cov-report=html --cov-report=term

test-property:  ## Run property-based tests only
	pytest -m property_tests

lint:  ## Run linting
	flake8 src tests
	mypy src

format:  ## Format code
	black src tests
	isort src tests

format-check:  ## Check code formatting
	black --check src tests
	isort --check-only src tests

clean:  ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

dev:  ## Start development server
	python run_demo.py

setup:  ## Initial project setup
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # Linux/Mac"
	@echo "  venv\\Scripts\\activate     # Windows"