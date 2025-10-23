import json
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients
firehose_client = boto3.client("firehose")
dynamodb_client = boto3.client("dynamodb")

# Environment variables
FIREHOSE_STREAM_NAME = os.environ.get("FIREHOSE_STREAM_NAME")
BRONZE_BUCKET = os.environ.get("BRONZE_BUCKET")
TABLE_NAME = os.environ.get("TABLE_NAME")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Process DynamoDB Streams events and send to Firehose for S3 delivery.

    Args:
        event: DynamoDB Streams event
        context: Lambda context

    Returns:
        Dict containing processing results
    """
    try:
        logger.info(
            "Processing DynamoDB Streams event",
            extra={
                "event_source": "dynamodb",
                "record_count": len(event.get("Records", [])),
            },
        )

        # Process each record in the batch
        processed_records = []
        failed_records = []

        for record in event.get("Records", []):
            try:
                processed_record = _process_dynamodb_record(record)
                if processed_record:
                    processed_records.append(processed_record)
            except Exception as e:
                logger.error(
                    f"Failed to process record: {e}",
                    extra={
                        "record_id": record.get("dynamodb", {}).get("SequenceNumber"),
                        "error": str(e),
                    },
                )
                failed_records.append({"record": record, "error": str(e)})

        # Send processed records to Firehose
        if processed_records:
            _send_to_firehose(processed_records)

        # Log metrics
        metrics.add_metric(
            name="RecordsProcessed", unit="Count", value=len(processed_records)
        )
        metrics.add_metric(
            name="RecordsFailed", unit="Count", value=len(failed_records)
        )

        logger.info(
            "CDC processing completed",
            extra={
                "processed_count": len(processed_records),
                "failed_count": len(failed_records),
            },
        )

        return {
            "statusCode": 200,
            "processedRecords": len(processed_records),
            "failedRecords": len(failed_records),
        }

    except Exception as e:
        logger.error(f"CDC processing failed: {e}")
        metrics.add_metric(name="ProcessingErrors", unit="Count", value=1)
        raise


def _process_dynamodb_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single DynamoDB Streams record.

    Args:
        record: DynamoDB Streams record

    Returns:
        Processed record for Firehose
    """
    try:
        # Extract record metadata
        event_name = record.get("eventName")
        dynamodb_data = record.get("dynamodb", {})

        # Skip REMOVE events for now (we can add them later if needed)
        if event_name == "REMOVE":
            logger.info(
                "Skipping REMOVE event",
                extra={
                    "event_name": event_name,
                    "sequence_number": dynamodb_data.get("SequenceNumber"),
                },
            )
            return {}

        # Extract the actual data
        if event_name in ["INSERT", "MODIFY"]:
            # Get the new image (after the change)
            image_data = dynamodb_data.get("NewImage", {})
        else:
            # For other events, use the old image
            image_data = dynamodb_data.get("OldImage", {})

        if not image_data:
            logger.warning(
                "No image data found in record",
                extra={
                    "event_name": event_name,
                    "sequence_number": dynamodb_data.get("SequenceNumber"),
                },
            )
            return {}

        # Convert DynamoDB format to regular JSON
        converted_data = _convert_dynamodb_to_json(image_data)

        # Add metadata
        processed_record = {
            "event_name": event_name,
            "event_time": record.get("eventTime"),
            "sequence_number": dynamodb_data.get("SequenceNumber"),
            "table_name": TABLE_NAME,
            "processed_at": datetime.utcnow().isoformat(),
            "data": converted_data,
        }

        # Add partition key for better S3 organization
        if "PK" in converted_data:
            processed_record["partition_key"] = converted_data["PK"]

        return processed_record

    except Exception as e:
        logger.error(f"Failed to process DynamoDB record: {e}")
        raise


def _convert_dynamodb_to_json(dynamodb_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert DynamoDB item format to regular JSON.

    Args:
        dynamodb_item: DynamoDB item in AWS format

    Returns:
        Converted JSON object
    """
    converted = {}

    for key, value in dynamodb_item.items():
        if "S" in value:
            # String value
            converted[key] = value["S"]
        elif "N" in value:
            # Number value
            try:
                # Try to convert to int first, then float
                if "." in value["N"]:
                    converted[key] = float(value["N"])
                else:
                    converted[key] = int(value["N"])
            except ValueError:
                # If conversion fails, keep as string
                converted[key] = value["N"]
        elif "BOOL" in value:
            # Boolean value
            converted[key] = value["BOOL"]
        elif "NULL" in value:
            # Null value
            converted[key] = None
        elif "L" in value:
            # List value
            converted[key] = [
                _convert_dynamodb_to_json({"item": item})["item"] for item in value["L"]
            ]
        elif "M" in value:
            # Map value
            converted[key] = _convert_dynamodb_to_json(value["M"])
        elif "SS" in value:
            # String set
            converted[key] = value["SS"]
        elif "NS" in value:
            # Number set
            converted[key] = [float(n) if "." in n else int(n) for n in value["NS"]]
        elif "BS" in value:
            # Binary set
            converted[key] = value["BS"]
        else:
            # Unknown type, keep as is
            converted[key] = value

    return converted


def _send_to_firehose(records: List[Dict[str, Any]]) -> None:
    """
    Send processed records to Firehose delivery stream.

    Args:
        records: List of processed records
    """
    try:
        # Prepare records for Firehose
        firehose_records = []

        for record in records:
            # Convert record to JSON string
            record_data = json.dumps(record) + "\n"
            firehose_records.append({"Data": record_data.encode("utf-8")})

        # Send to Firehose in batches (max 500 records per batch)
        batch_size = 500
        for i in range(0, len(firehose_records), batch_size):
            batch = firehose_records[i : i + batch_size]

            response = firehose_client.put_record_batch(
                DeliveryStreamName=FIREHOSE_STREAM_NAME, Records=batch
            )

            # Check for failed records
            if response.get("FailedPutCount", 0) > 0:
                logger.warning(
                    "Some records failed to send to Firehose",
                    extra={
                        "failed_count": response["FailedPutCount"],
                        "total_count": len(batch),
                    },
                )

                # Log failed records for debugging
                for i, result in enumerate(response.get("RequestResponses", [])):
                    if "ErrorCode" in result:
                        logger.error(
                            f"Firehose error for record {i}: {result['ErrorCode']} - {result.get('ErrorMessage', '')}"
                        )
            else:
                logger.info(f"Successfully sent {len(batch)} records to Firehose")

    except Exception as e:
        logger.error(f"Failed to send records to Firehose: {e}")
        raise
