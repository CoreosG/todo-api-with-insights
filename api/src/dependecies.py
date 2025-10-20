import logging
import os
import uuid

from fastapi import HTTPException, Request

from .models.idempotency_models import IdempotencyResponse

logger = logging.getLogger(__name__)


# Idempotency-Key header dependency for FastAPI
def get_idempotency_key_from_header(request: Request) -> str:
    """Extract and validate Idempotency-Key header."""
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key header is required"
        )
    return idempotency_key


# User context information from API Gateway JWT claims
class UserContext:
    """User context extracted from API Gateway JWT claims."""

    def __init__(self, user_id: str, email: str, name: str):
        self.user_id = user_id
        self.email = email
        self.name = name


# Generate request_id for idempotency tracking
async def get_request_id(
    request: Request, user_id: str | None = None, idempotency_key: str | None = None
) -> str:
    """Generate unique request ID for idempotency tracking."""
    # Priority: Idempotency-Key header > X-Request-ID > X-Amzn-RequestId > UUID
    base_request_id = (
        idempotency_key
        or request.headers.get("X-Request-ID")
        or request.headers.get("X-Amzn-RequestId")
        or str(uuid.uuid4())
    )

    # Add user scoping for user-specific operations
    return f"{user_id}:{base_request_id}" if user_id else base_request_id


# Extract user context from request context (for API Gateway integration)
async def get_user_context(request: Request) -> UserContext:
    """Extract user context from API Gateway event context (Cognito authorizer)."""
    # For FastAPI in Lambda, extract from request context (via Mangum or direct event)
    # In production, use event["requestContext"]["authorizer"]["jwt"]["claims"] for HTTP API v2.0
    event = None

    # Add LOCAL_USER environment variable to test locally, needs to be true for local testing
    if os.getenv("LOCAL_USER") == "true":
        return UserContext(
            user_id="1234567890", email="test@example.com", name="Test User"
        )

    # Try to get event from Mangum's scope first (primary method for Lambda)
    if hasattr(request, "scope") and request.scope.get("aws.event"):
        event = request.scope["aws.event"]
    # Fallback to request.state.event (for testing or direct event passing)
    elif hasattr(request.state, "event"):
        event = request.state.event

    if not event:
        raise HTTPException(
            status_code=401, detail="Unauthorized: No API Gateway event found"
        )

    # Handle both API Gateway v1.0 (REST API) and v2.0 (HTTP API) formats
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})

    # Try HTTP API v2.0 format first (requestContext.authorizer.jwt.claims)
    claims = authorizer.get("jwt", {}).get("claims", {})

    # Fallback to REST API v1.0 format (requestContext.authorizer.claims)
    if not claims and "claims" in authorizer:
        claims = authorizer["claims"]

    user_id = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name") or claims.get("cognito:username") or email

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing user_id")
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing email")

    return UserContext(
        user_id=str(user_id),
        email=str(email),
        name=(
            str(name) if name else str(email)
        ),  # Fallback to email if name not available
    )


# Extract user_id from request context (for API Gateway integration)
async def get_user_id(request: Request) -> str:
    """Extract user_id from API Gateway event context (Cognito authorizer)."""
    user_context = await get_user_context(request)
    return user_context.user_id


# Idempotency-Key header is now handled by FastAPI Header dependency in main.py


# ------------------------------------------------------------------------------------------------
# Idempotency check function - now using actual IdempotencyService
async def check_idempotency(request_id: str) -> IdempotencyResponse | None:
    """Check for duplicate requests and return cached response if found."""
    from .utils.dependency_injection import get_idempotency_service

    idempotency_service = get_idempotency_service()
    return await idempotency_service.check_and_return_existing(request_id)


# Store idempotency record using IdempotencyService
def store_idempotency(
    request_id: str, user_id: str, task_id: str, response_data: dict, status_code: int
) -> None:
    """Store idempotency record asynchronously using IdempotencyService."""
    from .utils.dependency_injection import get_idempotency_service

    idempotency_service = get_idempotency_service()

    # Use asyncio.create_task to avoid blocking the response
    # In test environments, just call the method directly since there's no event loop
    import asyncio

    try:
        asyncio.create_task(
            idempotency_service.store_response_async(
                request_id, user_id, task_id, response_data, status_code
            )
        )
    except RuntimeError:
        # No event loop running (e.g., in tests), call synchronously
        # This is safe since store_response_async is designed to be non-blocking
        try:
            asyncio.run(
                idempotency_service.store_response_async(
                    request_id, user_id, task_id, response_data, status_code
                )
            )
        except RuntimeError:
            # If even asyncio.run fails, just skip the operation
            # This maintains backward compatibility for tests
            pass
