.PHONY: test test-unit test-integration test-coverage clean lint install-test-deps

# Test commands
test: install-test-deps
	python -m pytest tests/ -v

test-unit: install-test-deps
	python -m pytest tests/unit/ -v -m "not slow"

test-integration: install-test-deps
	python -m pytest tests/integration/ -v

test-coverage: install-test-deps
	python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Install test dependencies
install-test-deps:
	pip install -r requirements-test.txt

# Linting and code quality
lint:
	python -m flake8 app/ tests/ --max-line-length=100 --exclude=__pycache__

# Clean up generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# Run all checks
check: lint test-coverage

# Quick development test
dev-test: test-unit
