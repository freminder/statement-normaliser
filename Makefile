# Four commands you should be able to run in every project from now on.
# Muscle memory: `make check` before every commit.

.PHONY: install test lint typecheck check run clean

install:
	uv sync
	uv run pre-commit install

test:
	uv run pytest --cov=src --cov-report=term-missing

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy

check: lint typecheck test

run:
	uv run normalise --input examples/ --output out/canonical.csv

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov out
	find . -type d -name __pycache__ -exec rm -rf {} +
