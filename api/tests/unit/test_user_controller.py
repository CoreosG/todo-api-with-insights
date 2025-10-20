from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.user_models import UserResponse

client = TestClient(app)


# Mock Services for testing
@pytest.fixture
def mock_user_service(mocker):
    mock_service = mocker.Mock()
    # Mock the create_or_get_user method as AsyncMock
    mock_service.create_or_get_user = mocker.AsyncMock(
        return_value=Mock(
            id="test-user-123", email="test@example.com", name="Test User"
        )
    )
    mocker.patch(
        "src.utils.dependency_injection.get_user_service", return_value=mock_service
    )
    mocker.patch(
        "src.controllers.user_controller.get_user_context",
        return_value=Mock(
            user_id="test-user-123", email="test@example.com", name="Test User"
        ),
    )

    # Mock the user repository to avoid DynamoDB calls
    mock_user_repo = mocker.Mock()
    mock_user_repo.get_user = mocker.AsyncMock(
        return_value=None
    )  # No user exists initially
    mock_user_repo.create_user = mocker.AsyncMock(
        return_value=Mock(
            id="test-user-123", email="test@example.com", name="Test User"
        )
    )
    mock_user_repo.update_user = mocker.AsyncMock(
        return_value=Mock(
            id="test-user-123", email="test@example.com", name="Test User"
        )
    )
    mock_user_repo.delete_user = mocker.AsyncMock()
    mocker.patch("src.utils.dependency_injection.user_repo", mock_user_repo)
    return mock_service


# Happy Path Tests
class TestUserControllerCreate:
    def test_create_user_success(self, mock_user_service, mocker):
        """Happy Path: Create user explicitly."""
        user_data = {"email": "test@example.com", "name": "Test User"}
        mock_response = UserResponse(
            id="user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.create_user = mocker.AsyncMock(return_value=mock_response)

        response = client.post("/api/v1/users", json=user_data, headers={"Idempotency-Key": "test-create-user-123"})

        assert response.status_code == 201
        assert response.json()["email"] == "test@example.com"


class TestUserControllerRead:
    def test_get_user_success(self, mock_user_service, mocker):
        """Happy Path: Get user."""
        mock_response = UserResponse(
            id="user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.get_user = mocker.AsyncMock(return_value=mock_response)

        response = client.get("/api/v1/users")

        assert response.status_code == 200
        assert response.json()["id"] == "user-123"

    def test_get_user_not_found(self, mock_user_service, mocker):
        """Failure Mode: User not found."""
        mock_user_service.get_user = mocker.AsyncMock(return_value=None)

        response = client.get("/api/v1/users/nonexistent")

        assert response.status_code == 404


class TestUserControllerUpdate:
    def test_update_user_success(self, mock_user_service, mocker):
        """Happy Path: Update user."""
        mock_response = UserResponse(
            id="user-123",
            email="updated@example.com",
            name="Updated User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.update_user = mocker.AsyncMock(return_value=mock_response)

        updates = {"email": "updated@example.com", "name": "Updated User"}
        response = client.put("/api/v1/users", json=updates, headers={"Idempotency-Key": "test-update-user-123"})

        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_update_user_invalid_email(self, mock_user_service, mocker):
        """Failure Mode: Invalid email format."""
        mock_user_service.update_user = mocker.AsyncMock(
            side_effect=ValueError("Invalid email")
        )

        updates = {"email": "invalid-email"}
        response = client.put("/api/v1/users", json=updates, headers={"Idempotency-Key": "test-update-invalid-email"})

        assert response.status_code == 422


class TestUserControllerDelete:
    def test_delete_user_success(self, mock_user_service, mocker):
        """Happy Path: Delete user."""
        mock_user_service.delete_user = mocker.AsyncMock()

        response = client.delete("/api/v1/users", headers={"Idempotency-Key": "test-delete-user-123"})

        assert response.status_code == 204


# Error Handling and Auth
class TestUserControllerErrors:
    def test_unauthorized_access(self, mocker):
        """Failure Mode: Missing auth (user_id)."""
        # Don't mock get_user_id for this test - let it use the real implementation
        # which will fail because there's no user_id in the request context
        response = client.get("/api/v1/users")

        assert response.status_code == 401


# Integration with Models
class TestUserControllerModelIntegration:
    def test_full_crud_cycle(self, mock_user_service, mocker):
        """Happy Path: Simulate full CRUD cycle."""
        # Create
        user_data = {"email": "cycle@example.com", "name": "Cycle User"}
        created = UserResponse(
            id="user-cycle",
            email="cycle@example.com",
            name="Cycle User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.create_user = mocker.AsyncMock(return_value=created)

        response = client.post("/api/v1/users", json=user_data, headers={"Idempotency-Key": "test-crud-cycle-create"})
        assert response.status_code == 201

        # Read
        mock_user_service.get_user = mocker.AsyncMock(return_value=created)
        response = client.get("/api/v1/users")
        assert response.status_code == 200

        # Update
        updated = UserResponse(
            id="user-cycle",
            email="updated@example.com",
            name="Updated Cycle",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.update_user = mocker.AsyncMock(return_value=updated)

        updates = {"email": "updated@example.com"}
        response = client.put("/api/v1/users", json=updates, headers={"Idempotency-Key": "test-crud-cycle-update"})
        assert response.status_code == 200

        # Delete
        mock_user_service.delete_user = mocker.AsyncMock()
        response = client.delete("/api/v1/users", headers={"Idempotency-Key": "test-crud-cycle-delete"})
        assert response.status_code == 204
