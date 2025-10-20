from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.task_models import (
    Priority,
    TaskResponse,
    TaskStatus,
)

client = TestClient(app)


# Mock Services for testing
@pytest.fixture
def mock_task_service(mocker):
    mock_service = mocker.Mock()
    mocker.patch(
        "src.utils.dependency_injection.get_task_service", return_value=mock_service
    )
    mocker.patch(
        "src.controllers.task_controller.get_user_context",
        return_value=Mock(
            user_id="test-user-123", email="test@example.com", name="Test User"
        ),
    )

    # Mock the user service to avoid real create_or_get_user calls
    mock_user_service = mocker.Mock()
    mock_user_service.create_or_get_user = mocker.AsyncMock(
        return_value=Mock(
            id="test-user-123", email="test@example.com", name="Test User"
        )
    )
    mocker.patch(
        "src.utils.dependency_injection.get_user_service",
        return_value=mock_user_service,
    )

    # Mock the user repository to avoid DynamoDB calls during create_or_get_user
    mock_user_repo = mocker.Mock()
    mock_user_repo.get_user = mocker.AsyncMock(
        return_value=None
    )  # No user exists initially
    mock_user_repo.create_user = mocker.AsyncMock(
        return_value=Mock(
            id="test-user-123", email="test@example.com", name="Test User"
        )
    )
    mocker.patch("src.utils.dependency_injection.user_repo", mock_user_repo)
    return mock_service


# Happy Path Tests
class TestTaskControllerCreate:
    def test_create_task_success(self, mock_task_service, mocker):
        """Happy Path: Create task with valid data."""
        task_data = {"title": "Test Task", "priority": "high"}
        mock_response = TaskResponse(
            id="task-123",
            title="Test Task",
            priority=Priority.high,
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_service.create_task = mocker.AsyncMock(return_value=mock_response)

        response = client.post(
            "/api/v1/tasks",
            json=task_data,
            headers={"Idempotency-Key": "test-create-task-123"},
        )

        assert response.status_code == 201
        assert response.json()["id"] == "task-123"

    def test_create_task_boundary_values(self, mock_task_service, mocker):
        """Happy Path: Create task with max title length."""
        long_title = "A" * 200
        task_data = {"title": long_title, "priority": "low"}
        mock_response = TaskResponse(
            id="task-456",
            title=long_title,
            priority=Priority.low,
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_service.create_task = mocker.AsyncMock(return_value=mock_response)

        response = client.post(
            "/api/v1/tasks",
            json=task_data,
            headers={"Idempotency-Key": "test-create-task-boundary"},
        )

        assert response.status_code == 201
        assert response.json()["title"] == long_title


class TestTaskControllerRead:
    def test_get_tasks_success(self, mock_task_service, mocker):
        """Happy Path: Get all tasks."""
        mock_responses = [
            TaskResponse(
                id="task-1",
                title="Task 1",
                status=TaskStatus.pending,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            TaskResponse(
                id="task-2",
                title="Task 2",
                status=TaskStatus.completed,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]
        mock_task_service.get_tasks = mocker.AsyncMock(return_value=mock_responses)

        response = client.get("/api/v1/tasks")

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_task_success(self, mock_task_service, mocker):
        """Happy Path: Get single task."""
        mock_response = TaskResponse(
            id="task-123",
            title="Test Task",
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_service.get_task = mocker.AsyncMock(return_value=mock_response)

        response = client.get("/api/v1/tasks/task-123")

        assert response.status_code == 200
        assert response.json()["id"] == "task-123"

    def test_get_task_not_found(self, mock_task_service, mocker):
        """Failure Mode: Task not found."""
        mock_task_service.get_task = mocker.AsyncMock(return_value=None)

        response = client.get("/api/v1/tasks/nonexistent")

        assert response.status_code == 404


class TestTaskControllerUpdate:
    def test_update_task_success(self, mock_task_service, mocker):
        """Happy Path: Update task."""
        updated_response = TaskResponse(
            id="task-123",
            title="Updated",
            status=TaskStatus.in_progress,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_service.update_task = mocker.AsyncMock(return_value=updated_response)

        updates = {"status": "in_progress"}
        response = client.put(
            "/api/v1/tasks/task-123",
            json=updates,
            headers={"Idempotency-Key": "test-update-task-123"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_task_invalid_status(self, mock_task_service, mocker):
        """Failure Mode: Invalid status transition."""
        mock_task_service.update_task = mocker.AsyncMock(
            side_effect=ValueError("Cannot change status")
        )

        updates = {"status": "pending"}
        response = client.put(
            "/api/v1/tasks/task-123",
            json=updates,
            headers={"Idempotency-Key": "test-update-invalid-status"},
        )

        assert response.status_code == 400


class TestTaskControllerDelete:
    def test_delete_task_success(self, mock_task_service, mocker):
        """Happy Path: Delete task."""
        mock_task_service.delete_task = mocker.AsyncMock()

        response = client.delete(
            "/api/v1/tasks/task-123",
            headers={"Idempotency-Key": "test-delete-task-123"},
        )

        assert response.status_code == 204


# Error Handling and Auth
class TestTaskControllerErrors:
    def test_unauthorized_access(self, mocker):
        """Failure Mode: Missing auth (user_id)."""
        # Don't mock get_user_id for this test - let it use the real implementation
        # which will fail because there's no user_id in the request context
        response = client.get("/api/v1/tasks")

        assert response.status_code == 401


# Integration with Models
class TestTaskControllerModelIntegration:
    def test_full_crud_cycle(self, mock_task_service, mocker):
        """Happy Path: Simulate full CRUD cycle."""
        # Create
        task_data = {"title": "Cycle Task", "priority": "urgent"}
        created = TaskResponse(
            id="task-cycle",
            title="Cycle Task",
            priority=Priority.urgent,
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_service.create_task = mocker.AsyncMock(return_value=created)

        response = client.post(
            "/api/v1/tasks",
            json=task_data,
            headers={"Idempotency-Key": "test-crud-cycle-create"},
        )
        assert response.status_code == 201

        # Read
        mock_task_service.get_tasks = mocker.AsyncMock(return_value=[created])
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200

        # Update
        updated = TaskResponse(
            id="task-cycle",
            title="Updated Cycle",
            status=TaskStatus.in_progress,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_service.update_task = mocker.AsyncMock(return_value=updated)

        updates = {"status": "in_progress"}
        response = client.put(
            "/api/v1/tasks/task-cycle",
            json=updates,
            headers={"Idempotency-Key": "test-crud-cycle-update"},
        )
        assert response.status_code == 200

        # Delete
        mock_task_service.delete_task = mocker.AsyncMock()
        response = client.delete(
            "/api/v1/tasks/task-cycle",
            headers={"Idempotency-Key": "test-crud-cycle-delete"},
        )
        assert response.status_code == 204
