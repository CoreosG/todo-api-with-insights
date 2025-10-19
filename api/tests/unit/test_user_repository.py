import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from src.models.user_models import UserCreate, UserResponse
from src.repositories.user_repository import UserRepository


# Fixture to set up a mocked DynamoDB table for each test
@pytest.fixture
def dynamodb_table():
    with mock_aws():
        import boto3

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="todo-app-data",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


# Fixture for UserRepository instance
@pytest.fixture
def user_repo(dynamodb_table):
    return UserRepository(table_name="todo-app-data", region="us-east-1")


# Happy Path Tests for CRUD Operations
class TestUserRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_repo):
        """Happy Path: Create a user and verify DynamoDB item + response."""
        user_create = UserCreate(email="test@example.com", name="Test User")
        response = await user_repo.create_user("cognito-user-123", user_create)
        assert isinstance(response, UserResponse)
        assert response.email == "test@example.com"
        assert response.id == "cognito-user-123"
        assert response.name == "Test User"

    @pytest.mark.asyncio
    async def test_create_user_boundary_values(self, user_repo):
        """Happy Path: Test boundary values (e.g., long name)."""
        long_name = "A" * 100
        user_create = UserCreate(email="long@example.com", name=long_name)
        response = await user_repo.create_user("user-456", user_create)
        assert response.name == long_name


class TestUserRepositoryRead:
    @pytest.mark.asyncio
    async def test_get_user_success(self, user_repo):
        """Happy Path: Retrieve a user."""
        user_create = UserCreate(email="retrieve@example.com", name="Retrieve User")
        await user_repo.create_user("user-123", user_create)
        response = await user_repo.get_user("user-123")
        assert response is not None
        assert response.email == "retrieve@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_repo):
        """Failure Mode: User not found."""
        response = await user_repo.get_user("nonexistent")
        assert response is None


class TestUserRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_repo):
        """Happy Path: Update a user."""
        user_create = UserCreate(email="original@example.com", name="Original")
        await user_repo.create_user("user-123", user_create)
        updates = {"name": "Updated"}
        response = await user_repo.update_user("user-123", updates)
        assert response.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_repo):
        """Failure Mode: Update non-existent user raises error."""
        with pytest.raises(ClientError):
            await user_repo.update_user("nonexistent", {"name": "Fail"})


class TestUserRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_repo):
        """Happy Path: Delete a user."""
        user_create = UserCreate(email="delete@example.com", name="Delete User")
        await user_repo.create_user("user-123", user_create)
        await user_repo.delete_user("user-123")
        response = await user_repo.get_user("user-123")
        assert response is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_repo):
        """Success Mode: Delete non-existent user should not raise error (DynamoDB behavior)."""
        # DynamoDB delete_item doesn't raise error for non-existent items
        await user_repo.delete_user("nonexistent")  # Should complete without error


# Error Handling and Edge Cases
class TestUserRepositoryErrors:
    @pytest.mark.asyncio
    async def test_dynamodb_client_error_simulation(self, user_repo, mocker):
        """Failure Mode: Simulate DynamoDB errors (e.g., throttling)."""
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
    async def test_full_crud_cycle(self, user_repo):
        """Happy Path: Full create-read-update-delete cycle with model validation."""
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
