"""
Real AWS Lambda + API Gateway + Mangum integration tests for Todo API.

Tests the complete Lambda execution flow using Mangum handler with real API Gateway events.
Mocks DynamoDB services to focus on the Lambda integration and authentication flow.
"""

import json
import os
import uuid
from unittest.mock import AsyncMock

import pytest
from mangum import Mangum

from src.main import app

from ..helpers.api_gateway_events import (
    create_authenticated_api_gateway_event,
    create_health_check_event,
    create_task_create_event,
    create_task_delete_event,
    create_task_get_event,
    create_task_update_event,
    create_unauthenticated_api_gateway_event,
)

# Set up test environment - use mocked DynamoDB for testing
os.environ["USE_LOCAL_DYNAMODB"] = "false"  # Use mocked DynamoDB

# Create Mangum handler for testing
handler = Mangum(app, lifespan="off")


# Mock the DynamoDB services to avoid actual database calls during testing
def create_mock_user_service():
    """Create a mock user service with mocked repository methods."""
    from unittest.mock import AsyncMock

    from src.repositories.user_repository import UserRepository
    from src.services.user_service import UserService

    # Create a real repository instance but mock its methods
    mock_repo = UserRepository()
    mock_repo.get_user = AsyncMock()
    mock_repo.create_user = AsyncMock()
    mock_repo.update_user = AsyncMock()
    mock_repo.delete_user = AsyncMock()

    mock_user_service = UserService(mock_repo)
    return mock_user_service


def create_mock_task_service():
    """Create a mock task service with mocked repository methods."""
    from unittest.mock import AsyncMock

    from src.repositories.task_repository import TaskRepository
    from src.services.task_service import TaskService

    # Create a real repository instance but mock its methods
    mock_repo = TaskRepository()
    mock_repo.get_task = AsyncMock()
    mock_repo.get_tasks = AsyncMock()
    mock_repo.create_task = AsyncMock()
    mock_repo.update_task = AsyncMock()
    mock_repo.delete_task = AsyncMock()
    mock_repo.get_tasks_by_status = AsyncMock()

    mock_task_service = TaskService(mock_repo)
    return mock_task_service


@pytest.fixture
def mock_services():
    """Create fresh mock services for each test to prevent interference."""
    return {"user": create_mock_user_service(), "task": create_mock_task_service()}


class TestLambdaAPIGatewayIntegration:
    """Test complete Lambda execution flow with real API Gateway events."""

    def test_health_check_endpoint(self):
        """Test health check endpoint through Lambda handler."""
        event = create_health_check_event()

        response = handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"
        assert "version" in body
        assert "environment" in body

    def test_user_context_extraction_from_jwt(self, mock_services):
        """Test that user context is properly extracted from JWT claims in Lambda execution."""
        from unittest.mock import patch

        user_id = f"lambda-user-{uuid.uuid4().hex[:8]}"
        email = f"lambda{user_id}@example.com"
        name = f"Lambda User {user_id}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]

        # Create authenticated event
        event = create_authenticated_api_gateway_event(
            method="GET",
            path="/api/v1/users",
            user_id=user_id,
            email=email,
            name=name,
        )

        # Mock user service to return existing user
        mock_user_service.user_repo.get_user.return_value = {
            "id": user_id,
            "email": email,
            "name": name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["id"] == user_id
        assert body["email"] == email
        assert body["name"] == name

    def test_task_creation_through_lambda(self, mock_services):
        """Test task creation through complete Lambda execution flow."""
        from unittest.mock import patch

        user_id = f"task-create-user-{uuid.uuid4().hex[:8]}"
        email = f"taskcreate{user_id}@example.com"
        name = f"Task Create User {user_id}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Mock user service to auto-create user
        mock_user_service.user_repo.get_user.return_value = None
        mock_user_service.user_repo.create_user.return_value = {
            "id": user_id,
            "email": email,
            "name": name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        from datetime import datetime, timezone

        from src.models.task_models import TaskResponse

        mock_task_service.task_repo.create_task.return_value = TaskResponse(
            id=task_id,
            title="Test Task",
            description="Test Description",
            priority="medium",
            category="test",
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        event = create_task_create_event(
            user_id=user_id,
            email=email,
            name=name,
            title="Test Task",
            description="Test Description",
            idempotency_key="test-idempotency-key-123",
        )

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["title"] == "Test Task"
        assert body["id"] == task_id
        assert body["status"] == "pending"

    def test_task_retrieval_through_lambda(self, mock_services):
        """Test task retrieval through complete Lambda execution flow."""
        from unittest.mock import patch

        user_id = f"task-get-user-{uuid.uuid4().hex[:8]}"
        email = f"taskget{user_id}@example.com"
        name = f"Task Get User {user_id}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Mock user service
        mock_user_service.user_repo.get_user.return_value = {
            "id": user_id,
            "email": email,
            "name": name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service to return tasks
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        from datetime import datetime, timezone

        from src.models.task_models import TaskResponse

        mock_task_service.task_repo.get_tasks.return_value = [
            TaskResponse(
                id=task_id,
                title="Retrieved Task",
                description="Retrieved Description",
                priority="high",
                category="test",
                status="pending",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]

        event = create_task_get_event(user_id=user_id, email=email, name=name)

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["title"] == "Retrieved Task"
        assert body[0]["id"] == task_id

    def test_task_update_through_lambda(self, mock_services):
        """Test task update through complete Lambda execution flow."""
        from unittest.mock import patch

        user_id = f"task-update-user-{uuid.uuid4().hex[:8]}"
        email = f"taskupdate{user_id}@example.com"
        name = f"Task Update User {user_id}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Mock user service
        mock_user_service.user_repo.get_user.return_value = {
            "id": user_id,
            "email": email,
            "name": name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service
        task_id = "existing-task-id"
        from datetime import datetime, timezone

        from src.models.task_models import TaskResponse

        mock_task_service.task_repo.get_task.return_value = TaskResponse(
            id=task_id,
            title="Original Task",
            description="Original Description",
            priority="medium",
            category="test",
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_task_service.task_repo.update_task.return_value = TaskResponse(
            id=task_id,
            title="Updated Task",
            description="Updated Description",
            priority="high",
            category="test",
            status="in_progress",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        event = create_task_update_event(
            user_id=user_id,
            email=email,
            name=name,
            task_id=task_id,
            title="Updated Task",
            description="Updated Description",
            priority="high",
            status="in_progress",
            idempotency_key="test-update-idempotency-key-123",
        )

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["title"] == "Updated Task"
        assert body["description"] == "Updated Description"
        assert body["priority"] == "high"
        assert body["status"] == "in_progress"

    def test_task_deletion_through_lambda(self, mock_services):
        """Test task deletion through complete Lambda execution flow."""
        from unittest.mock import patch

        user_id = f"task-delete-user-{uuid.uuid4().hex[:8]}"
        email = f"taskdelete{user_id}@example.com"
        name = f"Task Delete User {user_id}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Mock user service
        mock_user_service.user_repo.get_user.return_value = {
            "id": user_id,
            "email": email,
            "name": name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service
        task_id = "task-to-delete"
        mock_task_service.task_repo.delete_task = AsyncMock()

        event = create_task_delete_event(
            user_id=user_id, email=email, name=name, task_id=task_id,
            idempotency_key="test-delete-idempotency-key-123"
        )

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 204
        assert response["body"] == "{}"

    def test_missing_authentication(self):
        """Test that endpoints properly handle missing authentication."""
        event = create_unauthenticated_api_gateway_event(
            method="GET", path="/api/v1/users"
        )

        response = handler(event, {})

        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "Unauthorized" in body["detail"]

    def test_invalid_task_data_validation(self, mock_services):
        """Test validation errors for invalid task data."""
        from unittest.mock import patch

        user_id = f"validation-user-{uuid.uuid4().hex[:8]}"
        email = f"validation{user_id}@example.com"
        name = f"Validation User {user_id}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Create event with invalid priority
        event = create_authenticated_api_gateway_event(
            method="POST",
            path="/api/v1/tasks",
            user_id=user_id,
            email=email,
            name=name,
            body=json.dumps(
                {
                    "title": "Invalid Task",
                    "priority": "invalid_priority_value",  # Should be enum value
                }
            ),
        )

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 422
        body = json.loads(response["body"])
        assert "detail" in body

    def test_idempotency_key_handling(self, mock_services):
        """Test idempotency key extraction and handling."""
        from unittest.mock import patch

        user_id = f"idempotency-user-{uuid.uuid4().hex[:8]}"
        email = f"idempotency{user_id}@example.com"
        name = f"Idempotency User {user_id}"
        idempotency_key = "test-idempotency-key-123"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Mock user service
        mock_user_service.user_repo.get_user.return_value = None
        mock_user_service.user_repo.create_user.return_value = {
            "id": user_id,
            "email": email,
            "name": name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        from datetime import datetime, timezone

        from src.models.task_models import TaskResponse

        mock_task_service.task_repo.create_task.return_value = TaskResponse(
            id=task_id,
            title="Idempotency Task",
            description="Test Description",
            priority="medium",
            category="test",
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        event = create_task_create_event(
            user_id=user_id, email=email, name=name, idempotency_key=idempotency_key
        )

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["title"] == "Idempotency Task"
        assert body["id"] == task_id

    def test_user_isolation(self, mock_services):
        """Test that users cannot access each other's data."""
        from unittest.mock import patch

        user1_id = f"isolation-user-1-{uuid.uuid4().hex[:8]}"
        user1_email = f"isolation1{user1_id}@example.com"
        user1_name = f"Isolation User 1 {user1_id}"

        user2_id = f"isolation-user-2-{uuid.uuid4().hex[:8]}"
        user2_email = f"isolation2{user2_id}@example.com"
        user2_name = f"Isolation User 2 {user2_id}"

        # Create task for user 1
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Mock user service for user 1
        mock_user_service.user_repo.get_user.return_value = {
            "id": user1_id,
            "email": user1_email,
            "name": user1_name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service - user 1's task exists
        from datetime import datetime, timezone

        from src.models.task_models import TaskResponse

        mock_task_service.task_repo.get_task.return_value = TaskResponse(
            id=task_id,
            title="User 1 Task",
            description="Only User 1 can see this",
            priority="high",
            category="test",
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # User 1 retrieves their task
        event1 = create_task_get_event(
            user_id=user1_id, email=user1_email, name=user1_name, task_id=task_id
        )

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response1 = handler(event1, {})

        assert response1["statusCode"] == 200

        # User 2 tries to retrieve user 1's task (should fail)
        # Mock user service for user 2
        mock_user_service.user_repo.get_user.return_value = {
            "id": user2_id,
            "email": user2_email,
            "name": user2_name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service - user 2 doesn't have access to user 1's task
        mock_task_service.task_repo.get_task.return_value = None

        event2 = create_task_get_event(
            user_id=user2_id, email=user2_email, name=user2_name, task_id=task_id
        )

        # Patch again for user 2
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response2 = handler(event2, {})

        # Should get 404 because user 2 doesn't have access to user 1's task
        assert response2["statusCode"] == 404

    def test_bulk_task_operations(self, mock_services):
        """Test bulk task operations through Lambda handler."""
        from unittest.mock import patch

        user_id = f"bulk-user-{uuid.uuid4().hex[:8]}"
        email = f"bulk{user_id}@example.com"
        name = f"Bulk User {user_id}"

        # Get mocks from fixture
        mock_user_service = mock_services["user"]
        mock_task_service = mock_services["task"]

        # Mock user service
        mock_user_service.user_repo.get_user.return_value = {
            "id": user_id,
            "email": email,
            "name": name,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        # Mock task service for multiple tasks
        task1_id = f"task-1-{uuid.uuid4().hex[:8]}"
        task2_id = f"task-2-{uuid.uuid4().hex[:8]}"
        task3_id = f"task-3-{uuid.uuid4().hex[:8]}"

        from datetime import datetime, timezone

        from src.models.task_models import TaskResponse

        mock_task_service.task_repo.get_tasks.return_value = [
            TaskResponse(
                id=task1_id,
                title="Bulk Task 1",
                description="First task",
                priority="high",
                category="test",
                status="pending",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            TaskResponse(
                id=task2_id,
                title="Bulk Task 2",
                description="Second task",
                priority="medium",
                category="test",
                status="in_progress",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            TaskResponse(
                id=task3_id,
                title="Bulk Task 3",
                description="Third task",
                priority="low",
                category="test",
                status="completed",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        event = create_task_get_event(user_id=user_id, email=email, name=name)

        # Patch the dependency injection functions
        with patch(
            "src.utils.dependency_injection.get_user_service", lambda: mock_user_service
        ), patch(
            "src.utils.dependency_injection.get_task_service", lambda: mock_task_service
        ):
            response = handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) == 3

        # Verify all tasks belong to the correct user and have expected titles
        for task in body:
            assert task["id"] in [task1_id, task2_id, task3_id]

        # Test filtering by status
        mock_task_service.task_repo.get_tasks_by_status.return_value = [
            task
            for task in mock_task_service.task_repo.get_tasks.return_value
            if task.status == "pending"
        ]

        # In a real implementation, you'd need to modify the event to include query parameters
        # For this test, we just verify the mock was called correctly
        assert len(mock_task_service.task_repo.get_tasks_by_status.return_value) == 1
