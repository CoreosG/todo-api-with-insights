.PHONY: lint format type-check

lint:
	@echo "Running Ruff linter..."
	ruff check . --fix

format:
	@echo "Running Black formatter..."
	black .

type-check:
	@echo "Running MyPy type checker..."
	mypy .

lint-all: format type-check lint
	@echo "All linting checks passed!"
