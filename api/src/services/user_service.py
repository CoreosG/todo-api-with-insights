import logging

from ..models.user_models import UserCreate, UserResponse, UserUpdate
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def create_or_get_user(
        self, user_id: str, email: str, name: str
    ) -> UserResponse:
        """Create user if not exists (auto-creation from API Gateway context), or return existing."""
        # Check if user exists
        existing = await self.user_repo.get_user(user_id)
        if existing:
            logger.info(f"User already exists: {user_id}")
            return existing  # Return existing user

        # Auto-create using API Gateway-provided data
        user_create = UserCreate(email=email, name=name)
        response = await self.user_repo.create_user(user_id, user_create)
        logger.info(f"User auto-created: {user_id}")
        return response

    async def create_user(self, user_id: str, user: UserCreate) -> UserResponse:
        """Explicit create for cases where full user data is provided (e.g., via request body)."""
        # Business logic: Check for existing user
        existing = await self.user_repo.get_user(user_id)
        if existing:
            raise ValueError(f"User with ID {user_id} already exists")

        # Create user via Repository
        response = await self.user_repo.create_user(user_id, user)
        logger.info(f"User created: {user_id}")
        return response

    async def get_user(self, user_id: str) -> UserResponse | None:
        """Retrieve a user."""
        return await self.user_repo.get_user(user_id)

    async def update_user(self, user_id: str, updates: UserUpdate) -> UserResponse:
        """Update a user with partial data and validation."""
        # Business logic: Pydantic handles email validation, no need for additional checks

        # Update via Repository
        update_dict = updates.model_dump(exclude_unset=True)
        return await self.user_repo.update_user(user_id, update_dict)

    async def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        await self.user_repo.delete_user(user_id)
        logger.info(f"User deleted: {user_id}")
