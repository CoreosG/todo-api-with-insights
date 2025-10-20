import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from ..models.task_models import Priority, TaskCreate, TaskResponse, TaskStatus

logger = logging.getLogger(__name__)


class TaskRepository:
    def __init__(
        self,
        table_name: str = "todo-app-data",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ):
        self.dynamodb = boto3.resource(
            "dynamodb", region_name=region, endpoint_url=endpoint_url
        )
        self.table = self.dynamodb.Table(table_name)

    async def create_task(self, user_id: str, task: TaskCreate) -> TaskResponse:
        """Create a new task in DynamoDB per ADR-003 schema."""
        task_id = f"task-{datetime.now(timezone.utc).timestamp()}"  # Use timezone-aware datetime
        pk = f"TASK#{user_id}"
        sk = f"TASK#{task_id}"
        item = {
            "PK": pk,
            "SK": sk,
            "GSI1PK": f"USER#{user_id}",  # For status queries
            "GSI1SK": f"STATUS#{task.status.value}#{task_id}",
            "GSI2PK": f"USER#{user_id}",  # For due_date queries
            "GSI2SK": f"DUEDATE#{task.due_date.isoformat() if task.due_date else 'none'}#{task_id}",
            "GSI3PK": f"USER#{user_id}",  # For priority queries
            "GSI3SK": f"PRIORITY#{task.priority.value}#{task_id}",
            "GSI4PK": f"USER#{user_id}",  # For category queries
            "GSI4SK": f"CATEGORY#{task.category or 'none'}#{task_id}",
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "category": task.category,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
            "completed_at": None,
        }
        try:
            self.table.put_item(Item=item)
            logger.info(f"Task created: {task_id} for user {user_id}")
            return TaskResponse(
                id=task_id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                category=task.category,
                due_date=task.due_date,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        except ClientError as e:
            logger.error(f"Error creating task: {e}")
            raise

    async def get_task(self, user_id: str, task_id: str) -> TaskResponse:
        """Fetch a single task by user_id and task_id."""
        pk = f"TASK#{user_id}"
        sk = f"TASK#{task_id}"
        try:
            response = self.table.get_item(Key={"PK": pk, "SK": sk})
            if "Item" not in response:
                raise ValueError(f"Task {task_id} not found for user {user_id}")
            item = response["Item"]
            return self._item_to_task_response(item)
        except ClientError as e:
            logger.error(f"Error fetching task: {e}")
            raise

    async def get_tasks(self, user_id: str) -> list[TaskResponse]:
        """Fetch all tasks for a user."""
        pk = f"TASK#{user_id}"
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": pk},
                ScanIndexForward=True,
            )
            return [self._item_to_task_response(item) for item in response["Items"]]
        except ClientError as e:
            logger.error(f"Error fetching tasks: {e}")
            raise

    async def get_tasks_by_status(
        self, user_id: str, status: TaskStatus
    ) -> list[TaskResponse]:
        """Query tasks by status via GSI1 per ADR-003."""
        gsi1pk = f"USER#{user_id}"
        gsi1sk = f"STATUS#{status.value}#"
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :gsi1pk AND begins_with(GSI1SK, :gsi1sk)",
                ExpressionAttributeValues={":gsi1pk": gsi1pk, ":gsi1sk": gsi1sk},
            )
            return [self._item_to_task_response(item) for item in response["Items"]]
        except ClientError as e:
            logger.error(f"Error querying tasks by status: {e}")
            raise

    async def get_tasks_by_due_date(
        self, user_id: str, due_date: str
    ) -> list[TaskResponse]:
        """Query tasks by due_date via GSI2."""
        gsi2pk = f"USER#{user_id}"
        gsi2sk_prefix = f"DUEDATE#{due_date}#"
        try:
            response = self.table.query(
                IndexName="GSI2",
                KeyConditionExpression="GSI2PK = :gsi2pk AND begins_with(GSI2SK, :gsi2sk_prefix)",
                ExpressionAttributeValues={
                    ":gsi2pk": gsi2pk,
                    ":gsi2sk_prefix": gsi2sk_prefix,
                },
            )
            return [self._item_to_task_response(item) for item in response["Items"]]
        except ClientError as e:
            logger.error(f"Error querying tasks by due_date: {e}")
            raise

    async def get_tasks_by_priority(
        self, user_id: str, priority: Priority
    ) -> list[TaskResponse]:
        """Query tasks by priority via GSI3 per ADR-003."""
        gsi3pk = f"USER#{user_id}"
        gsi3sk = f"PRIORITY#{priority.value}#"
        try:
            response = self.table.query(
                IndexName="GSI3",
                KeyConditionExpression="GSI3PK = :gsi3pk AND begins_with(GSI3SK, :gsi3sk)",
                ExpressionAttributeValues={":gsi3pk": gsi3pk, ":gsi3sk": gsi3sk},
            )
            return [self._item_to_task_response(item) for item in response["Items"]]
        except ClientError as e:
            logger.error(f"Error querying tasks by priority: {e}")
            raise

    async def get_tasks_by_category(
        self, user_id: str, category: str
    ) -> list[TaskResponse]:
        """Query tasks by category via GSI4 per ADR-003."""
        gsi4pk = f"USER#{user_id}"
        gsi4sk = f"CATEGORY#{category}#"
        try:
            response = self.table.query(
                IndexName="GSI4",
                KeyConditionExpression="GSI4PK = :gsi4pk AND begins_with(GSI4SK, :gsi4sk)",
                ExpressionAttributeValues={":gsi4pk": gsi4pk, ":gsi4sk": gsi4sk},
            )
            return [self._item_to_task_response(item) for item in response["Items"]]
        except ClientError as e:
            logger.error(f"Error querying tasks by category: {e}")
            raise

    async def get_overdue_tasks(self, user_id: str) -> list[TaskResponse]:
        """Query tasks that are overdue (due_date < today and status != completed) via GSI2."""
        gsi2pk = f"USER#{user_id}"
        gsi2sk = "DUEDATE#"  # This will need to be dynamic for date ranges
        try:
            response = self.table.query(
                IndexName="GSI2",
                KeyConditionExpression="GSI2PK = :gsi2pk AND begins_with(GSI2SK, :gsi2sk)",
                ExpressionAttributeValues={":gsi2pk": gsi2pk, ":gsi2sk": gsi2sk},
            )
            return [self._item_to_task_response(item) for item in response["Items"]]
        except ClientError as e:
            logger.error(f"Error querying overdue tasks: {e}")
            raise

    # Add similar methods for priority (GSI3), category (GSI4), etc., as needed

    async def update_task(
        self, user_id: str, task_id: str, updates: dict
    ) -> TaskResponse:
        """Update a task with partial data."""
        pk = f"TASK#{user_id}"
        sk = f"TASK#{task_id}"

        # Merge updates with current values to preserve unchanged fields
        merged_updates = {}
        for key, value in updates.items():
            if value is not None:  # Only update non-None values
                merged_updates[key] = value

        # Escape reserved keywords in DynamoDB expressions
        reserved_keywords = {
            "status",
            "name",
            "email",
        }  # Add other reserved keywords as needed
        expr_attr_names = {}
        expr_attr_values = {}
        update_expr_parts = []

        for key, value in merged_updates.items():
            # Handle special types that need conversion for DynamoDB
            if key == "due_date" and value is not None:
                # Convert datetime.date to ISO format string for DynamoDB
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif isinstance(value, str):
                    # If it's already a string, keep it as is
                    pass
                else:
                    # Convert other types to string
                    value = str(value)

            if key in reserved_keywords:
                # Use expression attribute name for reserved keywords
                attr_name = f"#{key}"
                expr_attr_names[attr_name] = key
                expr_attr_values[f":{key}"] = value
                update_expr_parts.append(f"{attr_name} = :{key}")
            else:
                expr_attr_values[f":{key}"] = value
                update_expr_parts.append(f"{key} = :{key}")

        # Add updated_at timestamp
        current_time = int(datetime.now(timezone.utc).timestamp())
        expr_attr_values[":updated_at"] = current_time
        update_expr_parts.append("updated_at = :updated_at")

        update_expr = "SET " + ", ".join(update_expr_parts)

        try:
            update_params = {
                "Key": {"PK": pk, "SK": sk},
                "UpdateExpression": update_expr,
                "ExpressionAttributeValues": expr_attr_values,
                "ConditionExpression": "attribute_exists(PK)",  # Only update existing items
            }

            # Add expression attribute names if any reserved keywords used
            if expr_attr_names:
                update_params["ExpressionAttributeNames"] = expr_attr_names

            self.table.update_item(**update_params)
            # Fetch and return updated task
            return await self.get_task(user_id, task_id)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(f"Task {task_id} not found for user {user_id}") from e
            logger.error(f"Error updating task: {e}")
            raise

    async def delete_task(self, user_id: str, task_id: str) -> None:
        """Delete a task."""
        pk = f"TASK#{user_id}"
        sk = f"TASK#{task_id}"
        try:
            self.table.delete_item(
                Key={"PK": pk, "SK": sk},
                ConditionExpression="attribute_exists(PK)",  # Only delete existing items
            )
            logger.info(f"Task deleted: {task_id} for user {user_id}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Re-raise as a more generic ClientError for non-existent items
                raise ClientError(
                    {
                        "Error": {
                            "Code": "ResourceNotFoundException",
                            "Message": f"Task {task_id} not found",
                        }
                    },
                    "DeleteItem",
                ) from e
            logger.error(f"Error deleting task: {e}")
            raise

    def _item_to_task_response(self, item: dict) -> TaskResponse:
        """Helper to convert DynamoDB item to TaskResponse."""

        # Helper function to convert Decimal to float for datetime operations
        def decimal_to_number(value: int | float | str | Decimal) -> float:
            if isinstance(value, Decimal):
                return float(value)
            elif isinstance(value, int):
                return float(value)
            return float(value)

        status_value = item.get("status", "pending")
        return TaskResponse(
            id=item["SK"].split("#")[1],  # Extract task_id from SK
            title=item["title"],
            description=item.get("description"),  # Use .get() for safety
            status=TaskStatus(
                status_value if status_value is not None else "pending"
            ),  # Default to 'pending' if missing
            priority=Priority(
                item.get("priority", "medium")
            ),  # Default to 'medium' if missing
            category=item.get("category"),  # Use .get() for safety
            due_date=(
                datetime.fromisoformat(item["due_date"])
                if item.get("due_date")
                else None
            ),
            created_at=datetime.fromtimestamp(
                decimal_to_number(item["created_at"]), tz=timezone.utc
            ),
            updated_at=datetime.fromtimestamp(
                decimal_to_number(item["updated_at"]), tz=timezone.utc
            ),
            completed_at=(
                datetime.fromtimestamp(
                    decimal_to_number(item["completed_at"]), tz=timezone.utc
                )
                if item.get("completed_at")
                else None
            ),
        )
