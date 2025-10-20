import json  # Added for JSON parsing in serialization test
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models.idempotency_models import (
    IdempotencyCreate,
    IdempotencyResponse,
    IdempotencyUpdate,
)


# Test IdempotencyCreate Model
class TestIdempotencyCreate:
    def test_idempotency_create_valid(self):
        """Happy Path: Create with typical valid data."""
        record = IdempotencyCreate(
            request_id="req-123",
            response_data='{"status": "success"}',
            target_task_pk="TASK#user-456",
            target_task_sk="TASK#task-789",
            http_status_code=200,
            expiration_timestamp=1634567890,
        )
        assert record.request_id == "req-123"
        assert record.http_status_code == 200
        assert record.expiration_timestamp == 1634567890

    def test_idempotency_create_boundary_values(self):
        """Happy Path: Test boundary values (e.g., min/max request_id length, status code range)."""
        # Min request_id length
        record = IdempotencyCreate(
            request_id="A",
            response_data="{}",
            target_task_pk="TASK#user-1",
            target_task_sk="TASK#task-1",
            http_status_code=100,
            expiration_timestamp=1,
        )
        assert record.request_id == "A"
        # Max request_id length (255 chars)
        long_id = "A" * 255
        record = IdempotencyCreate(
            request_id=long_id,
            response_data="{}",
            target_task_pk="TASK#user-1",
            target_task_sk="TASK#task-1",
            http_status_code=599,
            expiration_timestamp=9999999999,
        )
        assert record.request_id == long_id
        assert record.http_status_code == 599

    def test_idempotency_create_invalid_request_id(self):
        """Failure Mode: Invalid request_id (too short or too long)."""
        with pytest.raises(ValidationError):
            IdempotencyCreate(
                request_id="",  # Too short
                response_data="{}",
                target_task_pk="TASK#user-1",
                target_task_sk="TASK#task-1",
                http_status_code=200,
                expiration_timestamp=1234567890,
            )
        with pytest.raises(ValidationError):
            IdempotencyCreate(
                request_id="A" * 256,  # Too long
                response_data="{}",
                target_task_pk="TASK#user-1",
                target_task_sk="TASK#task-1",
                http_status_code=200,
                expiration_timestamp=1234567890,
            )

    def test_idempotency_create_invalid_http_status_code(self):
        """Failure Mode: Invalid status code (out of 100-599 range)."""
        with pytest.raises(ValidationError):
            IdempotencyCreate(
                request_id="req-123",
                response_data="{}",
                target_task_pk="TASK#user-1",
                target_task_sk="TASK#task-1",
                http_status_code=99,  # Below min
                expiration_timestamp=1234567890,
            )
        with pytest.raises(ValidationError):
            IdempotencyCreate(
                request_id="req-123",
                response_data="{}",
                target_task_pk="TASK#user-1",
                target_task_sk="TASK#task-1",
                http_status_code=600,  # Above max
                expiration_timestamp=1234567890,
            )

    def test_idempotency_create_missing_required_fields(self):
        """Failure Mode: Missing required fields."""
        with pytest.raises(ValidationError):
            IdempotencyCreate(
                request_id="req-123",
                # Missing others
            )


# Test IdempotencyResponse Model
class TestIdempotencyResponse:
    def test_idempotency_response_valid(self, mocker):
        """Happy Path: Create with valid data, mocking timestamps."""
        mock_now = datetime(2023, 10, 1, 12, 0, 0)
        mocker.patch(
            "src.models.idempotency_models.datetime",
            utcnow=lambda: mock_now,  # Fixed path
        )
        record = IdempotencyResponse(
            request_id="req-456",
            response_data='{"status": "created"}',
            target_task_pk="TASK#user-789",
            target_task_sk="TASK#task-012",
            http_status_code=201,
            expiration_timestamp=1634567890,
            created_at=mock_now,
        )
        assert record.request_id == "req-456"
        assert record.created_at == mock_now

    def test_idempotency_response_boundary_values(self, mocker):
        """Happy Path: Test boundary values."""
        mock_now = datetime(2023, 10, 1)
        mocker.patch(
            "src.models.idempotency_models.datetime",
            utcnow=lambda: mock_now,  # Fixed path
        )
        # Max request_id
        long_id = "B" * 255
        record = IdempotencyResponse(
            request_id=long_id,
            response_data="{}",
            target_task_pk="TASK#user-1",
            target_task_sk="TASK#task-1",
            http_status_code=404,
            expiration_timestamp=1234567890,
            created_at=mock_now,
        )
        assert record.request_id == long_id

    def test_idempotency_response_invalid_status_code(self):
        """Failure Mode: Invalid status code."""
        with pytest.raises(ValidationError):
            IdempotencyResponse(
                request_id="req-123",
                response_data="{}",
                target_task_pk="TASK#user-1",
                target_task_sk="TASK#task-1",
                http_status_code=99,
                expiration_timestamp=1234567890,
                created_at=datetime.now(timezone.utc),  # Fixed: Use timezone.utc
            )

    def test_idempotency_response_missing_required_fields(self):
        """Failure Mode: Missing required fields (e.g., created_at)."""
        with pytest.raises(ValidationError):
            IdempotencyResponse(
                request_id="req-123",
                response_data="{}",
                target_task_pk="TASK#user-1",
                target_task_sk="TASK#task-1",
                http_status_code=200,
                expiration_timestamp=1234567890,
                # Missing created_at
            )


# Test IdempotencyUpdate Model
class TestIdempotencyUpdate:
    def test_idempotency_update_valid_partial(self):
        """Happy Path: Partial update with valid data."""
        update = IdempotencyUpdate(
            response_data='{"updated": true}', http_status_code=200
        )
        assert update.response_data == '{"updated": true}'
        assert update.http_status_code == 200
        # Other fields None
        assert update.expiration_timestamp is None

    def test_idempotency_update_boundary_values(self):
        """Happy Path: Test boundary values for update fields."""
        # Max request_id in inherited fields (if applicable, but update doesn't have it directly)
        long_response = "C" * 10000  # Assuming no strict limit, but test large data
        update = IdempotencyUpdate(response_data=long_response)
        assert update.response_data == long_response

    def test_idempotency_update_invalid_http_status_code(self):
        """Failure Mode: Invalid status code in update."""
        with pytest.raises(ValidationError):
            IdempotencyUpdate(http_status_code=99)

    def test_idempotency_update_all_optional(self):
        """Happy Path: All fields can be None for partial updates."""
        update = IdempotencyUpdate()
        assert update.response_data is None
        assert update.http_status_code is None

    def test_idempotency_update_extra_fields_forbidden(self):
        """Failure Mode: Extra fields raise error."""
        with pytest.raises(ValidationError):
            IdempotencyUpdate(response_data="{}", extra_field="not allowed")


# Integration Test for Serialization
class TestIdempotencySerialization:
    def test_idempotency_create_dict_serialization(self):
        """Happy Path: Ensure dict() works for serialization."""
        record = IdempotencyCreate(
            request_id="req-serial",
            response_data="{}",
            target_task_pk="TASK#user-1",
            target_task_sk="TASK#task-1",
            http_status_code=200,
            expiration_timestamp=1234567890,
        )
        data = record.model_dump()  # Updated for Pydantic V2
        assert data["request_id"] == "req-serial"
        assert data["http_status_code"] == 200

    def test_idempotency_response_json_serialization(self, mocker):
        """Happy Path: JSON serialization."""
        mock_now = datetime(2023, 10, 1)
        mocker.patch(
            "src.models.idempotency_models.datetime",
            utcnow=lambda: mock_now,  # Fixed path
        )
        record = IdempotencyResponse(
            request_id="req-json",
            response_data="{}",
            target_task_pk="TASK#user-1",
            target_task_sk="TASK#task-1",
            http_status_code=201,
            expiration_timestamp=1234567890,
            created_at=mock_now,
        )
        json_data = record.model_dump_json()  # Updated for Pydantic V2
        # Fix: Parse JSON to check contents accurately
        parsed = json.loads(json_data)
        assert parsed["request_id"] == "req-json"
        assert parsed["http_status_code"] == 201
