.PHONY: help install lint fmt check test run clean

# Default target
help:
	@echo "Available targets:"
	@echo "  make install  - Install all dependencies"
	@echo "  make lint     - Run all linters (ruff + mypy)"
	@echo "  make fmt      - Format all code"
	@echo "  make check    - Run type checking only"
	@echo "  make test     - Run all tests"
	@echo "  make run      - Run the application"
	@echo "  make clean    - Clean build artifacts"

# Install dependencies
install:
	@echo "Installing dependencies..."
	uv pip install -e ".[dev]"
	@echo "Dependencies installed!"

# Linting (ruff + mypy)
lint:
	@echo "Running ruff check..."
	uv run ruff check imessage_data_foundry/ tests/
	@echo "Checking formatting..."
	uv run ruff format --check imessage_data_foundry/ tests/
	@echo "Running mypy..."
	uv run mypy imessage_data_foundry/
	@echo "All linting complete!"

# Format code
fmt:
	@echo "Formatting code..."
	uv run ruff format imessage_data_foundry/ tests/
	uv run ruff check --fix imessage_data_foundry/ tests/
	@echo "Formatting complete!"

# Type checking only
check:
	@echo "Running mypy..."
	uv run mypy imessage_data_foundry/

# Run tests
test:
	@echo "Running tests..."
	uv run pytest tests/ -v

# Run the application
run:
	@echo "Starting iMessage Data Foundry..."
	uv run python -m imessage_data_foundry

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__ .coverage htmlcov
	rm -rf imessage_data_foundry/__pycache__ tests/__pycache__
	rm -rf dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"
