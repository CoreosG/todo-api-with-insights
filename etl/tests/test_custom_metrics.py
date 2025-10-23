"""Unit tests for custom metrics Lambda function."""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# Set environment variable to disable metrics before importing
os.environ["POWERTOOLS_METRICS_NAMESPACE"] = "TestNamespace"

from lambda_custom_metrics.src.custom_metrics import (
    _collect_system_metrics,
    _collect_task_metrics,
    _collect_user_metrics,
    _send_metrics_to_cloudwatch,
    lambda_handler,
)


class TestCustomMetrics:
    """Test cases for custom metrics Lambda function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_dynamodb_response = {
            "Items": [
                {
                    "PK": {"S": "USER#123"},
                    "SK": {"S": "PROFILE"},
                    "user_id": {"S": "123"},
                    "email": {"S": "test@example.com"},
                    "is_active": {"BOOL": True},
                    "created_at": {"S": "2024-01-01T00:00:00Z"},
                    "last_login": {"S": "2024-01-15T10:00:00Z"},
                }
            ],
            "Count": 1,
        }

    @patch.dict(
        "os.environ", {"TABLE_NAME": "test-table", "NAMESPACE": "TestApi/CustomMetrics"}
    )
    @patch("lambda_custom_metrics.src.custom_metrics._collect_user_metrics")
    @patch("lambda_custom_metrics.src.custom_metrics._collect_task_metrics")
    @patch("lambda_custom_metrics.src.custom_metrics._collect_system_metrics")
    @patch("lambda_custom_metrics.src.custom_metrics._send_metrics_to_cloudwatch")
    def test_lambda_handler_success(
        self,
        mock_send_metrics,
        mock_system_metrics,
        mock_task_metrics,
        mock_user_metrics,
    ):
        """Test successful Lambda handler execution."""
        mock_user_metrics.return_value = [{"MetricName": "TotalUsers", "Value": 100}]
        mock_task_metrics.return_value = [{"MetricName": "TotalTasks", "Value": 500}]
        mock_system_metrics.return_value = [{"MetricName": "TableSize", "Value": 1024}]

        result = lambda_handler({}, Mock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "Custom metrics collected successfully"
        assert body["user_metrics"] == 1
        assert body["task_metrics"] == 1
        assert body["system_metrics"] == 1

    @patch.dict(
        "os.environ", {"TABLE_NAME": "test-table", "NAMESPACE": "TestApi/CustomMetrics"}
    )
    def test_lambda_handler_exception(self):
        """Test Lambda handler with exception."""
        with patch(
            "lambda_custom_metrics.src.custom_metrics._collect_user_metrics"
        ) as mock_user:
            mock_user.side_effect = Exception("Test error")

            with pytest.raises(Exception):
                lambda_handler({}, Mock())

    @patch("lambda_custom_metrics.src.custom_metrics.dynamodb_client")
    def test_collect_user_metrics_success(self, mock_dynamodb):
        """Test successful user metrics collection."""
        # Mock all the different scan calls
        mock_dynamodb.scan.side_effect = [
            {"Count": 2},  # Total users
            {"Count": 0},  # Active users (no last_login field in current schema)
            {"Count": 0},  # Verified users (no verification_status field in current schema)
        ]

        result = _collect_user_metrics()

        assert len(result) == 4  # TotalUsers, ActiveUsers, VerifiedUsers, UserVerificationRate
        assert any(
            metric["MetricName"] == "TotalUsers" and metric["Value"] == 2
            for metric in result
        )
        assert any(
            metric["MetricName"] == "ActiveUsers" and metric["Value"] == 0  # No last_login field in current schema
            for metric in result
        )
        assert any(
            metric["MetricName"] == "VerifiedUsers" and metric["Value"] == 0  # No verification_status field in current schema
            for metric in result
        )

    @patch("lambda_custom_metrics.src.custom_metrics.dynamodb_client")
    def test_collect_user_metrics_empty(self, mock_dynamodb):
        """Test user metrics collection with empty results."""
        mock_dynamodb.scan.return_value = {"Items": [], "Count": 0}

        result = _collect_user_metrics()

        assert len(result) == 4  # TotalUsers, ActiveUsers, VerifiedUsers, UserVerificationRate
        assert all(metric["Value"] == 0 for metric in result)

    @patch("lambda_custom_metrics.src.custom_metrics.dynamodb_client")
    def test_collect_task_metrics_success(self, mock_dynamodb):
        """Test successful task metrics collection."""
        # Mock all the different scan calls
        mock_dynamodb.scan.side_effect = [
            {"Count": 2},  # Total tasks
            {"Count": 1},  # Completed tasks
            {"Count": 1},  # Pending tasks
            {"Count": 0},  # In-progress tasks
            {"Count": 1},  # High priority tasks
        ]

        result = _collect_task_metrics()

        assert (
            len(result) == 6
        )  # TotalTasks, CompletedTasks, PendingTasks, InProgressTasks, HighPriorityTasks, TaskCompletionRate
        assert any(
            metric["MetricName"] == "TotalTasks" and metric["Value"] == 2
            for metric in result
        )
        assert any(
            metric["MetricName"] == "CompletedTasks" and metric["Value"] == 1
            for metric in result
        )
        assert any(
            metric["MetricName"] == "PendingTasks" and metric["Value"] == 1
            for metric in result
        )

    @patch("lambda_custom_metrics.src.custom_metrics.dynamodb_client")
    def test_collect_task_metrics_empty(self, mock_dynamodb):
        """Test task metrics collection with empty results."""
        mock_dynamodb.scan.return_value = {"Items": [], "Count": 0}

        result = _collect_task_metrics()

        assert len(result) == 6  # TotalTasks, CompletedTasks, PendingTasks, InProgressTasks, HighPriorityTasks, TaskCompletionRate
        assert all(metric["Value"] == 0 for metric in result)

    @patch("lambda_custom_metrics.src.custom_metrics.dynamodb_client")
    def test_collect_system_metrics_success(self, mock_dynamodb):
        """Test successful system metrics collection."""
        mock_dynamodb.describe_table.return_value = {
            "Table": {"TableSizeBytes": 1024000, "ItemCount": 100}  # 1MB
        }

        mock_dynamodb.scan.return_value = {
            "Items": [
                {"PK": {"S": "USER#123"}, "SK": {"S": "PROFILE"}},
                {"PK": {"S": "USER#456"}, "SK": {"S": "PROFILE"}},
            ],
            "Count": 2,
        }

        result = _collect_system_metrics()

        assert len(result) == 3  # TableSizeBytes, TotalItems, AverageTasksPerUser
        assert any(metric["MetricName"] == "TableSizeBytes" for metric in result)
        assert any(metric["MetricName"] == "TotalItems" for metric in result)
        assert any(metric["MetricName"] == "AverageTasksPerUser" for metric in result)

    @patch("lambda_custom_metrics.src.custom_metrics.dynamodb_client")
    def test_collect_system_metrics_error(self, mock_dynamodb):
        """Test system metrics collection with error."""
        mock_dynamodb.describe_table.side_effect = Exception("Table not found")

        result = _collect_system_metrics()

        # Should return empty list on error
        assert result == []

    @patch("lambda_custom_metrics.src.custom_metrics.cloudwatch_client")
    def test_send_metrics_to_cloudwatch_success(self, mock_cloudwatch):
        """Test successful metrics sending to CloudWatch."""
        mock_cloudwatch.put_metric_data.return_value = {}

        metrics = [
            {"MetricName": "TotalUsers", "Value": 100, "Unit": "Count"},
            {"MetricName": "TotalTasks", "Value": 500, "Unit": "Count"},
        ]

        _send_metrics_to_cloudwatch(metrics)

        mock_cloudwatch.put_metric_data.assert_called_once()
        call_args = mock_cloudwatch.put_metric_data.call_args
        assert call_args[1]["Namespace"] == "TodoApi/CustomMetrics"
        assert len(call_args[1]["MetricData"]) == 2

    @patch("lambda_custom_metrics.src.custom_metrics.cloudwatch_client")
    def test_send_metrics_to_cloudwatch_empty(self, mock_cloudwatch):
        """Test sending empty metrics to CloudWatch."""
        metrics = []

        _send_metrics_to_cloudwatch(metrics)

        # Should not call CloudWatch with empty metrics
        mock_cloudwatch.put_metric_data.assert_not_called()

    @patch("lambda_custom_metrics.src.custom_metrics.cloudwatch_client")
    def test_send_metrics_to_cloudwatch_error(self, mock_cloudwatch):
        """Test CloudWatch metrics sending with error."""
        mock_cloudwatch.put_metric_data.side_effect = Exception("CloudWatch error")

        metrics = [{"MetricName": "TotalUsers", "Value": 100, "Unit": "Count"}]

        # Should not raise exception, just log the error
        _send_metrics_to_cloudwatch(metrics)

        mock_cloudwatch.put_metric_data.assert_called_once()

    def test_metrics_data_structure(self):
        """Test that metrics have correct data structure."""
        metric = {
            "MetricName": "TestMetric",
            "Value": 42,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
        }

        assert "MetricName" in metric
        assert "Value" in metric
        assert "Unit" in metric
        assert isinstance(metric["Value"], (int, float))
        assert metric["Unit"] in ["Count", "Bytes", "Seconds", "Percent"]

    def test_recent_users_calculation(self):
        """Test recent users calculation logic."""
        now = datetime.utcnow()  # Use UTC to match the actual implementation
        recent_threshold = now - timedelta(days=7)

        # Test with recent login
        recent_login = (now - timedelta(days=3)).isoformat()
        assert datetime.fromisoformat(recent_login) > recent_threshold

        # Test with old login
        old_login = (now - timedelta(days=10)).isoformat()
        assert datetime.fromisoformat(old_login) <= recent_threshold
