from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.models.user_models import UserCreate, UserResponse, UserUpdate
from src.repositories.user_repository import UserRepository
from src.services.user_service import UserService


# Fixture for mocked UserRepository
@pytest.fixture
def mock_user_repo():
    return AsyncMock(spec=UserRepository)


# Fixture for UserService with mocked repository
@pytest.fixture
def user_service(mock_user_repo):
    return UserService(user_repo=mock_user_repo)


# Tests for CreateOrGet (Auto-Creation from API Gateway Params)
class TestUserServiceCreateOrGet:
    @pytest.mark.asyncio
    async def test_create_or_get_user_new(self, user_service, mock_user_repo):
        """Happy Path: Auto-create user from API Gateway params if not exists."""
        mock_user_repo.get_user = AsyncMock(return_value=None)
        mock_response = UserResponse(
            id="user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.create_user = AsyncMock(return_value=mock_response)

        response = await user_service.create_or_get_user(
            "user-123", "test@example.com", "Test User"
        )

        assert response.id == "user-123"
        assert response.email == "test@example.com"
        mock_user_repo.get_user.assert_called_once_with("user-123")
        mock_user_repo.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_or_get_user_existing(self, user_service, mock_user_repo):
        """Happy Path: Return existing user without creating."""
        existing = UserResponse(
            id="user-123",
            email="existing@example.com",
            name="Existing User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.get_user = AsyncMock(return_value=existing)

        response = await user_service.create_or_get_user(
            "user-123", "test@example.com", "Test User"
        )

        assert response.id == "user-123"
        assert response.name == "Existing User"
        mock_user_repo.get_user.assert_called_once_with("user-123")
        mock_user_repo.create_user.assert_not_called()


# Tests for Explicit Create
class TestUserServiceCreate:
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo):
        """Happy Path: Explicit create with full user data."""
        user_create = UserCreate(email="create@example.com", name="Create User")
        mock_response = UserResponse(
            id="user-456",
            email="create@example.com",
            name="Create User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.get_user = AsyncMock(return_value=None)
        mock_user_repo.create_user = AsyncMock(return_value=mock_response)

        response = await user_service.create_user("user-456", user_create)

        assert response.id == "user-456"
        mock_user_repo.get_user.assert_called_once_with("user-456")
        mock_user_repo.create_user.assert_called_once_with("user-456", user_create)

    @pytest.mark.asyncio
    async def test_create_user_duplicate(self, user_service, mock_user_repo):
        """Failure Mode: Raise error for duplicate user."""
        existing = UserResponse(
            id="user-456",
            email="existing@example.com",
            name="Existing",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.get_user = AsyncMock(return_value=existing)

        user_create = UserCreate(email="new@example.com", name="New User")

        with pytest.raises(ValueError, match="User with ID user-456 already exists"):
            await user_service.create_user("user-456", user_create)

        mock_user_repo.get_user.assert_called_once_with("user-456")
        mock_user_repo.create_user.assert_not_called()


# Tests for Read
class TestUserServiceRead:
    @pytest.mark.asyncio
    async def test_get_user_success(self, user_service, mock_user_repo):
        """Happy Path: Retrieve a user."""
        mock_response = UserResponse(
            id="user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.get_user = AsyncMock(return_value=mock_response)

        response = await user_service.get_user("user-123")

        assert response.id == "user-123"
        mock_user_repo.get_user.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_service, mock_user_repo):
        """Failure Mode: User not found."""
        mock_user_repo.get_user = AsyncMock(return_value=None)

        response = await user_service.get_user("nonexistent")

        assert response is None
        mock_user_repo.get_user.assert_called_once_with("nonexistent")


# Tests for Update
class TestUserServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user_repo):
        """Happy Path: Update user with valid email."""
        mock_response = UserResponse(
            id="user-123",
            email="updated@example.com",
            name="Updated User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.update_user = AsyncMock(return_value=mock_response)

        updates = UserUpdate(email="updated@example.com", name="Updated User")
        response = await user_service.update_user("user-123", updates)

        assert response.email == "updated@example.com"
        mock_user_repo.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_invalid_email(self, user_service, mock_user_repo):
        """Failure Mode: Pydantic model rejects invalid email format."""
        # Test that UserUpdate model itself validates email format
        with pytest.raises(Exception) as exc_info:
            UserUpdate(email="invalid-email")

        # Verify it's a Pydantic validation error
        assert "value is not a valid email address" in str(exc_info.value)

        # Since Pydantic rejects it, the service method won't even be called
        # This validates that invalid emails are caught at the model level


# Tests for Delete
class TestUserServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_user_repo):
        """Happy Path: Delete a user."""
        mock_user_repo.delete_user = AsyncMock()

        await user_service.delete_user("user-123")

        mock_user_repo.delete_user.assert_called_once_with("user-123")


# Error Handling and Edge Cases
class TestUserServiceErrors:
    @pytest.mark.asyncio
    async def test_create_or_get_user_repo_error(self, user_service, mock_user_repo):
        """Failure Mode: Repository error during auto-create."""
        mock_user_repo.get_user = AsyncMock(return_value=None)
        mock_user_repo.create_user = AsyncMock(side_effect=Exception("DynamoDB Error"))

        with pytest.raises(Exception, match="DynamoDB Error"):
            await user_service.create_or_get_user(
                "user-123", "test@example.com", "Test User"
            )


# Integration with Models
class TestUserServiceModelIntegration:
    @pytest.mark.asyncio
    async def test_workflow_simulation(self, user_service, mock_user_repo):
        """Happy Path: Simulate API Gateway workflow (auto-create on first request)."""
        # First request: Auto-create
        mock_user_repo.get_user = AsyncMock(return_value=None)
        created = UserResponse(
            id="user-123",
            email="workflow@example.com",
            name="Workflow User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.create_user = AsyncMock(return_value=created)

        response = await user_service.create_or_get_user(
            "user-123", "workflow@example.com", "Workflow User"
        )
        assert response.email == "workflow@example.com"

        # Subsequent request: Return existing
        mock_user_repo.get_user = AsyncMock(return_value=created)
        response = await user_service.create_or_get_user(
            "user-123", "workflow@example.com", "Workflow User"
        )
        assert response.id == "user-123"
        mock_user_repo.create_user.assert_called_once()  # Only called once
