import logging
import uuid
import os

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


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
            user_id="1234567890",
            email="test@example.com",
            name="Test User"
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


# Extract idempotency key from headers
async def get_idempotency_key(request: Request) -> str | None:
    """Extract idempotency key from request headers."""
    return request.headers.get("Idempotency-Key")

#------------------------------------------------------------------------------------------------
# Idempotency check function (placeholder - integrate with IdempotencyService if needed)
async def check_idempotency(request_id: str) -> None:
    """Check for duplicate requests (placeholder - implement via IdempotencyService)."""
    # In production, query IdempotencyRepository here
    # For now, pass through (no-op)
    pass


# Store idempotency record (placeholder - integrate with IdempotencyService)
def store_idempotency(
    request_id: str, user_id: str, task_id: str, response_data: dict, status_code: int
) -> None:
    """Store idempotency record asynchronously (placeholder)."""
    # In production, use asyncio.create_task to call IdempotencyService
    # For now, no-op
    pass
