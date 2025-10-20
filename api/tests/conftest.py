"""
Pytest configuration and shared fixtures for the API tests.

This file makes fixtures from the fixtures/ directory available to all tests.
"""

# Import fixtures to make them available to all tests
from .fixtures.database import (
    mock_dynamodb,
    mock_dynamodb_table,
    mock_repositories,
    integration_repositories,
    local_dynamodb,
    integration_dynamodb_table,
    clean_database,
    database_health_check,
    create_test_user,
    create_test_task,
)
