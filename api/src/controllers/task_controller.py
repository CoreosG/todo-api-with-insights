from fastapi import APIRouter, HTTPException, Request, status

from ..dependecies import (
    check_idempotency,
    get_request_id,
    get_user_context,
    store_idempotency,
)
from ..models.task_models import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    request: Request,
) -> TaskResponse:
    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    request_id = await get_request_id(request, user_context.user_id)
    from ..utils.dependency_injection import get_task_service

    task_service = get_task_service()
    await check_idempotency(request_id=request_id)  # Idempotency check
    try:
        response = await task_service.create_task(user_context.user_id, task)
        store_idempotency(
            request_id, user_context.user_id, response.id, {"status": "created"}, 201
        )  # Async store
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/tasks", response_model=list[TaskResponse])
async def get_tasks(
    request: Request,
) -> list[TaskResponse]:
    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    from ..utils.dependency_injection import get_task_service

    task_service = get_task_service()
    return await task_service.get_tasks(user_context.user_id)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    request: Request,
) -> TaskResponse:
    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    from ..utils.dependency_injection import get_task_service

    task_service = get_task_service()
    task = await task_service.get_task(user_context.user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    updates: TaskUpdate,
    request: Request,
) -> TaskResponse:
    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    request_id = await get_request_id(request, user_context.user_id)
    from ..utils.dependency_injection import get_task_service

    task_service = get_task_service()
    await check_idempotency(request_id=request_id)
    try:
        response = await task_service.update_task(
            user_context.user_id, task_id, updates
        )
        store_idempotency(
            request_id, user_context.user_id, response.id, {"status": "updated"}, 200
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    request: Request,
) -> None:
    # Get user context and ensure user exists (create if needed)
    user_context = await get_user_context(request)
    from ..utils.dependency_injection import get_user_service

    user_service = get_user_service()
    await user_service.create_or_get_user(
        user_context.user_id, user_context.email, user_context.name
    )

    request_id = await get_request_id(request, user_context.user_id)
    from ..utils.dependency_injection import get_task_service

    task_service = get_task_service()
    await check_idempotency(request_id=request_id)
    await task_service.delete_task(user_context.user_id, task_id)
    store_idempotency(
        request_id, user_context.user_id, task_id, {"status": "deleted"}, 204
    )
