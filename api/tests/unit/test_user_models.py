from datetime import datetime, timezone  # Added 'timezone' to imports

import pytest
from pydantic import ValidationError

# Import user models
from src.models.user_models import UserCreate, UserResponse, UserUpdate


class TestUserModels:
    def test_user_create_valid(self) -> None:
        """Test creating a valid UserCreate model."""
        user = UserCreate.model_validate(
            {"email": "test@example.com", "name": "John Doe"}
        )
        assert user.email == "test@example.com"
        assert user.name == "John Doe"
        # Ensure serialization works (for API responses)
        data = user.model_dump()
        assert "email" in data and "name" in data

    def test_user_create_invalid_email(self) -> None:
        """Test UserCreate with invalid email raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate({"email": "invalid-email", "name": "John Doe"})
        assert "email" in str(exc_info.value)

    def test_user_create_missing_name(self) -> None:
        """Test UserCreate with missing name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate({"email": "test@example.com"})  # name is required
        assert "name" in str(exc_info.value)

    def test_user_create_name_too_long(self) -> None:
        """Test UserCreate with name exceeding max length raises ValidationError."""
        long_name = "A" * 101  # Exceeds 100 char limit
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate({"email": "test@example.com", "name": long_name})
        assert "name" in str(exc_info.value)

    def test_user_response_valid(self) -> None:
        """Test creating a valid UserResponse model."""
        now = datetime.now(timezone.utc)  # Fixed: Use timezone.utc for UTC
        user = UserResponse.model_validate(
            {
                "id": "user-123",
                "email": "test@example.com",
                "name": "John Doe",
                "created_at": now,
                "updated_at": now,
            }
        )
        assert user.id == "user-123"
        assert user.email == "test@example.com"
        assert user.created_at == now
        # Ensure serialization works
        data = user.model_dump()
        assert "id" in data and "created_at" in data

    def test_user_response_missing_id(self) -> None:
        """Test UserResponse with missing id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserResponse.model_validate(
                {
                    "email": "test@example.com",
                    "name": "John Doe",
                    "created_at": datetime.now(timezone.utc),  # Fixed: Use timezone.utc
                    "updated_at": datetime.now(timezone.utc),  # Fixed: Use timezone.utc
                }
            )
        assert "id" in str(exc_info.value)

    def test_user_update_partial(self) -> None:
        """Test UserUpdate with partial fields (only name updated)."""
        update = UserUpdate.model_validate({"name": "Jane Doe"})  # email is optional
        assert update.name == "Jane Doe"
        assert update.email is None
        # Ensure it serializes correctly for patches
        data = update.model_dump(exclude_unset=True)  # Only set fields
        assert "name" in data and "email" not in data

    def test_user_update_invalid_email(self) -> None:
        """Test UserUpdate with invalid email raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate.model_validate({"email": "invalid-email"})
        assert "email" in str(exc_info.value)

    def test_user_update_no_changes(self) -> None:
        """Test UserUpdate with no fields set (edge case)."""
        update = UserUpdate.model_validate({})  # No fields provided
        assert update.name is None
        assert update.email is None
        # Should serialize to empty dict for unset fields
        data = update.model_dump(exclude_unset=True)
        assert data == {}

    def test_model_serialization_json(self) -> None:
        """Test that models serialize to JSON correctly (for API responses)."""
        user = UserCreate.model_validate(
            {"email": "test@example.com", "name": "John Doe"}
        )
        json_data = user.model_dump_json()
        assert "test@example.com" in json_data
        assert "John Doe" in json_data

    def test_model_config_extra_forbid(self) -> None:
        """Test that extra fields are forbidden in UserUpdate (per Config)."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate.model_validate(
                {"email": "test@example.com", "extra_field": "not allowed"}
            )
        assert "extra" in str(exc_info.value).lower()
