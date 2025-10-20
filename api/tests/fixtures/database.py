"""
Centralized database fixtures for testing.

This module provides comprehensive database mocking and setup for both:
- Unit tests (with moto in-memory mocking)
- Integration tests (with local DynamoDB container)
"""

import os

import boto3
import pytest
from moto import mock_aws

# Environment-based configuration
USE_LOCAL_DYNAMODB = os.getenv("USE_LOCAL_DYNAMODB", "false").lower() == "true"
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8000")


def create_dynamodb_table(table_name: str = "todo-app-data") -> boto3.resource:
    """Create or get existing DynamoDB table with the schema defined in ADR-003."""

    if USE_LOCAL_DYNAMODB:
        # Use local DynamoDB endpoint
        dynamodb = boto3.resource(
            "dynamodb", endpoint_url=DYNAMODB_ENDPOINT, region_name="us-east-1"
        )
    else:
        # Use AWS DynamoDB (moto mock for testing)
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    try:
        # Try to get existing table first
        table = dynamodb.Table(table_name)
        # Check if table exists by trying to describe it
        _ = table.table_status
        print(f"Using existing table: {table_name}")
        return table
    except Exception:
        # Table doesn't exist, create it
        print(f"Creating new table: {table_name}")

    # Create table with comprehensive schema from ADR-003
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
            {"AttributeName": "GSI2PK", "AttributeType": "S"},
            {"AttributeName": "GSI2SK", "AttributeType": "S"},
            {"AttributeName": "GSI3PK", "AttributeType": "S"},
            {"AttributeName": "GSI3SK", "AttributeType": "S"},
            {"AttributeName": "GSI4PK", "AttributeType": "S"},
            {"AttributeName": "GSI4SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI2",
                "KeySchema": [
                    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI3",
                "KeySchema": [
                    {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI4",
                "KeySchema": [
                    {"AttributeName": "GSI4PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI4SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )

    # Wait for table to be created
    table.wait_until_exists()
    return table


# Unit Test Fixtures (Fast, Isolated)
@pytest.fixture(scope="function")
def mock_dynamodb():
    """Mock AWS services for fast unit tests."""
    with mock_aws():
        yield


@pytest.fixture(scope="function")
def mock_dynamodb_table(mock_dynamodb):
    """Mock DynamoDB table for unit tests."""
    return create_dynamodb_table()


# Integration Test Fixtures (Real Local DynamoDB)
@pytest.fixture(scope="module")
def local_dynamodb():
    """Local DynamoDB container for integration tests."""
    if not USE_LOCAL_DYNAMODB:
        pytest.skip("Local DynamoDB not enabled. Set USE_LOCAL_DYNAMODB=true")

    # Check if local DynamoDB is running
    try:
        dynamodb = boto3.resource(
            "dynamodb", endpoint_url=DYNAMODB_ENDPOINT, region_name="us-east-1"
        )
        # Try to list tables to verify connection
        dynamodb.tables.all()
    except Exception as e:
        pytest.skip(f"Local DynamoDB not available at {DYNAMODB_ENDPOINT}: {e}")

    return {"endpoint_url": DYNAMODB_ENDPOINT, "region": "us-east-1"}


@pytest.fixture(scope="function")
def integration_dynamodb_table(local_dynamodb):
    """Real local DynamoDB table for integration tests."""
    return create_dynamodb_table()


# Repository Factory Functions
def create_repository(
    table_name: str = "todo-app-data", endpoint_url: str = None, table=None
):
    """Create repository instances with environment-based configuration."""
    from src.repositories.idempotency_repository import IdempotencyRepository
    from src.repositories.task_repository import TaskRepository
    from src.repositories.user_repository import UserRepository

    region = "us-east-1"

    # If table is provided (for mock testing), use it directly
    if table:
        # Create repositories with the provided table (bypasses boto3 resource creation)
        user_repo = UserRepository.__new__(UserRepository)
        user_repo.table = table
        user_repo.dynamodb = table.meta.client

        task_repo = TaskRepository.__new__(TaskRepository)
        task_repo.table = table
        task_repo.dynamodb = table.meta.client

        idempotency_repo = IdempotencyRepository.__new__(IdempotencyRepository)
        idempotency_repo.table = table
        idempotency_repo.dynamodb = table.meta.client

        return {
            "user_repo": user_repo,
            "task_repo": task_repo,
            "idempotency_repo": idempotency_repo,
        }
    else:
        # Use normal constructor for integration tests
        return {
            "user_repo": UserRepository(
                table_name=table_name, region=region, endpoint_url=endpoint_url
            ),
            "task_repo": TaskRepository(
                table_name=table_name, region=region, endpoint_url=endpoint_url
            ),
            "idempotency_repo": IdempotencyRepository(
                table_name=table_name, region=region, endpoint_url=endpoint_url
            ),
        }


# Centralized Repository Fixtures
@pytest.fixture(scope="function")
def mock_repositories(mock_dynamodb_table):
    """Mock repositories for unit tests."""
    return create_repository(table=mock_dynamodb_table)


@pytest.fixture(scope="function")
def integration_repositories(integration_dynamodb_table):
    """Real repositories for integration tests."""
    return create_repository(endpoint_url=DYNAMODB_ENDPOINT)


# Database State Management
@pytest.fixture(scope="function")
def clean_database(mock_dynamodb_table):
    """Ensure clean database state for each test."""
    # Clear any existing data
    try:
        # Scan and delete all items (for mock tables)
        response = mock_dynamodb_table.scan()
        with mock_dynamodb_table.batch_writer() as batch:
            for item in response["Items"]:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
    except Exception:
        # Table might be empty, that's fine
        pass

    yield mock_dynamodb_table

    # Cleanup after test
    try:
        response = mock_dynamodb_table.scan()
        with mock_dynamodb_table.batch_writer() as batch:
            for item in response["Items"]:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
    except Exception:
        pass


# Test Data Helpers
def create_test_user(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    name: str = "Test User",
):
    """Helper to create test user data."""
    from src.models.user_models import UserCreate

    return UserCreate(email=email, name=name)


def create_test_task(
    user_id: str = "test-user-123",
    title: str = "Test Task",
    priority: str = "medium",
    status: str = "pending",
):
    """Helper to create test task data."""
    from src.models.task_models import Priority, TaskCreate, TaskStatus

    return TaskCreate(
        title=title, priority=Priority(priority), status=TaskStatus(status)
    )


# Database Health Check
@pytest.fixture(scope="session")
def database_health_check():
    """Check database connectivity for integration tests."""
    if USE_LOCAL_DYNAMODB:
        try:
            dynamodb = boto3.resource(
                "dynamodb", endpoint_url=DYNAMODB_ENDPOINT, region_name="us-east-1"
            )
            dynamodb.tables.all()
            return True
        except Exception:
            return False
    return True  # Mock tests don't need connectivity check
