from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from src.models.task_models import (
    Priority,
    TaskBase,
    TaskCreate,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)


# Test Enums (TaskStatus and Priority) - Happy Path and Boundary
class TestTaskStatus:
    def test_task_status_enum_values(self) -> None:
        """Happy Path: Verify all enum values are correct."""
        assert TaskStatus.pending == "pending"
        assert TaskStatus.in_progress == "in_progress"
        assert TaskStatus.completed == "completed"
        assert TaskStatus.cancelled == "cancelled"
        assert len(list(TaskStatus)) == 4

    def test_task_status_enum_str(self) -> None:
        """Happy Path: Ensure string representation works."""
        # Fixed: Use .value to get the enum's string value
        assert TaskStatus.pending.value == "pending"
        assert repr(TaskStatus.completed) == "<TaskStatus.completed: 'completed'>"


class TestPriority:
    def test_priority_enum_values(self) -> None:
        """Happy Path: Verify all enum values are correct."""
        assert Priority.low == "low"
        assert Priority.medium == "medium"
        assert Priority.high == "high"
        assert Priority.urgent == "urgent"
        assert len(list(Priority)) == 4

    def test_priority_enum_str(self) -> None:
        """Happy Path: Ensure string representation works."""
        # Fixed: Use .value to get the enum's string value
        assert Priority.medium.value == "medium"
        assert repr(Priority.urgent) == "<Priority.urgent: 'urgent'>"


# Test TaskBase Model
class TestTaskBase:
    def test_task_base_valid_creation(self) -> None:
        """Happy Path: Create with typical valid data."""
        task = TaskBase(
            title="Sample Task",
            description="A description",
            priority=Priority.medium,
            category="work",
            due_date=date(2023, 10, 1),
        )
        assert task.title == "Sample Task"
        assert task.description == "A description"
        assert task.priority == Priority.medium
        assert task.category == "work"
        assert task.due_date == date(2023, 10, 1)

    def test_task_base_boundary_values(self) -> None:
        """Happy Path: Test boundary values (e.g., min/max lengths)."""
        # Min length for title
        task = TaskBase(
            title="A",
            description=None,
            priority=Priority.low,
            category=None,
            due_date=None,
        )
        assert task.title == "A"
        # Max length for title (200 chars)
        long_title = "A" * 200
        task = TaskBase(
            title=long_title,
            description=None,
            priority=Priority.low,
            category=None,
            due_date=None,
        )
        assert task.title == long_title
        # Max length for description (1000 chars)
        long_desc = "B" * 1000
        task = TaskBase(
            title="Test",
            description=long_desc,
            priority=Priority.low,
            category=None,
            due_date=None,
        )
        assert task.description == long_desc

    def test_task_base_invalid_title(self) -> None:
        """Failure Mode: Invalid title (too short or too long)."""
        with pytest.raises(ValidationError):
            TaskBase(
                title="",
                description=None,
                priority=Priority.low,
                category=None,
                due_date=None,
            )  # Too short
        with pytest.raises(ValidationError):
            TaskBase(
                title="A" * 201,
                description=None,
                priority=Priority.low,
                category=None,
                due_date=None,
            )  # Too long

    def test_task_base_invalid_description(self) -> None:
        """Failure Mode: Invalid description (too long)."""
        with pytest.raises(ValidationError):
            TaskBase(
                title="Test",
                description="A" * 1001,
                priority=Priority.low,
                category=None,
                due_date=None,
            )  # Exceeds max length

    def test_task_base_invalid_priority(self) -> None:
        """Failure Mode: Invalid priority enum value."""
        with pytest.raises(ValidationError):
            TaskBase(
                title="Test",
                description=None,
                priority="invalid",  # type: ignore[arg-type]
                category=None,
                due_date=None,
            )

    def test_task_base_invalid_category(self) -> None:
        """Failure Mode: Invalid category (too long)."""
        with pytest.raises(ValidationError):
            TaskBase(
                title="Test",
                description=None,
                priority=Priority.low,
                category="A" * 51,
                due_date=None,
            )

    def test_task_base_optional_fields(self) -> None:
        """Happy Path: Optional fields can be None."""
        task = TaskBase(
            title="Test",
            description=None,
            priority=Priority.low,
            category=None,
            due_date=None,
        )
        assert task.description is None
        assert task.category is None
        assert task.due_date is None


# Test TaskCreate Model (inherits from TaskBase)
class TestTaskCreate:
    def test_task_create_valid(self) -> None:
        """Happy Path: Create with valid data."""
        task = TaskCreate(
            title="New Task",
            description="Description",
            priority=Priority.high,
            category="urgent",
            due_date=date(2023, 12, 1),
        )
        assert task.title == "New Task"
        assert task.priority == Priority.high

    def test_task_create_inherits_validation(self) -> None:
        """Happy Path: Inherits boundary and failure tests from TaskBase."""
        # Valid boundary
        task = TaskCreate(
            title="A",
            description="B" * 1000,
            priority=Priority.low,
            category=None,
            due_date=None,
        )
        assert task.title == "A"
        # Invalid (raises ValidationError)
        with pytest.raises(ValidationError):
            TaskCreate(
                title="",
                description=None,
                priority=Priority.low,
                category=None,
                due_date=None,
            )


# Test TaskResponse Model
class TestTaskResponse:
    def test_task_response_valid_creation(self, mocker) -> None:
        """Happy Path: Create with valid data, mocking timestamps."""
        mock_now = datetime(2023, 10, 1, 12, 0, 0)
        mocker.patch("src.models.task_models.datetime", utcnow=lambda: mock_now)
        task = TaskResponse(
            id="task-123",
            title="Response Task",
            description="Description",
            priority=Priority.low,
            category="test",
            due_date=date(2023, 11, 1),
            status=TaskStatus.pending,
            created_at=mock_now,
            updated_at=mock_now,
            completed_at=None,
        )
        assert task.id == "task-123"
        assert task.status == TaskStatus.pending
        assert task.created_at == mock_now

    def test_task_response_boundary_values(self, mocker) -> None:
        """Happy Path: Test boundary values for fields."""
        mock_now = datetime(2023, 10, 1)
        mocker.patch("src.models.task_models.datetime", utcnow=lambda: mock_now)
        # Long title
        long_title = "A" * 200
        task = TaskResponse(
            id="task-456",
            title=long_title,
            description=None,
            priority=Priority.medium,
            category=None,
            due_date=None,
            status=TaskStatus.completed,
            created_at=mock_now,
            updated_at=mock_now,
            completed_at=mock_now,
        )
        assert task.title == long_title
        assert task.status == TaskStatus.completed

    def test_task_response_invalid_status(self) -> None:
        """Failure Mode: Invalid status enum."""
        with pytest.raises(ValidationError):
            TaskResponse(
                id="task-123",
                title="Test",
                description=None,
                priority=Priority.low,
                category=None,
                due_date=None,
                status="invalid",  # type: ignore[arg-type]
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=None,
            )

    def test_task_response_missing_required_fields(self) -> None:
        """Failure Mode: Missing required fields (e.g., created_at, updated_at)."""
        with pytest.raises(ValidationError):
            TaskResponse(
                id="task-123",
                title="Test",
                description=None,
                priority=Priority.low,
                category=None,
                due_date=None,
                status=TaskStatus.pending,
                # Intentionally missing created_at, updated_at, completed_at
            )

    def test_task_response_completed_at_optional(self, mocker) -> None:
        """Happy Path: completed_at can be None."""
        mock_now = datetime(2023, 10, 1)
        mocker.patch("src.models.task_models.datetime", utcnow=lambda: mock_now)
        task = TaskResponse(
            id="task-123",
            title="Test",
            description=None,
            priority=Priority.low,
            category=None,
            due_date=None,
            status=TaskStatus.pending,
            created_at=mock_now,
            updated_at=mock_now,
            completed_at=None,
        )
        assert task.completed_at is None


# Test TaskUpdate Model
class TestTaskUpdate:
    def test_task_update_valid_partial(self) -> None:
        """Happy Path: Partial update with valid data."""
        update = TaskUpdate(
            title="Updated Title",
            description=None,
            status=TaskStatus.in_progress,
            priority=None,
            category=None,
            due_date=None,
        )
        assert update.title == "Updated Title"
        assert update.status == TaskStatus.in_progress
        assert update.description is None

    def test_task_update_boundary_values(self) -> None:
        """Happy Path: Test boundary values for update fields."""
        # Max title length
        long_title = "A" * 200
        update = TaskUpdate(
            title=long_title,
            description=None,
            status=None,
            priority=None,
            category=None,
            due_date=None,
        )
        assert update.title == long_title
        # Max description length
        long_desc = "B" * 1000
        update = TaskUpdate(
            title=None,
            description=long_desc,
            status=None,
            priority=None,
            category=None,
            due_date=None,
        )
        assert update.description == long_desc

    def test_task_update_invalid_title(self) -> None:
        """Failure Mode: Invalid title in update."""
        with pytest.raises(ValidationError):
            TaskUpdate(
                title="",
                description=None,
                status=None,
                priority=None,
                category=None,
                due_date=None,
            )

    def test_task_update_invalid_description(self) -> None:
        """Failure Mode: Invalid description in update."""
        with pytest.raises(ValidationError):
            TaskUpdate(
                title=None,
                description="A" * 1001,
                status=None,
                priority=None,
                category=None,
                due_date=None,
            )

    def test_task_update_invalid_status(self) -> None:
        """Failure Mode: Invalid status in update."""
        with pytest.raises(ValidationError):
            TaskUpdate(
                title=None,
                description=None,
                status="invalid",  # type: ignore[arg-type]
                priority=None,
                category=None,
                due_date=None,
            )

    def test_task_update_all_optional(self) -> None:
        """Happy Path: All fields can be None for partial updates."""
        update = TaskUpdate()  # No arguments
        assert update.title is None
        assert update.status is None

    def test_task_update_extra_fields_forbidden(self) -> None:
        """Failure Mode: Extra fields not in model raise error."""
        # Valid partial update
        update = TaskUpdate(title="Test")
        assert update.title == "Test"
        # Invalid with extra field
        with pytest.raises(ValidationError):
            TaskUpdate(
                title="Test",
                extra_field="not allowed",  # type: ignore[call-arg]
            )


# Integration Test for Serialization
class TestModelSerialization:
    def test_task_create_dict_serialization(self) -> None:
        """Happy Path: Ensure dict() works for serialization."""
        task = TaskCreate(
            title="Serialize Test",
            description=None,
            priority=Priority.urgent,
            category=None,
            due_date=None,
        )
        data = task.model_dump()
        assert data["title"] == "Serialize Test"
        assert data["priority"] == "urgent"

    def test_task_response_json_serialization(self, mocker) -> None:
        """Happy Path: JSON serialization for API responses."""
        mock_now = datetime(2023, 10, 1, tzinfo=UTC)
        mocker.patch("src.models.task_models.datetime", **{"now": lambda tz: mock_now})
        task = TaskResponse(
            id="task-json",
            title="JSON Test",
            description=None,
            priority=Priority.low,
            category=None,
            due_date=None,
            status=TaskStatus.completed,
            created_at=mock_now,
            updated_at=mock_now,
            completed_at=mock_now,
        )
        json_data = task.model_dump_json()
        assert '"id":"task-json"' in json_data
        assert '"status":"completed"' in json_data
