.PHONY: lint format type-check serve-local serve-local-win

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

serve-local:
	@echo "Starting uvicorn with local development settings..."
	@echo "Environment variables:"
	@echo "  LOCAL_USER=true (for authentication)"
	@echo "  AWS_ACCESS_KEY_ID=dummy (for local DynamoDB)"
	@echo "  AWS_SECRET_ACCESS_KEY=dummy (for local DynamoDB)"
	@echo "  USE_LOCAL_DYNAMODB=true (for local database)"
	@echo "  DYNAMODB_ENDPOINT=http://localhost:8000 (local DynamoDB endpoint)"
	@echo ""
	@echo "Starting server at http://localhost:8000"
	@echo "API docs available at http://localhost:8000/docs"
	@echo ""
	LOCAL_USER=true \
	AWS_ACCESS_KEY_ID=dummy \
	AWS_SECRET_ACCESS_KEY=dummy \
	USE_LOCAL_DYNAMODB=true \
	DYNAMODB_ENDPOINT=http://localhost:8000 \
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

serve-local-win:
	@echo "Starting uvicorn with local development settings (Windows)..."
	powershell -Command "$$env:LOCAL_USER='true'; $$env:AWS_ACCESS_KEY_ID='dummy'; $$env:AWS_SECRET_ACCESS_KEY='dummy'; $$env:USE_LOCAL_DYNAMODB='true'; $$env:DYNAMODB_ENDPOINT='http://localhost:8000'; uvicorn src.main:app --reload --host 0.0.0.0 --port 8001"