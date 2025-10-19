import os
from ..repositories.idempotency_repository import IdempotencyRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from ..services.idempotency_service import IdempotencyService
from ..services.task_service import TaskService
from ..services.user_service import UserService


def _get_dynamodb_endpoint_url() -> str | None:
    """Get DynamoDB endpoint URL from environment variables."""
    use_local = os.getenv("USE_LOCAL_DYNAMODB", "false").lower() == "true"
    if use_local:
        return os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8000")
    return None  # Use AWS DynamoDB


# Repository factory functions (create new instances for each request)
def create_user_repo() -> UserRepository:
    return UserRepository(endpoint_url=_get_dynamodb_endpoint_url())


def create_task_repo() -> TaskRepository:
    return TaskRepository(endpoint_url=_get_dynamodb_endpoint_url())


def create_idempotency_repo() -> IdempotencyRepository:
    return IdempotencyRepository(endpoint_url=_get_dynamodb_endpoint_url())


# Service factory functions with dependency injection
def create_user_service() -> UserService:
    return UserService(user_repo=create_user_repo())


def create_task_service() -> TaskService:
    return TaskService(task_repo=create_task_repo())


def create_idempotency_service() -> IdempotencyService:
    return IdempotencyService(idempotency_repo=create_idempotency_repo())


# Repository instances for backward compatibility (used in tests)
user_repo = create_user_repo()
task_repo = create_task_repo()
idempotency_repo = create_idempotency_repo()


# Service instances for backward compatibility (used in tests)
user_service = create_user_service()
task_service = create_task_service()
idempotency_service = create_idempotency_service()


# Dependency functions for FastAPI (create new instances for each request)
def get_user_service() -> UserService:
    return create_user_service()


def get_task_service() -> TaskService:
    return create_task_service()


def get_idempotency_service() -> IdempotencyService:
    return create_idempotency_service()
