from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from src.models.idempotency_models import IdempotencyCreate, IdempotencyResponse
from src.repositories.idempotency_repository import IdempotencyRepository


# Fixture to set up a mocked DynamoDB table for each test (exact copy from user tests)
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


# Fixture for IdempotencyRepository instance (exact copy from user tests)
@pytest.fixture
def idempotency_repo(dynamodb_table):
    return IdempotencyRepository(table_name="todo-app-data", region="us-east-1")


# Happy Path Tests for CRUD Operations (Create)
class TestIdempotencyRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_idempotency_success(self, idempotency_repo):
        """Happy Path: Create an idempotency record and verify DynamoDB item + response."""
        idempotency = IdempotencyCreate(
            request_id="req-123",
            response_data='{"status": "success"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=201,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 86400,
        )
        response = await idempotency_repo.create_idempotency(idempotency)
        assert isinstance(response, IdempotencyResponse)
        assert response.request_id == "req-123"
        assert response.http_status_code == 201

    @pytest.mark.asyncio
    async def test_create_idempotency_boundary_values(self, idempotency_repo):
        """Happy Path: Test boundary values (e.g., long request_id)."""
        long_id = "A" * 255
        idempotency = IdempotencyCreate(
            request_id=long_id,
            response_data='{"data": "test"}',
            target_task_pk="TASK#user-456",
            target_task_sk="TASK#task-456",
            http_status_code=200,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
        )
        response = await idempotency_repo.create_idempotency(idempotency)
        assert response.request_id == long_id


# Happy Path Tests for Read (Get)
class TestIdempotencyRepositoryRead:
    @pytest.mark.asyncio
    async def test_get_idempotency_success(self, idempotency_repo):
        """Happy Path: Retrieve an idempotency record."""
        idempotency = IdempotencyCreate(
            request_id="req-456",
            response_data='{"status": "created"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-789",
            http_status_code=201,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 86400,
        )
        await idempotency_repo.create_idempotency(idempotency)
        response = await idempotency_repo.get_idempotency("req-456")
        assert response is not None
        assert response.response_data == '{"status": "created"}'

    @pytest.mark.asyncio
    async def test_get_idempotency_not_found(self, idempotency_repo):
        """Failure Mode: Record not found."""
        response = await idempotency_repo.get_idempotency("nonexistent")
        assert response is None


class TestIdempotencyRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_idempotency_success(self, idempotency_repo):
        """Happy Path: Delete an idempotency record."""
        idempotency = IdempotencyCreate(
            request_id="req-789",
            response_data='{"status": "deleted"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-999",
            http_status_code=200,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 86400,
        )
        await idempotency_repo.create_idempotency(idempotency)
        await idempotency_repo.delete_idempotency("req-789")
        response = await idempotency_repo.get_idempotency("req-789")
        assert response is None

    @pytest.mark.asyncio
    async def test_delete_idempotency_not_found(self, idempotency_repo):
        """Success Mode: Delete non-existent record should not raise error (DynamoDB behavior)."""
        await idempotency_repo.delete_idempotency(
            "nonexistent"
        )  # Should complete without error


# Error Handling and Edge Cases
class TestIdempotencyRepositoryErrors:
    @pytest.mark.asyncio
    async def test_dynamodb_client_error_simulation(self, idempotency_repo, mocker):
        """Failure Mode: Simulate DynamoDB errors (e.g., throttling)."""
        mocker.patch.object(
            idempotency_repo.table,
            "put_item",
            side_effect=ClientError(
                {"Error": {"Code": "ThrottlingException"}}, "PutItem"
            ),
        )
        idempotency = IdempotencyCreate(
            request_id="req-fail",
            response_data='{"error": "test"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=500,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 86400,
        )
        with pytest.raises(ClientError):
            await idempotency_repo.create_idempotency(idempotency)

    @pytest.mark.asyncio
    async def test_create_idempotency_propagates_client_error(self, idempotency_repo):
        """Test: ClientError is properly propagated from create_idempotency."""
        # Mock the table's put_item method to raise ClientError
        from unittest.mock import MagicMock

        mock_put_item = MagicMock(
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ValidationException",
                        "Message": "Invalid request",
                    }
                },
                "PutItem",
            )
        )

        with pytest.MonkeyPatch().context() as m:
            m.setattr(idempotency_repo.table, "put_item", mock_put_item)

            idempotency = IdempotencyCreate(
                request_id="client-error-test",
                response_data='{"test": "data"}',
                target_task_pk="TASK#user-123",
                target_task_sk="TASK#task-123",
                http_status_code=200,
                expiration_timestamp=int(datetime.now(timezone.utc).timestamp())
                + 86400,
            )

            # Should re-raise the ClientError
            with pytest.raises(ClientError) as exc_info:
                await idempotency_repo.create_idempotency(idempotency)

            assert exc_info.value.response["Error"]["Code"] == "ValidationException"


# Integration with Models
class TestIdempotencyRepositoryModelIntegration:
    @pytest.mark.asyncio
    async def test_full_crud_cycle(self, idempotency_repo):
        """Happy Path: Full create-read-delete cycle with model validation."""
        idempotency = IdempotencyCreate(
            request_id="req-cycle",
            response_data='{"status": "cycle"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=201,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 86400,
        )
        created = await idempotency_repo.create_idempotency(idempotency)
        assert created.http_status_code == 201

        fetched = await idempotency_repo.get_idempotency("req-cycle")
        assert fetched is not None
        assert fetched.response_data == '{"status": "cycle"}'

        await idempotency_repo.delete_idempotency("req-cycle")
        deleted = await idempotency_repo.get_idempotency("req-cycle")
        assert deleted is None

    @pytest.mark.asyncio
    async def test_item_to_idempotency_response_helper(self, idempotency_repo):
        """Happy Path: Test helper method for item conversion."""
        item = {
            "PK": "IDEMPOTENCY#req-helper",
            "SK": "METADATA",
            "response_data": '{"test": "data"}',
            "target_task_pk": "TASK#user-123",
            "target_task_sk": "TASK#task-123",
            "http_status_code": 200,
            "expiration_timestamp": int(datetime.now(timezone.utc).timestamp()) + 86400,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        response = idempotency_repo._item_to_idempotency_response(item)
        assert isinstance(response, IdempotencyResponse)
        assert response.request_id == "req-helper"
        assert response.response_data == '{"test": "data"}'
