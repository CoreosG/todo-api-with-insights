from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request

from src.dependecies import (
    UserContext,
    check_idempotency,
    get_request_id,
    get_user_context,
    get_user_id,
    store_idempotency,
)


class TestGetRequestId:
    """Test get_request_id function for request ID generation."""

    @pytest.mark.asyncio
    async def test_get_request_id_with_idempotency_key(self):
        """Test get_request_id with Idempotency-Key header (highest priority)."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"Idempotency-Key": "test-key-123"}

        result = await get_request_id(mock_request, idempotency_key="test-key-123")

        assert result == "test-key-123"

    @pytest.mark.asyncio
    async def test_get_request_id_with_x_request_id(self):
        """Test get_request_id with X-Request-ID header (second priority)."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Request-ID": "req-456"}

        result = await get_request_id(mock_request)

        assert result == "req-456"

    @pytest.mark.asyncio
    async def test_get_request_id_with_amzn_request_id(self):
        """Test get_request_id with X-Amzn-RequestId header (third priority)."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Amzn-RequestId": "amzn-789"}

        result = await get_request_id(mock_request)

        assert result == "amzn-789"

    @pytest.mark.asyncio
    async def test_get_request_id_fallback_to_uuid(self):
        """Test get_request_id falls back to UUID when no headers present."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        result = await get_request_id(mock_request)

        # Should be a UUID string (36 characters with dashes)
        assert len(result) == 36
        assert result.count("-") == 4

    @pytest.mark.asyncio
    async def test_get_request_id_with_user_scoping(self):
        """Test get_request_id adds user scoping when user_id provided."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        result = await get_request_id(mock_request, user_id="user-123")

        # Should contain user_id as prefix
        assert result.startswith("user-123:")
        assert len(result) > 36  # Longer than just UUID

    @pytest.mark.asyncio
    async def test_get_request_id_without_user_scoping(self):
        """Test get_request_id doesn't add scoping when no user_id provided."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        result = await get_request_id(mock_request)

        # Should just be UUID without user prefix
        assert len(result) == 36
        assert not result.startswith("user-123:")


class TestGetUserContext:
    """Test get_user_context function for user information extraction."""

    @pytest.mark.asyncio
    async def test_get_user_context_successful_extraction(self):
        """Test get_user_context successfully extracts user info from API Gateway context."""
        mock_request = Mock(spec=Request)
        mock_request.state.event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "user-123",
                        "email": "test@example.com",
                        "name": "Test User",
                    }
                }
            }
        }

        result = await get_user_context(mock_request)

        assert isinstance(result, UserContext)
        assert result.user_id == "user-123"
        assert result.email == "test@example.com"
        assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_context_fallback_name_from_username(self):
        """Test get_user_context falls back to cognito:username when name not available."""
        mock_request = Mock(spec=Request)
        mock_request.state.event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "user-123",
                        "email": "test@example.com",
                        "cognito:username": "test@example.com",
                    }
                }
            }
        }

        result = await get_user_context(mock_request)

        assert result.name == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_context_fallback_name_from_email(self):
        """Test get_user_context falls back to email when name and username not available."""
        mock_request = Mock(spec=Request)
        mock_request.state.event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "user-123",
                        "email": "test@example.com",
                    }
                }
            }
        }

        result = await get_user_context(mock_request)

        assert result.name == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_context_missing_user_id(self):
        """Test get_user_context raises 401 when user_id (sub) is missing."""
        mock_request = Mock(spec=Request)
        mock_request.state.event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "email": "test@example.com",
                        "name": "Test User",
                    }
                }
            }
        }

        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(mock_request)

        assert exc_info.value.status_code == 401
        assert "Missing user_id" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_context_missing_email(self):
        """Test get_user_context raises 401 when email is missing."""
        mock_request = Mock(spec=Request)
        mock_request.state.event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "user-123",
                        "name": "Test User",
                    }
                }
            }
        }

        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(mock_request)

        assert exc_info.value.status_code == 401
        assert "Missing email" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_context_missing_event_context(self):
        """Test get_user_context handles missing event context gracefully."""
        mock_request = Mock(spec=Request)
        mock_request.state.event = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(mock_request)

        assert exc_info.value.status_code == 401
        assert "No API Gateway event found" in exc_info.value.detail


class TestGetUserId:
    """Test get_user_id function for backward compatibility."""

    @pytest.mark.asyncio
    async def test_get_user_id_returns_user_id_from_context(self):
        """Test get_user_id returns user_id from get_user_context."""
        mock_request = Mock(spec=Request)
        mock_request.state.event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "user-123",
                        "email": "test@example.com",
                        "name": "Test User",
                    }
                }
            }
        }

        result = await get_user_id(mock_request)

        assert result == "user-123"


class TestCheckIdempotency:
    """Test check_idempotency function for duplicate request checking."""

    @pytest.mark.asyncio
    async def test_check_idempotency_with_no_existing(self):
        """Test check_idempotency returns None when no existing request found."""
        result = await check_idempotency("test-request-id")
        assert result is None


class TestStoreIdempotency:
    """Test store_idempotency function for response caching."""

    def test_store_idempotency_async_operation(self):
        """Test store_idempotency queues async operation."""
        # Should not raise any exceptions
        store_idempotency("req-123", "user-123", "task-123", {"status": "created"}, 201)


class TestUserContext:
    """Test UserContext class."""

    def test_user_context_creation(self):
        """Test UserContext can be created with required attributes."""
        context = UserContext(
            user_id="user-123", email="test@example.com", name="Test User"
        )

        assert context.user_id == "user-123"
        assert context.email == "test@example.com"
        assert context.name == "Test User"

    def test_user_context_attributes_are_strings(self):
        """Test UserContext attributes are properly typed as strings."""
        context = UserContext(
            user_id="user-123", email="test@example.com", name="Test User"
        )

        assert isinstance(context.user_id, str)
        assert isinstance(context.email, str)
        assert isinstance(context.name, str)


# Integration tests with FastAPI app
class TestDependenciesIntegration:
    """Test dependencies functions work correctly with FastAPI app."""

    def test_dependencies_imports(self):
        """Test that all dependencies functions can be imported."""
        # This test ensures imports work correctly
        from src.dependecies import (
            UserContext,
            check_idempotency,
            get_request_id,
            get_user_context,
            get_user_id,
            store_idempotency,
        )

        # All imports should succeed
        assert check_idempotency is not None
        assert get_request_id is not None
        assert get_user_context is not None
        assert get_user_id is not None
        assert store_idempotency is not None
        assert UserContext is not None
