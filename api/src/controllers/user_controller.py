from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..dependecies import (
    check_idempotency,
    get_request_id,
    get_user_context,
    store_idempotency,
)
from ..models.user_models import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    request: Request,
    idempotency_key: str = Header(
        ..., description="Unique identifier for request deduplication"
    ),
) -> UserResponse | JSONResponse:
    # Validate idempotency key
    if not idempotency_key:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key header is required"
        )

    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    user_context = await get_user_context(request)
    user_id = user_context.user_id

    request_id = await get_request_id(request, user_context.user_id, idempotency_key)

    # Check for duplicate requests and return cached response if found
    cached_response = await check_idempotency(request_id=request_id)
    if cached_response:
        # Return cached response for duplicate requests
        import json

        return JSONResponse(
            status_code=cached_response.http_status_code,
            content=json.loads(cached_response.response_data),
        )

    try:
        response = await user_service.create_user(user_id, user)
        store_idempotency(request_id, user_id, user_id, {"status": "created"}, 201)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/users", response_model=UserResponse)
async def get_user(
    request: Request,
) -> UserResponse:
    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    user = await user_service.get_user(user_context.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users", response_model=UserResponse)
async def update_user(
    updates: UserUpdate,
    request: Request,
    idempotency_key: str = Header(
        ..., description="Unique identifier for request deduplication"
    ),
) -> UserResponse | JSONResponse:
    # Validate idempotency key
    if not idempotency_key:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key header is required"
        )

    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    request_id = await get_request_id(request, user_context.user_id, idempotency_key)

    # Check for duplicate requests and return cached response if found
    cached_response = await check_idempotency(request_id=request_id)
    if cached_response:
        # Return cached response for duplicate requests
        import json

        return JSONResponse(
            status_code=cached_response.http_status_code,
            content=json.loads(cached_response.response_data),
        )

    try:
        response = await user_service.update_user(user_context.user_id, updates)
        store_idempotency(
            request_id,
            user_context.user_id,
            user_context.user_id,
            {"status": "updated"},
            200,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/users", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    idempotency_key: str = Header(
        ..., description="Unique identifier for request deduplication"
    ),
) -> None:
    # Validate idempotency key
    if not idempotency_key:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key header is required"
        )

    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    request_id = await get_request_id(request, user_context.user_id, idempotency_key)

    # For delete operations, we don't return cached responses to avoid 204 response body issues
    # Check for duplicate requests but don't return cached response
    cached_response = await check_idempotency(request_id=request_id)
    if cached_response:
        # For delete operations, we just proceed with the deletion even if cached
        # This maintains idempotency but avoids FastAPI 204 response body restrictions
        pass

    await user_service.delete_user(user_context.user_id)
    store_idempotency(
        request_id,
        user_context.user_id,
        user_context.user_id,
        {"status": "deleted"},
        204,
    )
    return None
