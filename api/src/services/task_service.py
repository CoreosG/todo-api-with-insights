import logging

from ..models.task_models import TaskCreate, TaskResponse, TaskStatus, TaskUpdate
from ..repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo

    async def create_task(self, user_id: str, task: TaskCreate) -> TaskResponse:
        """Create a task with business validation only."""
        response = await self.task_repo.create_task(user_id, task)
        return response

    async def get_task(self, user_id: str, task_id: str) -> TaskResponse | None:
        """Retrieve a single task."""
        return await self.task_repo.get_task(user_id, task_id)

    async def get_tasks(self, user_id: str) -> list[TaskResponse]:
        """Retrieve all tasks for a user."""
        return await self.task_repo.get_tasks(user_id)

    async def get_tasks_by_status(
        self, user_id: str, status: TaskStatus
    ) -> list[TaskResponse]:
        """Retrieve tasks by status."""
        return await self.task_repo.get_tasks_by_status(user_id, status)

    async def update_task(
        self, user_id: str, task_id: str, updates: TaskUpdate
    ) -> TaskResponse:
        """Update a task with business validation (e.g., status transitions)."""
        # Business logic: Validate status transitions (e.g., can't go from completed to pending)
        if updates.status is not None:
            current_task = await self.task_repo.get_task(user_id, task_id)
            if (
                current_task
                and current_task.status == TaskStatus.completed
                and updates.status != TaskStatus.completed
            ):
                raise ValueError("Cannot change status from completed to another state")

        # Update via Repository
        update_dict = updates.model_dump(exclude_unset=True)
        return await self.task_repo.update_task(user_id, task_id, update_dict)

    async def delete_task(self, user_id: str, task_id: str) -> None:
        """Delete a task."""
        await self.task_repo.delete_task(user_id, task_id)
