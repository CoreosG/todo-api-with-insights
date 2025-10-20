from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.models.task_models import (
    Priority,
    TaskCreate,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)
from src.repositories.task_repository import TaskRepository
from src.services.task_service import TaskService


# Fixture for mocked TaskRepository
@pytest.fixture
def mock_task_repo():
    return AsyncMock(spec=TaskRepository)


# Fixture for TaskService with mocked repository
@pytest.fixture
def task_service(mock_task_repo):
    return TaskService(task_repo=mock_task_repo)


# Happy Path Tests for Create
class TestTaskServiceCreate:
    @pytest.mark.asyncio
    async def test_create_task_success(self, task_service, mock_task_repo):
        """Happy Path: Create a task successfully."""
        task_create = TaskCreate(title="Test Task", priority=Priority.high)
        mock_response = TaskResponse(
            id="task-123",
            title="Test Task",
            priority=Priority.high,
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.create_task = AsyncMock(return_value=mock_response)

        response = await task_service.create_task("user-123", task_create)

        assert response.id == "task-123"
        assert response.title == "Test Task"
        mock_task_repo.create_task.assert_called_once_with("user-123", task_create)

    @pytest.mark.asyncio
    async def test_create_task_boundary_values(self, task_service, mock_task_repo):
        """Happy Path: Test boundary values (e.g., max title length)."""
        long_title = "A" * 200
        task_create = TaskCreate(title=long_title, priority=Priority.low)
        mock_response = TaskResponse(
            id="task-456",
            title=long_title,
            priority=Priority.low,
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.create_task = AsyncMock(return_value=mock_response)

        response = await task_service.create_task("user-456", task_create)

        assert response.title == long_title
        mock_task_repo.create_task.assert_called_once_with("user-456", task_create)


# Happy Path Tests for Read
class TestTaskServiceRead:
    @pytest.mark.asyncio
    async def test_get_task_success(self, task_service, mock_task_repo):
        """Happy Path: Retrieve a task."""
        mock_response = TaskResponse(
            id="task-123",
            title="Test Task",
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.get_task = AsyncMock(return_value=mock_response)

        response = await task_service.get_task("user-123", "task-123")

        assert response.id == "task-123"
        mock_task_repo.get_task.assert_called_once_with("user-123", "task-123")

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_service, mock_task_repo):
        """Failure Mode: Task not found."""
        mock_task_repo.get_task = AsyncMock(return_value=None)

        response = await task_service.get_task("user-123", "nonexistent")

        assert response is None
        mock_task_repo.get_task.assert_called_once_with("user-123", "nonexistent")

    @pytest.mark.asyncio
    async def test_get_tasks_success(self, task_service, mock_task_repo):
        """Happy Path: Retrieve all tasks."""
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
        mock_task_repo.get_tasks = AsyncMock(return_value=mock_responses)

        responses = await task_service.get_tasks("user-123")

        assert len(responses) == 2
        assert responses[0].id == "task-1"
        mock_task_repo.get_tasks.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_get_tasks_by_status_success(self, task_service, mock_task_repo):
        """Happy Path: Retrieve tasks by status."""
        mock_responses = [
            TaskResponse(
                id="task-1",
                title="Pending Task",
                status=TaskStatus.pending,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        mock_task_repo.get_tasks_by_status = AsyncMock(return_value=mock_responses)

        responses = await task_service.get_tasks_by_status(
            "user-123", TaskStatus.pending
        )

        assert len(responses) == 1
        assert responses[0].status == TaskStatus.pending
        mock_task_repo.get_tasks_by_status.assert_called_once_with(
            "user-123", TaskStatus.pending
        )


# Tests for Update (with Business Logic)
class TestTaskServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_task_success(self, task_service, mock_task_repo):
        """Happy Path: Update a task with valid status transition."""
        current_task = TaskResponse(
            id="task-123",
            title="Original",
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        updated_task = TaskResponse(
            id="task-123",
            title="Updated",
            status=TaskStatus.in_progress,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.get_task = AsyncMock(return_value=current_task)
        mock_task_repo.update_task = AsyncMock(return_value=updated_task)

        updates = TaskUpdate(status=TaskStatus.in_progress)
        response = await task_service.update_task("user-123", "task-123", updates)

        assert response.status == TaskStatus.in_progress
        assert response.title == "Updated"
        mock_task_repo.get_task.assert_called_once_with("user-123", "task-123")
        mock_task_repo.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_invalid_status_transition(
        self, task_service, mock_task_repo
    ):
        """Failure Mode: Cannot change status from completed."""
        current_task = TaskResponse(
            id="task-123",
            title="Completed Task",
            status=TaskStatus.completed,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.get_task = AsyncMock(return_value=current_task)

        updates = TaskUpdate(status=TaskStatus.pending)

        with pytest.raises(ValueError, match="Cannot change status from completed"):
            await task_service.update_task("user-123", "task-123", updates)

        mock_task_repo.get_task.assert_called_once_with("user-123", "task-123")
        mock_task_repo.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_no_status_change(self, task_service, mock_task_repo):
        """Happy Path: Update without status (no validation)."""
        current_task = TaskResponse(
            id="task-123",
            title="Original",
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        updated_task = TaskResponse(
            id="task-123",
            title="Updated Title",
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.get_task = AsyncMock(return_value=current_task)
        mock_task_repo.update_task = AsyncMock(return_value=updated_task)

        updates = TaskUpdate(title="Updated Title")
        response = await task_service.update_task("user-123", "task-123", updates)

        assert response.title == "Updated Title"
        mock_task_repo.update_task.assert_called_once()


# Tests for Delete
class TestTaskServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_service, mock_task_repo):
        """Happy Path: Delete a task."""
        mock_task_repo.delete_task = AsyncMock()

        await task_service.delete_task("user-123", "task-123")

        mock_task_repo.delete_task.assert_called_once_with("user-123", "task-123")


# Error Handling and Edge Cases
class TestTaskServiceErrors:
    @pytest.mark.asyncio
    async def test_create_task_repo_error(self, task_service, mock_task_repo):
        """Failure Mode: Repository error during create."""
        task_create = TaskCreate(title="Fail Task")
        mock_task_repo.create_task = AsyncMock(side_effect=Exception("DynamoDB Error"))

        with pytest.raises(Exception, match="DynamoDB Error"):
            await task_service.create_task("user-123", task_create)


# Integration with Models
class TestTaskServiceModelIntegration:
    @pytest.mark.asyncio
    async def test_full_crud_cycle(self, task_service, mock_task_repo):
        """Happy Path: Simulate full cycle with mocked responses."""
        # Create
        task_create = TaskCreate(title="Cycle Task", priority=Priority.urgent)
        created = TaskResponse(
            id="task-cycle",
            title="Cycle Task",
            priority=Priority.urgent,
            status=TaskStatus.pending,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.create_task = AsyncMock(return_value=created)

        response = await task_service.create_task("user-123", task_create)
        assert response.priority == Priority.urgent

        # Read
        mock_task_repo.get_task = AsyncMock(return_value=created)
        fetched = await task_service.get_task("user-123", "task-cycle")
        assert fetched.title == "Cycle Task"

        # Update
        updated = TaskResponse(
            id="task-cycle",
            title="Updated Cycle",
            status=TaskStatus.in_progress,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_repo.update_task = AsyncMock(return_value=updated)

        updates = TaskUpdate(status=TaskStatus.in_progress)
        updated_response = await task_service.update_task(
            "user-123", "task-cycle", updates
        )
        assert updated_response.status == TaskStatus.in_progress

        # Delete
        mock_task_repo.delete_task = AsyncMock()
        await task_service.delete_task("user-123", "task-cycle")
        mock_task_repo.delete_task.assert_called_once_with("user-123", "task-cycle")
