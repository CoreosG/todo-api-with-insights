import pytest
from botocore.exceptions import ClientError

from src.models.user_models import UserCreate, UserResponse


# Happy Path Tests for CRUD Operations
class TestUserRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_repositories):
        """Happy Path: Create a user and verify DynamoDB item + response."""
        user_repo = mock_repositories["user_repo"]
        user_create = UserCreate(email="test@example.com", name="Test User")
        response = await user_repo.create_user("cognito-user-123", user_create)
        assert isinstance(response, UserResponse)
        assert response.email == "test@example.com"
        assert response.id == "cognito-user-123"
        assert response.name == "Test User"

    @pytest.mark.asyncio
    async def test_create_user_boundary_values(self, mock_repositories):
        """Happy Path: Test boundary values (e.g., long name)."""
        user_repo = mock_repositories["user_repo"]
        long_name = "A" * 100
        user_create = UserCreate(email="long@example.com", name=long_name)
        response = await user_repo.create_user("user-456", user_create)
        assert response.name == long_name


class TestUserRepositoryRead:
    @pytest.mark.asyncio
    async def test_get_user_success(self, mock_repositories):
        """Happy Path: Retrieve a user."""
        user_repo = mock_repositories["user_repo"]
        user_create = UserCreate(email="retrieve@example.com", name="Retrieve User")
        await user_repo.create_user("user-123", user_create)
        response = await user_repo.get_user("user-123")
        assert response is not None
        assert response.email == "retrieve@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_repositories):
        """Failure Mode: User not found."""
        user_repo = mock_repositories["user_repo"]
        response = await user_repo.get_user("nonexistent")
        assert response is None


class TestUserRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_user_success(self, mock_repositories):
        """Happy Path: Update a user."""
        user_repo = mock_repositories["user_repo"]
        user_create = UserCreate(email="original@example.com", name="Original")
        await user_repo.create_user("user-123", user_create)
        updates = {"name": "Updated"}
        response = await user_repo.update_user("user-123", updates)
        assert response.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, mock_repositories):
        """Failure Mode: Update non-existent user raises error."""
        user_repo = mock_repositories["user_repo"]
        with pytest.raises(ClientError):
            await user_repo.update_user("nonexistent", {"name": "Fail"})


class TestUserRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_user_success(self, mock_repositories):
        """Happy Path: Delete a user."""
        user_repo = mock_repositories["user_repo"]
        user_create = UserCreate(email="delete@example.com", name="Delete User")
        await user_repo.create_user("user-123", user_create)
        await user_repo.delete_user("user-123")
        response = await user_repo.get_user("user-123")
        assert response is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, mock_repositories):
        """Success Mode: Delete non-existent user should not raise error (DynamoDB behavior)."""
        user_repo = mock_repositories["user_repo"]
        # DynamoDB delete_item doesn't raise error for non-existent items
        await user_repo.delete_user("nonexistent")  # Should complete without error


# Error Handling and Edge Cases
class TestUserRepositoryErrors:
    @pytest.mark.asyncio
    async def test_dynamodb_client_error_simulation(self, mock_repositories, mocker):
        """Failure Mode: Simulate DynamoDB errors (e.g., throttling)."""
        user_repo = mock_repositories["user_repo"]
        mocker.patch.object(
            user_repo.table,
            "put_item",
            side_effect=ClientError(
                {"Error": {"Code": "ThrottlingException"}}, "PutItem"
            ),
        )
        user_create = UserCreate(email="fail@example.com", name="Fail User")
        with pytest.raises(ClientError):
            await user_repo.create_user("user-123", user_create)


# Integration with Models
class TestUserRepositoryModelIntegration:
    @pytest.mark.asyncio
    async def test_full_crud_cycle(self, mock_repositories):
        """Happy Path: Full create-read-update-delete cycle with model validation."""
        user_repo = mock_repositories["user_repo"]
        user_create = UserCreate(email="cycle@example.com", name="Cycle User")
        created = await user_repo.create_user("user-123", user_create)
        assert created.email == "cycle@example.com"

        fetched = await user_repo.get_user("user-123")
        assert fetched.name == "Cycle User"

        updated = await user_repo.update_user("user-123", {"name": "Updated Cycle"})
        assert updated.name == "Updated Cycle"

        await user_repo.delete_user("user-123")
        deleted = await user_repo.get_user("user-123")
        assert deleted is None
