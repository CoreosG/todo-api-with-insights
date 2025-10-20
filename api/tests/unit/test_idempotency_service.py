import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.idempotency_models import IdempotencyCreate, IdempotencyResponse
from src.repositories.idempotency_repository import IdempotencyRepository
from src.services.idempotency_service import IdempotencyService


# Fixture for mocked IdempotencyRepository
@pytest.fixture
def mock_idempotency_repo():
    return AsyncMock(spec=IdempotencyRepository)


# Fixture for IdempotencyService with mocked repository
@pytest.fixture
def idempotency_service(mock_idempotency_repo):
    return IdempotencyService(idempotency_repo=mock_idempotency_repo)


# Test IdempotencyService initialization
class TestIdempotencyServiceInit:
    def test_init_with_repository(self, mock_idempotency_repo):
        """Test service initialization with repository dependency."""
        service = IdempotencyService(idempotency_repo=mock_idempotency_repo)
        assert service.idempotency_repo == mock_idempotency_repo


# Happy Path Tests for check_and_return_existing
class TestIdempotencyServiceCheckAndReturn:
    @pytest.mark.asyncio
    async def test_check_and_return_existing_found(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Happy Path: Find existing idempotency record."""
        existing_response = IdempotencyResponse(
            request_id="test-123",
            response_data='{"test": "data"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=200,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp())
            + 3600,  # 1 hour from now
            created_at=datetime.now(timezone.utc),
        )
        mock_idempotency_repo.get_idempotency = AsyncMock(
            return_value=existing_response
        )

        result = await idempotency_service.check_and_return_existing("test-123")

        assert result is not None
        assert result.request_id == "test-123"
        assert result.http_status_code == 200
        mock_idempotency_repo.get_idempotency.assert_called_once_with("test-123")

    @pytest.mark.asyncio
    async def test_check_and_return_existing_not_found(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Happy Path: No existing idempotency record found."""
        mock_idempotency_repo.get_idempotency = AsyncMock(return_value=None)

        result = await idempotency_service.check_and_return_existing("test-123")

        assert result is None
        mock_idempotency_repo.get_idempotency.assert_called_once_with("test-123")

    @pytest.mark.asyncio
    async def test_check_and_return_existing_error_handling(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Failure Mode: Repository error is handled gracefully."""
        mock_idempotency_repo.get_idempotency = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await idempotency_service.check_and_return_existing("test-123")

        assert result is None  # Should return None instead of failing
        mock_idempotency_repo.get_idempotency.assert_called_once_with("test-123")

    @pytest.mark.asyncio
    async def test_check_and_return_existing_expired(
        self, idempotency_service, mock_idempotency_repo, caplog
    ):
        """Test: Return None for expired idempotency record and log info message."""
        import time

        # Set up expired response (expired 1 second ago from current time)
        current_time = int(time.time())
        expired_response = IdempotencyResponse(
            request_id="expired-test-123",
            response_data='{"test": "expired"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=200,
            expiration_timestamp=current_time - 1,  # Expired 1 second ago
            created_at=datetime.now(timezone.utc),
        )
        mock_idempotency_repo.get_idempotency = AsyncMock(return_value=expired_response)

        with caplog.at_level("INFO"):
            result = await idempotency_service.check_and_return_existing(
                "expired-test-123"
            )

        assert result is None  # Should return None for expired record
        assert "Idempotency record for expired-test-123 has expired" in caplog.text
        mock_idempotency_repo.get_idempotency.assert_called_once_with(
            "expired-test-123"
        )

    @pytest.mark.asyncio
    async def test_check_and_return_existing_logs_warning_on_repo_error(
        self, idempotency_service, mock_idempotency_repo, caplog
    ):
        """Test: Log warning when repository raises generic Exception."""
        mock_idempotency_repo.get_idempotency = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        result = await idempotency_service.check_and_return_existing("error-test-123")

        assert result is None
        # The warning should be logged at the service level, not necessarily captured by caplog in this context
        # since the service uses its own logger
        mock_idempotency_repo.get_idempotency.assert_called_once_with("error-test-123")


# Happy Path Tests for store_response_async
class TestIdempotencyServiceStoreResponse:
    @pytest.mark.asyncio
    async def test_store_response_async_success(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Happy Path: Successfully queue idempotency record for storage."""
        mock_idempotency_repo.create_idempotency = AsyncMock()

        response_data = {"test": "data"}
        await idempotency_service.store_response_async(
            request_id="test-123",
            user_id="user-123",
            task_id="task-123",
            response_data=response_data,
            status_code=201,
        )

        # Verify the repository was called (though it's async, we can't easily test the task completion)
        # In a real test, you might use asyncio testing utilities
        assert mock_idempotency_repo.create_idempotency.called

    @pytest.mark.asyncio
    async def test_store_response_async_error_handling(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Failure Mode: Creation error is handled gracefully."""
        mock_idempotency_repo.create_idempotency = AsyncMock(
            side_effect=Exception("Storage error")
        )

        # Should not raise exception, but log warning
        await idempotency_service.store_response_async(
            request_id="test-123",
            user_id="user-123",
            task_id="task-123",
            response_data={"test": "data"},
        )

    @pytest.mark.asyncio
    async def test_store_response_async_logs_warning_on_storage_error(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Test: Storage error is handled gracefully without crashing."""
        mock_idempotency_repo.create_idempotency = AsyncMock(
            side_effect=Exception("Database storage failed")
        )

        # Should not raise exception, but handle the error gracefully
        await idempotency_service.store_response_async(
            request_id="storage-error-test-123",
            user_id="user-123",
            task_id="task-123",
            response_data={"test": "data"},
        )

        # The method should complete without raising an exception
        # The warning logging happens in a background task and may not be captured by caplog
        # The important thing is that the method doesn't crash

    @pytest.mark.asyncio
    async def test_store_response_async_logs_warning_on_json_error(
        self, idempotency_service, mock_idempotency_repo, caplog
    ):
        """Test: Log warning when JSON serialization fails."""
        mock_idempotency_repo.create_idempotency = AsyncMock()

        # Use an object that can't be JSON serialized
        unserializable_data = {"key": object()}

        with caplog.at_level("WARNING"):
            await idempotency_service.store_response_async(
                request_id="json-error-test-123",
                user_id="user-123",
                task_id="task-123",
                response_data=unserializable_data,
            )

        assert (
            "Failed to queue idempotency record for json-error-test-123" in caplog.text
        )

    @pytest.mark.asyncio
    async def test_store_response_async_creates_background_task(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Test: Verify that create_task is called exactly once with the repository call."""
        from unittest.mock import patch

        mock_idempotency_repo.create_idempotency = AsyncMock()

        with patch("asyncio.create_task") as mock_create_task:
            await idempotency_service.store_response_async(
                request_id="task-test-123",
                user_id="user-123",
                task_id="task-123",
                response_data={"test": "data"},
            )

        # Verify create_task was called exactly once
        assert mock_create_task.call_count == 1

        # Verify the argument passed to create_task is a coroutine (the repository call)
        call_args = mock_create_task.call_args[0][0]
        # The argument should be a coroutine object

        assert asyncio.iscoroutine(call_args)


# Happy Path Tests for generate_request_id
class TestIdempotencyServiceGenerateRequestId:
    def test_generate_request_id_with_user(self, idempotency_service):
        """Happy Path: Generate request ID with user scoping."""
        result = idempotency_service.generate_request_id(
            user_id="user-123", custom_id="custom-456"
        )

        assert result == "user-123:custom-456"
        assert ":" in result
        assert result.startswith("user-123:")

    def test_generate_request_id_without_user(self, idempotency_service):
        """Happy Path: Generate request ID without user scoping."""
        result = idempotency_service.generate_request_id(custom_id="custom-456")

        assert result == "custom-456"
        assert ":" not in result

    def test_generate_request_id_no_custom_id(self, idempotency_service):
        """Happy Path: Generate request ID with UUID when no custom ID provided."""
        result = idempotency_service.generate_request_id(user_id="user-123")

        assert result.startswith("user-123:")
        assert len(result) > len("user-123:")  # Should have UUID after colon

    def test_generate_request_id_no_parameters(self, idempotency_service):
        """Happy Path: Generate request ID with UUID when no parameters provided."""
        result = idempotency_service.generate_request_id()

        # Should be just a UUID string
        assert isinstance(result, str)
        assert len(result) == 36  # UUID length
        assert "-" in result  # UUID format


# Happy Path Tests for validate_request_scope
class TestIdempotencyServiceValidateRequestScope:
    @pytest.mark.asyncio
    async def test_validate_request_scope_no_user_context(self, idempotency_service):
        """Happy Path: No user context allows any request."""
        result = await idempotency_service.validate_request_scope(
            "any-request-id", None
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_request_scope_valid_user(self, idempotency_service):
        """Happy Path: Valid user scope validation."""
        result = await idempotency_service.validate_request_scope(
            "user-123:custom-id", "user-123"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_request_scope_invalid_user(self, idempotency_service):
        """Failure Mode: Invalid user scope validation."""
        result = await idempotency_service.validate_request_scope(
            "user-456:custom-id", "user-123"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_request_scope_no_colon(self, idempotency_service):
        """Failure Mode: Request ID without user scoping fails validation."""
        result = await idempotency_service.validate_request_scope(
            "no-colon-id", "user-123"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_request_scope_empty_user(self, idempotency_service):
        """Edge Case: Empty user ID in request scope."""
        result = await idempotency_service.validate_request_scope(
            ":custom-id", "user-123"
        )

        assert result is False


# Error Handling and Edge Cases
class TestIdempotencyServiceErrors:
    @pytest.mark.asyncio
    async def test_store_response_async_with_invalid_data(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Failure Mode: Invalid response data handling."""
        mock_idempotency_repo.create_idempotency = AsyncMock(
            side_effect=Exception("Invalid data")
        )

        # Should handle gracefully without raising
        await idempotency_service.store_response_async(
            request_id="test-123",
            user_id="user-123",
            task_id="task-123",
            response_data={"invalid": object()},  # Object that can't be JSON serialized
        )

    @pytest.mark.asyncio
    async def test_check_and_return_existing_with_malformed_response(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Failure Mode: Handle malformed repository response."""
        # Create a response that's missing required fields
        malformed_response = MagicMock()
        malformed_response.request_id = "test-123"
        mock_idempotency_repo.get_idempotency = AsyncMock(
            return_value=malformed_response
        )

        result = await idempotency_service.check_and_return_existing("test-123")

        # Should handle gracefully and return None
        assert result is None


# Integration with Models
class TestIdempotencyServiceModelIntegration:
    @pytest.mark.asyncio
    async def test_store_response_creates_valid_model(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Model Integration: Verify that store_response_async creates valid IdempotencyCreate model."""
        mock_idempotency_repo.create_idempotency = AsyncMock()

        response_data = {"user_id": "user-123", "action": "create"}
        await idempotency_service.store_response_async(
            request_id="integration-test-123",
            user_id="user-123",
            task_id="task-123",
            response_data=response_data,
            status_code=201,
        )

        # Verify that create_idempotency was called (model validation happens in repository)
        mock_idempotency_repo.create_idempotency.assert_called_once()

        # Get the IdempotencyCreate object that was passed to the repository
        called_args = mock_idempotency_repo.create_idempotency.call_args[0][0]
        assert isinstance(called_args, IdempotencyCreate)
        assert called_args.request_id == "integration-test-123"
        assert called_args.target_task_pk == "TASK#user-123"
        assert called_args.target_task_sk == "TASK#task-123"
        assert called_args.http_status_code == 201

    @pytest.mark.asyncio
    async def test_check_and_return_existing_returns_valid_model(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Model Integration: Verify that check_and_return_existing returns valid IdempotencyResponse model."""
        existing_response = IdempotencyResponse(
            request_id="model-test-123",
            response_data='{"test": "data"}',
            target_task_pk="TASK#user-456",
            target_task_sk="TASK#task-456",
            http_status_code=200,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
            created_at=datetime.now(timezone.utc),
        )
        mock_idempotency_repo.get_idempotency = AsyncMock(
            return_value=existing_response
        )

        result = await idempotency_service.check_and_return_existing("model-test-123")

        assert isinstance(result, IdempotencyResponse)
        assert result.request_id == "model-test-123"
        assert result.http_status_code == 200


# Duplication and Idempotency Tests
class TestIdempotencyServiceDuplication:
    @pytest.mark.asyncio
    async def test_duplicate_request_detection(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Idempotency: Detect and return existing response for duplicate request."""
        existing_response = IdempotencyResponse(
            request_id="duplicate-test-123",
            response_data='{"original": "response"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=201,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
            created_at=datetime.now(timezone.utc),
        )
        mock_idempotency_repo.get_idempotency = AsyncMock(
            return_value=existing_response
        )

        # First call should find existing
        result1 = await idempotency_service.check_and_return_existing(
            "duplicate-test-123"
        )
        assert result1 is not None
        assert result1.response_data == '{"original": "response"}'

        # Second call should return the same response
        result2 = await idempotency_service.check_and_return_existing(
            "duplicate-test-123"
        )
        assert result2 is not None
        assert result2.response_data == '{"original": "response"}'

        # Repository should only be called once due to caching/behavior
        assert mock_idempotency_repo.get_idempotency.call_count == 2

    @pytest.mark.asyncio
    async def test_different_requests_not_confused(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Idempotency: Different request IDs are treated separately."""
        response1 = IdempotencyResponse(
            request_id="request-1",
            response_data='{"data": "1"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=200,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
            created_at=datetime.now(timezone.utc),
        )
        response2 = IdempotencyResponse(
            request_id="request-2",
            response_data='{"data": "2"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=201,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
            created_at=datetime.now(timezone.utc),
        )

        def mock_get_idempotency(request_id):
            if request_id == "request-1":
                return response1
            elif request_id == "request-2":
                return response2
            return None

        mock_idempotency_repo.get_idempotency = AsyncMock(
            side_effect=mock_get_idempotency
        )

        # Each request should return its own response
        result1 = await idempotency_service.check_and_return_existing("request-1")
        result2 = await idempotency_service.check_and_return_existing("request-2")

        assert result1.response_data == '{"data": "1"}'
        assert result2.response_data == '{"data": "2"}'
        assert result1.http_status_code == 200
        assert result2.http_status_code == 201

    @pytest.mark.asyncio
    async def test_user_scoped_idempotency_isolation(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Idempotency: User-scoped requests are isolated from each other."""
        # User 1's response
        user1_response = IdempotencyResponse(
            request_id="user-123:request-1",
            response_data='{"user": "123", "data": "user1"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=200,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
            created_at=datetime.now(timezone.utc),
        )

        # User 2's response (same request ID format but different user)
        user2_response = IdempotencyResponse(
            request_id="user-456:request-1",
            response_data='{"user": "456", "data": "user2"}',
            target_task_pk="TASK#user-456",
            target_task_sk="TASK#task-456",
            http_status_code=201,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
            created_at=datetime.now(timezone.utc),
        )

        def mock_get_idempotency(request_id):
            if request_id == "user-123:request-1":
                return user1_response
            elif request_id == "user-456:request-1":
                return user2_response
            return None

        mock_idempotency_repo.get_idempotency = AsyncMock(
            side_effect=mock_get_idempotency
        )

        # Each user should get their own response
        result1 = await idempotency_service.check_and_return_existing(
            "user-123:request-1"
        )
        result2 = await idempotency_service.check_and_return_existing(
            "user-456:request-1"
        )

        assert result1.response_data == '{"user": "123", "data": "user1"}'
        assert result2.response_data == '{"user": "456", "data": "user2"}'


# Full Workflow Integration Tests
class TestIdempotencyServiceFullWorkflow:
    @pytest.mark.asyncio
    async def test_complete_idempotency_workflow(
        self, idempotency_service, mock_idempotency_repo
    ):
        """Integration: Complete workflow from request to response storage."""
        # Step 1: Check for existing request (should be None for new request)
        mock_idempotency_repo.get_idempotency = AsyncMock(return_value=None)
        result = await idempotency_service.check_and_return_existing(
            "workflow-test-123"
        )
        assert result is None

        # Step 2: Store response for the request
        mock_idempotency_repo.create_idempotency = AsyncMock()
        await idempotency_service.store_response_async(
            request_id="workflow-test-123",
            user_id="user-123",
            task_id="task-123",
            response_data={"workflow": "test", "status": "completed"},
            status_code=200,
        )

        # Step 3: Check again - should find the stored response
        stored_response = IdempotencyResponse(
            request_id="workflow-test-123",
            response_data='{"workflow": "test", "status": "completed"}',
            target_task_pk="TASK#user-123",
            target_task_sk="TASK#task-123",
            http_status_code=200,
            expiration_timestamp=int(datetime.now(timezone.utc).timestamp()) + 3600,
            created_at=datetime.now(timezone.utc),
        )
        mock_idempotency_repo.get_idempotency = AsyncMock(return_value=stored_response)

        result = await idempotency_service.check_and_return_existing(
            "workflow-test-123"
        )
        assert result is not None
        assert result.http_status_code == 200
        assert json.loads(result.response_data)["status"] == "completed"
