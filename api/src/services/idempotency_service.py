import asyncio
import json
import logging
from datetime import datetime, timezone

from ..models.idempotency_models import IdempotencyCreate, IdempotencyResponse
from ..repositories.idempotency_repository import IdempotencyRepository

logger = logging.getLogger(__name__)


class IdempotencyService:
    def __init__(self, idempotency_repo: IdempotencyRepository):
        self.idempotency_repo = idempotency_repo

    async def check_and_return_existing(
        self, request_id: str
    ) -> IdempotencyResponse | None:
        """Check if request exists and return the stored response."""
        try:
            existing = await self.idempotency_repo.get_idempotency(request_id)
            if existing:
                # Check if the record has expired
                current_timestamp = int(datetime.now(timezone.utc).timestamp())
                if existing.expiration_timestamp < current_timestamp:
                    logger.info(
                        f"Idempotency record for {request_id} has expired (expired at {existing.expiration_timestamp}, current time {current_timestamp})"
                    )
                    return None

                logger.info(f"Found existing idempotency record for {request_id}")
                return existing
            return None
        except Exception as e:
            logger.warning(f"Failed to check idempotency for {request_id}: {e}")
            # Don't fail the request if idempotency check fails
            return None

    async def store_response_async(
        self,
        request_id: str,
        user_id: str,
        task_id: str,
        response_data: dict,
        status_code: int = 201,
    ) -> None:
        """Store idempotency record asynchronously to avoid blocking the response."""
        try:
            idempotency = IdempotencyCreate(
                request_id=request_id,
                response_data=json.dumps(response_data),
                target_task_pk=f"TASK#{user_id}",
                target_task_sk=f"TASK#{task_id}",
                http_status_code=status_code,
                expiration_timestamp=int(datetime.now(timezone.utc).timestamp())
                + 86400,
            )

            # Use asyncio.create_task to avoid blocking the response
            asyncio.create_task(self.idempotency_repo.create_idempotency(idempotency))
            logger.info(f"Idempotency record queued for {request_id}")

        except Exception as e:
            logger.warning(f"Failed to queue idempotency record for {request_id}: {e}")

    def generate_request_id(
        self, user_id: str | None = None, custom_id: str | None = None
    ) -> str:
        """Generate a unique request ID for idempotency tracking."""
        import uuid

        base_request_id = custom_id or str(uuid.uuid4())
        return f"{user_id}:{base_request_id}" if user_id else base_request_id

    async def validate_request_scope(
        self, request_id: str, expected_user_id: str | None
    ) -> bool:
        """Validate that the request_id is scoped to the correct user."""
        if not expected_user_id:
            return True  # No user context, allow global requests

        # Extract user_id from request_id (format: "user_id:uuid")
        if ":" in request_id:
            request_user_id = request_id.split(":")[0]
            return request_user_id == expected_user_id

        return False  # Request ID doesn't contain user scoping
