.PHONY: help setup setup-dev install test lint format typecheck check clean

help:
	@echo "PersonalRAGVault — common tasks"
	@echo "  make setup      Create .venv and install package"
	@echo "  make setup-dev  Install with dev dependencies"
	@echo "  make test       Run unit tests"
	@echo "  make lint       Ruff check"
	@echo "  make format     Ruff format"
	@echo "  make typecheck  Mypy"
	@echo "  make check      lint + typecheck + test"

setup:
	./scripts/setup.sh

setup-dev:
	./scripts/setup.sh --dev

install: setup-dev

test:
	pytest -m "not integration" -v

lint:
	ruff check src tests

format:
	ruff format src tests

typecheck:
	mypy src

check: lint typecheck test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
