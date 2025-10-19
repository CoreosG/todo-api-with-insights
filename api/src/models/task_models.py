from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# Enums for Task Status and Priority, directly derived from ADR-003 schema
class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


# Base model for shared Task attributes, ensuring validation per ADR-004
class TaskBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title (required, 1-200 characters)",
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Detailed task description (optional, up to 1000 characters)",
    )
    priority: Priority = Field(Priority.medium, description="Task priority level")
    category: str | None = Field(
        None,
        max_length=50,
        description="Task category or tag (optional, up to 50 characters)",
    )
    due_date: date | None = Field(
        None, description="Due date in YYYY-MM-DD format (optional)"
    )


# Model for creating a new task, inheriting from TaskBase for reuse
class TaskCreate(TaskBase):
    pass  # No additional fields needed; inherits validation from TaskBase


# Model for task responses, including computed/read-only fields from ADR-003
class TaskResponse(TaskBase):
    id: str = Field(
        ..., description="Unique task identifier (e.g., UUID or generated key)"
    )
    status: TaskStatus = Field(TaskStatus.pending, description="Current task status")
    created_at: datetime = Field(
        ...,
        description="Timestamp when the task was created (Unix timestamp or ISO format)",
    )
    updated_at: datetime = Field(
        ..., description="Timestamp of the last update (Unix timestamp or ISO format)"
    )
    completed_at: datetime | None = Field(
        None,
        description="Timestamp when the task was completed (null if not completed)",
    )


# Optional: Model for updating a task (partial updates, excluding read-only fields)
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    category: Optional[str] = Field(None, max_length=50)
    due_date: Optional[date] = None

    model_config = ConfigDict(extra="forbid")
