import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from ..models.user_models import UserCreate, UserResponse

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(
        self,
        table_name: str | None = None,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ):
        # Use environment variable if table_name not provided
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE_NAME", "todo-app-data")
        self.dynamodb = boto3.resource(
            "dynamodb", region_name=region, endpoint_url=endpoint_url
        )
        self.table = self.dynamodb.Table(self.table_name)

    async def create_user(self, user_id: str, user: UserCreate) -> UserResponse:
        """Create a new user in DynamoDB using Cognito-provided user_id per ADR-003 schema."""
        # Use provided user_id (from API Gateway/Cognito)
        pk = f"USER#{user_id}"
        sk = "METADATA"
        item = {
            "PK": pk,
            "SK": sk,
            "email": user.email,
            "name": user.name,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
        }
        try:
            self.table.put_item(Item=item)
            logger.info(f"User created: {user_id}")
            return UserResponse(
                id=user_id,  # Use provided ID
                **user.model_dump(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        except ClientError as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def get_user(self, user_id: str) -> UserResponse | None:
        """Fetch a user by user_id."""
        pk = f"USER#{user_id}"
        sk = "METADATA"
        try:
            response = self.table.get_item(Key={"PK": pk, "SK": sk})
            if "Item" not in response:
                return None
            item = response["Item"]
            return self._item_to_user_response(item)
        except ClientError as e:
            logger.error(f"Error fetching user: {e}")
            raise

    async def update_user(self, user_id: str, updates: dict) -> UserResponse:
        """Update a user with partial data."""
        pk = f"USER#{user_id}"
        sk = "METADATA"

        # Handle reserved keywords by using expression attribute names
        update_expr_parts = []
        expr_names = {}
        expr_values = {}

        for k, v in updates.items():
            if k == "name":
                # 'name' is a reserved keyword, use expression attribute name
                attr_name = "#n"
                expr_names[attr_name] = k
                update_expr_parts.append(f"{attr_name} = :{k}")
            else:
                update_expr_parts.append(f"{k} = :{k}")
            expr_values[f":{k}"] = v

        update_expr = "SET " + ", ".join(update_expr_parts)

        try:
            update_params = {
                "Key": {"PK": pk, "SK": sk},
                "UpdateExpression": update_expr,
                "ExpressionAttributeValues": expr_values,
                "ConditionExpression": "attribute_exists(PK)",  # Ensure item exists before updating
            }

            # Add expression attribute names if we have reserved keywords
            if expr_names:
                update_params["ExpressionAttributeNames"] = expr_names

            self.table.update_item(**update_params)
            return await self.get_user(user_id)  # type: ignore[return-value]
        except ClientError as e:
            logger.error(f"Error updating user: {e}")
            raise

    async def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        pk = f"USER#{user_id}"
        sk = "METADATA"
        try:
            self.table.delete_item(Key={"PK": pk, "SK": sk})
            logger.info(f"User deleted: {user_id}")
        except ClientError as e:
            logger.error(f"Error deleting user: {e}")
            raise

    def _item_to_user_response(self, item: dict) -> UserResponse:
        """Helper to convert DynamoDB item to UserResponse."""
        return UserResponse(
            id=item["PK"].split("#")[1],  # Extract user_id from PK
            email=item["email"],
            name=item["name"],
            created_at=datetime.fromtimestamp(int(item["created_at"]), tz=timezone.utc),
            updated_at=datetime.fromtimestamp(int(item["updated_at"]), tz=timezone.utc),
        )
