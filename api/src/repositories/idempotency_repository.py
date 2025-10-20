import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from ..models.idempotency_models import IdempotencyCreate, IdempotencyResponse

logger = logging.getLogger(__name__)


class IdempotencyRepository:
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

    async def create_idempotency(
        self, idempotency: IdempotencyCreate
    ) -> IdempotencyResponse:
        """Create an idempotency record in DynamoDB per ADR-003 schema."""
        pk = f"IDEMPOTENCY#{idempotency.request_id}"
        sk = "METADATA"
        item = {
            "PK": pk,
            "SK": sk,
            "response_data": idempotency.response_data,
            "target_task_pk": idempotency.target_task_pk,
            "target_task_sk": idempotency.target_task_sk,
            "http_status_code": idempotency.http_status_code,
            "expiration_timestamp": idempotency.expiration_timestamp,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        try:
            self.table.put_item(Item=item)
            logger.info(f"Idempotency record created: {idempotency.request_id}")
            return IdempotencyResponse(
                **idempotency.model_dump(),
                created_at=datetime.now(timezone.utc),
            )
        except ClientError as e:
            logger.error(f"Error creating idempotency record: {e}")
            raise

    async def get_idempotency(self, request_id: str) -> IdempotencyResponse | None:
        """Fetch an idempotency record by request_id."""
        pk = f"IDEMPOTENCY#{request_id}"
        sk = "METADATA"
        try:
            response = self.table.get_item(Key={"PK": pk, "SK": sk})
            if "Item" not in response:
                return None
            item = response["Item"]
            return self._item_to_idempotency_response(item)
        except ClientError as e:
            logger.error(f"Error fetching idempotency record: {e}")
            raise

    async def delete_idempotency(self, request_id: str) -> None:
        """Delete an idempotency record (e.g., after TTL or manual cleanup)."""
        pk = f"IDEMPOTENCY#{request_id}"
        sk = "METADATA"
        try:
            self.table.delete_item(Key={"PK": pk, "SK": sk})
            logger.info(f"Idempotency record deleted: {request_id}")
        except ClientError as e:
            logger.error(f"Error deleting idempotency record: {e}")
            raise

    def _item_to_idempotency_response(self, item: dict) -> IdempotencyResponse:
        """Helper to convert DynamoDB item to IdempotencyResponse."""
        return IdempotencyResponse(
            request_id=item["PK"].split("#")[1],  # Extract request_id from PK
            response_data=item["response_data"],
            target_task_pk=item["target_task_pk"],
            target_task_sk=item["target_task_sk"],
            http_status_code=item["http_status_code"],
            expiration_timestamp=item["expiration_timestamp"],
            created_at=datetime.fromtimestamp(int(item["created_at"]), tz=timezone.utc),
        )
