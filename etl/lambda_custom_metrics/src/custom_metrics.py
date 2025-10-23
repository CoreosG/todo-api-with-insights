import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="TodoApi/CustomMetrics")

# Initialize AWS clients
dynamodb_client = boto3.client("dynamodb")
cloudwatch_client = boto3.client("cloudwatch")

# Environment variables
TABLE_NAME = os.environ.get("TABLE_NAME", "todo-app-data")
NAMESPACE = os.environ.get("NAMESPACE", "TodoApi/CustomMetrics")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Collect custom metrics from DynamoDB and send to CloudWatch.

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Dict containing metrics collection results
    """
    try:
        logger.info("Starting custom metrics collection")

        # Collect user metrics
        user_metrics = _collect_user_metrics()

        # Collect task metrics
        task_metrics = _collect_task_metrics()

        # Collect system metrics
        system_metrics = _collect_system_metrics()

        # Send metrics to CloudWatch
        _send_metrics_to_cloudwatch(user_metrics + task_metrics + system_metrics)

        logger.info("Custom metrics collection completed successfully")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Custom metrics collected successfully",
                    "user_metrics": len(user_metrics),
                    "task_metrics": len(task_metrics),
                    "system_metrics": len(system_metrics),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Custom metrics collection failed: {e}")
        metrics.add_metric(name="CustomMetricsErrors", unit="Count", value=1)
        raise


def _collect_user_metrics() -> List[Dict[str, Any]]:
    """Collect user-related metrics"""

    metrics_list = []

    try:
        # Count total users
        user_count_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :user_prefix)",
            ExpressionAttributeValues={":user_prefix": {"S": "USER#"}},
            Select="COUNT",
        )
        total_users = user_count_response.get("Count", 0)

        # Count active users (last 30 days) - check for last_login field
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :user_prefix) AND last_login > :thirty_days_ago",
            ExpressionAttributeValues={
                ":user_prefix": {"S": "USER#"},
                ":thirty_days_ago": {"S": thirty_days_ago.isoformat()},
            },
            Select="COUNT",
        )
        active_users = active_users_response.get("Count", 0)

        # Count verified users - check for verification_status field
        verified_users_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :user_prefix) AND verification_status = :verified",
            ExpressionAttributeValues={
                ":user_prefix": {"S": "USER#"},
                ":verified": {"S": "verified"},
            },
            Select="COUNT",
        )
        verified_users = verified_users_response.get("Count", 0)

        # Add metrics to list
        metrics_list.extend(
            [
                {"MetricName": "TotalUsers", "Value": total_users, "Unit": "Count"},
                {"MetricName": "ActiveUsers", "Value": active_users, "Unit": "Count"},
                {
                    "MetricName": "VerifiedUsers",
                    "Value": verified_users,
                    "Unit": "Count",
                },
                {
                    "MetricName": "UserVerificationRate",
                    "Value": (
                        (verified_users / total_users * 100) if total_users > 0 else 0
                    ),
                    "Unit": "Percent",
                },
            ]
        )

        logger.info(f"Collected user metrics: {len(metrics_list)} metrics")

    except Exception as e:
        logger.error(f"Failed to collect user metrics: {e}")

    return metrics_list


def _collect_task_metrics() -> List[Dict[str, Any]]:
    """Collect task-related metrics"""

    metrics_list = []

    try:
        # Count total tasks
        task_count_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :task_prefix)",
            ExpressionAttributeValues={":task_prefix": {"S": "TASK#"}},
            Select="COUNT",
        )
        total_tasks = task_count_response.get("Count", 0)

        # Count completed tasks
        completed_tasks_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :task_prefix) AND #status = :completed",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":task_prefix": {"S": "TASK#"},
                ":completed": {"S": "completed"},
            },
            Select="COUNT",
        )
        completed_tasks = completed_tasks_response.get("Count", 0)

        # Count pending tasks
        pending_tasks_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :task_prefix) AND #status = :pending",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":task_prefix": {"S": "TASK#"},
                ":pending": {"S": "pending"},
            },
            Select="COUNT",
        )
        pending_tasks = pending_tasks_response.get("Count", 0)

        # Count in-progress tasks
        in_progress_tasks_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :task_prefix) AND #status = :in_progress",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":task_prefix": {"S": "TASK#"},
                ":in_progress": {"S": "in_progress"},
            },
            Select="COUNT",
        )
        in_progress_tasks = in_progress_tasks_response.get("Count", 0)

        # Count high priority tasks
        high_priority_tasks_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :task_prefix) AND priority = :high",
            ExpressionAttributeValues={
                ":task_prefix": {"S": "TASK#"},
                ":high": {"S": "high"},
            },
            Select="COUNT",
        )
        high_priority_tasks = high_priority_tasks_response.get("Count", 0)

        # Add metrics to list
        metrics_list.extend(
            [
                {"MetricName": "TotalTasks", "Value": total_tasks, "Unit": "Count"},
                {
                    "MetricName": "CompletedTasks",
                    "Value": completed_tasks,
                    "Unit": "Count",
                },
                {"MetricName": "PendingTasks", "Value": pending_tasks, "Unit": "Count"},
                {
                    "MetricName": "InProgressTasks",
                    "Value": in_progress_tasks,
                    "Unit": "Count",
                },
                {
                    "MetricName": "HighPriorityTasks",
                    "Value": high_priority_tasks,
                    "Unit": "Count",
                },
                {
                    "MetricName": "TaskCompletionRate",
                    "Value": (
                        (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                    ),
                    "Unit": "Percent",
                },
            ]
        )

        logger.info(f"Collected task metrics: {len(metrics_list)} metrics")

    except Exception as e:
        logger.error(f"Failed to collect task metrics: {e}")

    return metrics_list


def _collect_system_metrics() -> List[Dict[str, Any]]:
    """Collect system-related metrics"""

    metrics_list = []

    try:
        # Get table size and item count
        table_info = dynamodb_client.describe_table(TableName=TABLE_NAME)
        table_size = table_info["Table"]["TableSizeBytes"]
        item_count = table_info["Table"]["ItemCount"]

        # Calculate average task per user
        user_count_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :user_prefix)",
            ExpressionAttributeValues={":user_prefix": {"S": "USER#"}},
            Select="COUNT",
        )
        total_users = user_count_response.get("Count", 0)

        task_count_response = dynamodb_client.scan(
            TableName=TABLE_NAME,
            FilterExpression="begins_with(PK, :task_prefix)",
            ExpressionAttributeValues={":task_prefix": {"S": "TASK#"}},
            Select="COUNT",
        )
        total_tasks = task_count_response.get("Count", 0)

        avg_tasks_per_user = (total_tasks / total_users) if total_users > 0 else 0

        # Add metrics to list
        metrics_list.extend(
            [
                {"MetricName": "TableSizeBytes", "Value": table_size, "Unit": "Bytes"},
                {"MetricName": "TotalItems", "Value": item_count, "Unit": "Count"},
                {
                    "MetricName": "AverageTasksPerUser",
                    "Value": avg_tasks_per_user,
                    "Unit": "Count",
                },
            ]
        )

        logger.info(f"Collected system metrics: {len(metrics_list)} metrics")

    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")

    return metrics_list


def _send_metrics_to_cloudwatch(metrics_list: List[Dict[str, Any]]) -> None:
    """Send metrics to CloudWatch"""

    try:
        # Group metrics by namespace
        metrics_by_namespace: Dict[str, List[Dict[str, Any]]] = {}
        for metric in metrics_list:
            namespace = NAMESPACE
            if namespace not in metrics_by_namespace:
                metrics_by_namespace[namespace] = []
            metrics_by_namespace[namespace].append(metric)

        # Send metrics for each namespace
        for namespace, metrics in metrics_by_namespace.items():
            cloudwatch_client.put_metric_data(Namespace=namespace, MetricData=metrics)
            logger.info(
                f"Sent {len(metrics)} metrics to CloudWatch namespace: {namespace}"
            )

    except Exception as e:
        logger.error(f"Failed to send metrics to CloudWatch: {e}")
        # Don't raise the exception, just log it
