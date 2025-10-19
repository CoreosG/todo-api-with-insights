from datetime import datetime

from pydantic import BaseModel, Field


# Model for creating an idempotency record, based on ADR-003 schema
class IdempotencyCreate(BaseModel):
    request_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique request identifier (e.g., UUID) for idempotency checks",
    )
    response_data: str = Field(
        ...,
        description="JSON string of the API response data for duplicate requests",
    )
    target_task_pk: str = Field(
        ...,
        description="Target Task's Partition Key (e.g., TASK#{user_id}) from ADR-003",
    )
    target_task_sk: str = Field(
        ...,
        description="Target Task's Sort Key (e.g., TASK#{task_id}) from ADR-003",
    )
    http_status_code: int = Field(
        ...,
        ge=100,
        le=599,
        description="HTTP status code of the original response (100-599)",
    )
    expiration_timestamp: int = Field(
        ...,
        description="Unix timestamp for TTL-based cleanup (e.g., 24 hours after creation)",
    )


# Model for idempotency responses, including computed fields
class IdempotencyResponse(IdempotencyCreate):
    created_at: datetime = Field(
        ...,
        description="Timestamp when the idempotency record was created (Unix timestamp or ISO format)",
    )


# Optional: Model for updating an idempotency record (partial updates)
class IdempotencyUpdate(BaseModel):
    response_data: str | None = Field(
        None, description="Updated response data (optional)"
    )
    http_status_code: int | None = Field(
        None, ge=100, le=599, description="Updated status code (optional)"
    )
    expiration_timestamp: int | None = Field(
        None, description="Updated expiration timestamp (optional)"
    )

    model_config = {"extra": "forbid"}  # Pydantic V2 config for forbidding extra fields
