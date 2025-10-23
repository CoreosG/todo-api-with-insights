"""Unit tests for CDC handler Lambda function."""

import os
from unittest.mock import Mock, patch

# Set environment variable to disable metrics before importing
os.environ["POWERTOOLS_METRICS_NAMESPACE"] = "TestNamespace"

from lambda_cdc.src.cdc_handler import (
    _convert_dynamodb_to_json,
    _process_dynamodb_record,
    _send_to_firehose,
    lambda_handler,
)


class TestCDCHandler:
    """Test cases for CDC handler Lambda function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "SequenceNumber": "123456789",
                        "Keys": {"PK": {"S": "USER#123"}, "SK": {"S": "PROFILE"}},
                        "NewImage": {
                            "PK": {"S": "USER#123"},
                            "SK": {"S": "PROFILE"},
                            "user_id": {"S": "123"},
                            "email": {"S": "test@example.com"},
                            "name": {"S": "Test User"},
                            "created_at": {"S": "2024-01-01T00:00:00Z"},
                        },
                    },
                }
            ]
        }

    @patch.dict(
        "os.environ",
        {
            "FIREHOSE_STREAM_NAME": "test-stream",
            "BRONZE_BUCKET": "test-bucket",
            "TABLE_NAME": "test-table",
        },
    )
    @patch("lambda_cdc.src.cdc_handler._send_to_firehose")
    def test_lambda_handler_success(self, mock_send_to_firehose):
        """Test successful Lambda handler execution."""
        result = lambda_handler(self.sample_event, Mock())

        assert result["statusCode"] == 200
        assert result["processedRecords"] == 1
        assert result["failedRecords"] == 0
        mock_send_to_firehose.assert_called_once()

    @patch.dict(
        "os.environ",
        {
            "FIREHOSE_STREAM_NAME": "test-stream",
            "BRONZE_BUCKET": "test-bucket",
            "TABLE_NAME": "test-table",
        },
    )
    def test_lambda_handler_empty_records(self):
        """Test Lambda handler with empty records."""
        event = {"Records": []}

        result = lambda_handler(event, Mock())

        assert result["statusCode"] == 200
        assert result["processedRecords"] == 0
        assert result["failedRecords"] == 0

    @patch.dict(
        "os.environ",
        {
            "FIREHOSE_STREAM_NAME": "test-stream",
            "BRONZE_BUCKET": "test-bucket",
            "TABLE_NAME": "test-table",
        },
    )
    def test_lambda_handler_invalid_record(self):
        """Test Lambda handler with invalid record."""
        invalid_event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "SequenceNumber": "123456789",
                        "Keys": {"PK": {"S": "USER#123"}},
                        # Missing NewImage
                    },
                }
            ]
        }

        result = lambda_handler(invalid_event, Mock())

        assert result["statusCode"] == 200
        assert result["processedRecords"] == 0
        assert result["failedRecords"] == 0  # Changed from 1 to 0 since function now returns empty dict instead of raising exception

    def test_process_dynamodb_record_insert(self):
        """Test processing INSERT DynamoDB record."""
        record = {
            "eventName": "INSERT",
            "dynamodb": {
                "SequenceNumber": "123456789",
                "Keys": {"PK": {"S": "USER#123"}, "SK": {"S": "PROFILE"}},
                "NewImage": {
                    "PK": {"S": "USER#123"},
                    "SK": {"S": "PROFILE"},
                    "user_id": {"S": "123"},
                    "email": {"S": "test@example.com"},
                },
            },
        }

        result = _process_dynamodb_record(record)

        assert result is not None
        assert result["event_name"] == "INSERT"
        assert result["sequence_number"] == "123456789"
        assert result["data"]["user_id"] == "123"
        assert result["data"]["email"] == "test@example.com"

    def test_process_dynamodb_record_modify(self):
        """Test processing MODIFY DynamoDB record."""
        record = {
            "eventName": "MODIFY",
            "dynamodb": {
                "SequenceNumber": "123456790",
                "Keys": {"PK": {"S": "USER#123"}, "SK": {"S": "PROFILE"}},
                "OldImage": {
                    "PK": {"S": "USER#123"},
                    "SK": {"S": "PROFILE"},
                    "user_id": {"S": "123"},
                    "email": {"S": "old@example.com"},
                },
                "NewImage": {
                    "PK": {"S": "USER#123"},
                    "SK": {"S": "PROFILE"},
                    "user_id": {"S": "123"},
                    "email": {"S": "new@example.com"},
                },
            },
        }

        result = _process_dynamodb_record(record)

        assert result is not None
        assert result["event_name"] == "MODIFY"
        assert result["sequence_number"] == "123456790"
        assert result["data"]["email"] == "new@example.com"

    def test_process_dynamodb_record_remove(self):
        """Test processing REMOVE DynamoDB record."""
        record = {
            "eventName": "REMOVE",
            "dynamodb": {
                "SequenceNumber": "123456791",
                "Keys": {"PK": {"S": "USER#123"}, "SK": {"S": "PROFILE"}},
                "OldImage": {
                    "PK": {"S": "USER#123"},
                    "SK": {"S": "PROFILE"},
                    "user_id": {"S": "123"},
                    "email": {"S": "test@example.com"},
                },
            },
        }

        result = _process_dynamodb_record(record)

        assert result == {}  # Returns empty dict for REMOVE events

    def test_process_dynamodb_record_invalid_event(self):
        """Test processing invalid DynamoDB record."""
        record = {
            "eventName": "INVALID",
            "dynamodb": {
                "SequenceNumber": "123456792",
                "Keys": {"PK": {"S": "USER#123"}},
            },
        }

        result = _process_dynamodb_record(record)

        assert result == {}  # Returns empty dict for invalid events

    def test_convert_dynamodb_to_json_string(self):
        """Test converting DynamoDB string to JSON."""
        dynamodb_item = {
            "user_id": {"S": "123"},
            "email": {"S": "test@example.com"},
            "is_active": {"BOOL": True},
        }

        result = _convert_dynamodb_to_json(dynamodb_item)

        expected = {"user_id": "123", "email": "test@example.com", "is_active": True}
        assert result == expected

    def test_convert_dynamodb_to_json_number(self):
        """Test converting DynamoDB number to JSON."""
        dynamodb_item = {"age": {"N": "25"}, "score": {"N": "95.5"}}

        result = _convert_dynamodb_to_json(dynamodb_item)

        expected = {"age": 25, "score": 95.5}
        assert result == expected

    def test_convert_dynamodb_to_json_null(self):
        """Test converting DynamoDB null to JSON."""
        dynamodb_item = {"optional_field": {"NULL": True}}

        result = _convert_dynamodb_to_json(dynamodb_item)

        expected = {"optional_field": None}
        assert result == expected

    def test_convert_dynamodb_to_json_list(self):
        """Test converting DynamoDB list to JSON."""
        dynamodb_item = {"tags": {"L": [{"S": "urgent"}, {"S": "important"}]}}

        result = _convert_dynamodb_to_json(dynamodb_item)

        expected = {"tags": ["urgent", "important"]}
        assert result == expected

    def test_convert_dynamodb_to_json_map(self):
        """Test converting DynamoDB map to JSON."""
        dynamodb_item = {
            "address": {
                "M": {"street": {"S": "123 Main St"}, "city": {"S": "New York"}}
            }
        }

        result = _convert_dynamodb_to_json(dynamodb_item)

        expected = {"address": {"street": "123 Main St", "city": "New York"}}
        assert result == expected

    @patch("lambda_cdc.src.cdc_handler.firehose_client")
    def test_send_to_firehose_success(self, mock_firehose_client):
        """Test successful Firehose data sending."""
        mock_firehose_client.put_record_batch.return_value = {
            "FailedPutCount": 0,
            "RequestResponses": [{"RecordId": "test-record-id"}],
        }

        records = [
            {
                "event_name": "INSERT",
                "event_time": "2024-01-01T00:00:00Z",
                "data": {"user_id": "123"},
            }
        ]

        _send_to_firehose(records)

        mock_firehose_client.put_record_batch.assert_called_once()

    @patch("lambda_cdc.src.cdc_handler.firehose_client")
    def test_send_to_firehose_failure(self, mock_firehose_client):
        """Test Firehose data sending with failures."""
        mock_firehose_client.put_record_batch.return_value = {
            "FailedPutCount": 1,
            "RequestResponses": [{"RecordId": "test-record-id"}],
        }

        records = [
            {
                "event_name": "INSERT",
                "event_time": "2024-01-01T00:00:00Z",
                "data": {"user_id": "123"},
            }
        ]

        # Should not raise exception, just log the failure
        _send_to_firehose(records)

        mock_firehose_client.put_record_batch.assert_called_once()

    def test_send_to_firehose_empty_records(self):
        """Test Firehose data sending with empty records."""
        records = []

        # Should not call Firehose with empty records
        with patch("lambda_cdc.src.cdc_handler.firehose_client") as mock_firehose:
            _send_to_firehose(records)
            mock_firehose.put_record_batch.assert_not_called()
