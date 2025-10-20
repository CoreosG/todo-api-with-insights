from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Base model for shared User attributes, ensuring validation per ADR-004
class UserBase(BaseModel):
    email: EmailStr = Field(
        ...,
        description="User's email address (must be valid format, used as unique identifier)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's display name (required, 1-100 characters)",
    )


# Model for creating a new user, inheriting from UserBase for reuse
class UserCreate(UserBase):
    pass  # No additional fields needed; inherits validation from UserBase


# Model for user responses, including computed/read-only fields from ADR-003
class UserResponse(UserBase):
    id: str = Field(
        ..., description="Unique user identifier (e.g., UUID or Cognito user ID)"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the user was created (Unix timestamp or ISO format)",
    )
    updated_at: datetime = Field(
        ..., description="Timestamp of the last update (Unix timestamp or ISO format)"
    )


# Optional: Model for updating a user (partial updates, excluding read-only fields)
class UserUpdate(BaseModel):
    email: EmailStr | None = Field(
        None, description="Updated email (optional, must be valid)"
    )
    name: str | None = Field(
        None, min_length=1, max_length=100, description="Updated name (optional)"
    )

    model_config = ConfigDict(extra="forbid")
