"""
Helper functions for generating API Gateway events for integration testing.

These functions create realistic API Gateway HTTP API v2.0 event payloads
that can be used to test the complete Lambda execution flow.
"""

import json
import uuid
from typing import Any


def create_base_api_gateway_event(
    method: str,
    path: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a base API Gateway HTTP API v2.0 event structure.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: Request path (e.g., "/api/v1/tasks")
        body: Request body as JSON string
        headers: HTTP headers dictionary
        query_params: Query parameters dictionary

    Returns:
        API Gateway event dictionary
    """
    # Ensure path starts with /
    if not path.startswith("/"):
        path = f"/{path}"

    event = {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "requestContext": {
            "authorizer": {"jwt": {"claims": {}, "scopes": ["read", "write"]}},
            "requestId": str(uuid.uuid4()),
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test-client/1.0",
            },
            "stage": "$default",
        },
        "headers": {"content-type": "application/json", **(headers or {})},
        "isBase64Encoded": False,
    }

    # Add body if provided
    if body:
        event["body"] = body

    # Add query string parameters if provided
    if query_params:
        event["queryStringParameters"] = query_params

    return event


def create_authenticated_api_gateway_event(
    method: str,
    path: str,
    user_id: str,
    email: str,
    name: str | None = None,
    body: str | None = None,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Create an authenticated API Gateway event with JWT claims.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: Request path (e.g., "/api/v1/tasks")
        user_id: Cognito user ID (sub claim)
        email: User email address
        name: User display name (optional)
        body: Request body as JSON string
        headers: HTTP headers dictionary
        query_params: Query parameters dictionary
        idempotency_key: Idempotency key for request deduplication

    Returns:
        API Gateway event dictionary with authentication
    """
    event = create_base_api_gateway_event(method, path, body, headers, query_params)

    # Add JWT claims to the authorizer
    claims = {"sub": user_id, "email": email, "cognito:username": email}

    if name:
        claims["name"] = name
    else:
        claims["name"] = email  # Use email as fallback

    event["requestContext"]["authorizer"]["jwt"]["claims"] = claims

    # Add idempotency key to headers if provided
    if idempotency_key:
        event["headers"]["Idempotency-Key"] = idempotency_key

    return event


def create_unauthenticated_api_gateway_event(
    method: str,
    path: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create an unauthenticated API Gateway event (no JWT claims).

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: Request path (e.g., "/api/v1/tasks")
        body: Request body as JSON string
        headers: HTTP headers dictionary
        query_params: Query parameters dictionary

    Returns:
        API Gateway event dictionary without authentication
    """
    event = create_base_api_gateway_event(method, path, body, headers, query_params)

    # Remove authorizer claims for unauthenticated requests
    event["requestContext"]["authorizer"]["jwt"]["claims"] = {}

    return event


def create_task_create_event(
    user_id: str,
    email: str,
    name: str | None = None,
    title: str = "Test Task",
    description: str = "Test Description",
    priority: str = "medium",
    category: str = "test",
    due_date: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Create an API Gateway event for task creation.

    Args:
        user_id: Cognito user ID
        email: User email
        name: User display name
        title: Task title
        description: Task description
        priority: Task priority (low, medium, high)
        category: Task category
        due_date: Task due date in ISO format
        idempotency_key: Idempotency key

    Returns:
        API Gateway event for POST /api/v1/tasks
    """
    task_data = {
        "title": title,
        "description": description,
        "priority": priority,
        "category": category,
    }

    if due_date:
        task_data["due_date"] = due_date

    body = json.dumps(task_data)

    return create_authenticated_api_gateway_event(
        method="POST",
        path="/api/v1/tasks",
        user_id=user_id,
        email=email,
        name=name,
        body=body,
        idempotency_key=idempotency_key,
    )


def create_task_get_event(
    user_id: str,
    email: str,
    name: str | None = None,
    task_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Create an API Gateway event for task retrieval.

    Args:
        user_id: Cognito user ID
        email: User email
        name: User display name
        task_id: Specific task ID to retrieve (None for all tasks)
        idempotency_key: Idempotency key

    Returns:
        API Gateway event for GET /api/v1/tasks or GET /api/v1/tasks/{task_id}
    """
    path = "/api/v1/tasks"
    if task_id:
        path = f"/api/v1/tasks/{task_id}"

    return create_authenticated_api_gateway_event(
        method="GET",
        path=path,
        user_id=user_id,
        email=email,
        name=name,
        idempotency_key=idempotency_key,
    )


def create_task_update_event(
    user_id: str,
    email: str,
    name: str | None = None,
    task_id: str = "test-task-id",
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Create an API Gateway event for task update.

    Args:
        user_id: Cognito user ID
        email: User email
        name: User display name
        task_id: Task ID to update
        title: Updated task title
        description: Updated task description
        priority: Updated task priority
        category: Updated task category
        status: Updated task status
        due_date: Updated task due date
        idempotency_key: Idempotency key

    Returns:
        API Gateway event for PUT /api/v1/tasks/{task_id}
    """
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if priority is not None:
        update_data["priority"] = priority
    if category is not None:
        update_data["category"] = category
    if status is not None:
        update_data["status"] = status
    if due_date is not None:
        update_data["due_date"] = due_date

    body = json.dumps(update_data)

    return create_authenticated_api_gateway_event(
        method="PUT",
        path=f"/api/v1/tasks/{task_id}",
        user_id=user_id,
        email=email,
        name=name,
        body=body,
        idempotency_key=idempotency_key,
    )


def create_task_delete_event(
    user_id: str,
    email: str,
    name: str | None = None,
    task_id: str = "test-task-id",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Create an API Gateway event for task deletion.

    Args:
        user_id: Cognito user ID
        email: User email
        name: User display name
        task_id: Task ID to delete
        idempotency_key: Idempotency key

    Returns:
        API Gateway event for DELETE /api/v1/tasks/{task_id}
    """
    return create_authenticated_api_gateway_event(
        method="DELETE",
        path=f"/api/v1/tasks/{task_id}",
        user_id=user_id,
        email=email,
        name=name,
        idempotency_key=idempotency_key,
    )


def create_user_get_event(
    user_id: str,
    email: str,
    name: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Create an API Gateway event for user retrieval.

    Args:
        user_id: Cognito user ID
        email: User email
        name: User display name
        idempotency_key: Idempotency key

    Returns:
        API Gateway event for GET /api/v1/users/{user_id}
    """
    return create_authenticated_api_gateway_event(
        method="GET",
        path=f"/api/v1/users/{user_id}",
        user_id=user_id,
        email=email,
        name=name,
        idempotency_key=idempotency_key,
    )


def create_health_check_event() -> dict[str, Any]:
    """
    Create an API Gateway event for health check endpoint.

    Returns:
        API Gateway event for GET /health
    """
    return create_base_api_gateway_event(
        method="GET", path="/health", headers={"content-type": "application/json"}
    )
