import logging
from datetime import datetime
from typing import Any, Dict, List

import boto3

# Configure logging
logger = logging.getLogger(__name__)


class ETLUtils:
    """Utility functions for ETL operations"""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.s3_client = boto3.client("s3", region_name=region)
        self.glue_client = boto3.client("glue", region_name=region)
        self.athena_client = boto3.client("athena", region_name=region)

    def create_s3_path(
        self, bucket: str, prefix: str, year: int, month: int, day: int
    ) -> str:
        """Create S3 path with partitioning"""
        return (
            f"s3://{bucket}/{prefix}/year={year:04d}/month={month:02d}/day={day:02d}/"
        )

    def get_partition_values(self, date: datetime) -> Dict[str, int]:
        """Get partition values from date"""
        return {"year": date.year, "month": date.month, "day": date.day}

    def validate_data_quality(
        self, data: Dict[str, Any], rules: Dict[str, Any]
    ) -> bool:
        """Validate data quality against rules"""
        try:
            # Check required fields
            required_fields = rules.get("required_fields", [])
            for field in required_fields:
                if field not in data or data[field] is None:
                    logger.warning(f"Missing required field: {field}")
                    return False

            # Check data types
            data_types = rules.get("data_types", {})
            for field, expected_type in data_types.items():
                if field in data:
                    if expected_type == "string" and not isinstance(data[field], str):
                        logger.warning(
                            f"Field {field} should be string, got {type(data[field])}"
                        )
                        return False
                    elif expected_type == "int" and not isinstance(data[field], int):
                        logger.warning(
                            f"Field {field} should be int, got {type(data[field])}"
                        )
                        return False
                    elif expected_type == "float" and not isinstance(
                        data[field], (int, float)
                    ):
                        logger.warning(
                            f"Field {field} should be float, got {type(data[field])}"
                        )
                        return False
                    elif expected_type == "bool" and not isinstance(data[field], bool):
                        logger.warning(
                            f"Field {field} should be bool, got {type(data[field])}"
                        )
                        return False

            # Check constraints
            constraints = rules.get("constraints", {})
            for field, constraint in constraints.items():
                if field in data:
                    if (
                        constraint.get("min") is not None
                        and data[field] < constraint["min"]
                    ):
                        logger.warning(
                            f"Field {field} below minimum: {data[field]} < {constraint['min']}"
                        )
                        return False
                    if (
                        constraint.get("max") is not None
                        and data[field] > constraint["max"]
                    ):
                        logger.warning(
                            f"Field {field} above maximum: {data[field]} > {constraint['max']}"
                        )
                        return False
                    if constraint.get("pattern") is not None:
                        import re

                        if not re.match(constraint["pattern"], str(data[field])):
                            logger.warning(
                                f"Field {field} doesn't match pattern: {data[field]}"
                            )
                            return False

            return True

        except Exception as e:
            logger.error(f"Data quality validation failed: {e}")
            return False

    def transform_dynamodb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transform DynamoDB item to regular JSON"""
        transformed: Dict[str, Any] = {}

        for key, value in item.items():
            if "S" in value:
                # String value
                transformed[key] = value["S"]
            elif "N" in value:
                # Number value
                try:
                    if "." in value["N"]:
                        transformed[key] = float(value["N"])
                    else:
                        transformed[key] = int(value["N"])
                except ValueError:
                    transformed[key] = value["N"]
            elif "BOOL" in value:
                # Boolean value
                transformed[key] = value["BOOL"]
            elif "NULL" in value:
                # Null value
                transformed[key] = None
            elif "L" in value:
                # List value
                transformed[key] = [
                    self.transform_dynamodb_item({"item": v})["item"]
                    for v in value["L"]
                ]
            elif "M" in value:
                # Map value
                transformed[key] = self.transform_dynamodb_item(value["M"])
            elif "SS" in value:
                # String set
                transformed[key] = value["SS"]
            elif "NS" in value:
                # Number set
                transformed[key] = [
                    float(n) if "." in n else int(n) for n in value["NS"]
                ]
            elif "BS" in value:
                # Binary set
                transformed[key] = value["BS"]
            else:
                # Unknown type, keep as is
                transformed[key] = value

        return transformed

    def create_glue_table_schema(
        self,
        table_name: str,
        database_name: str,
        columns: List[Dict[str, Any]],
        partition_keys: List[str],
        location: str,
    ) -> Dict[str, Any]:
        """Create Glue table schema"""
        return {
            "Name": table_name,
            "DatabaseName": database_name,
            "TableType": "EXTERNAL_TABLE",
            "StorageDescriptor": {
                "Columns": columns,
                "Location": location,
                "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                "SerdeInfo": {
                    "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                },
            },
            "PartitionKeys": [
                {"Name": key, "Type": "string"} for key in partition_keys
            ],
            "Parameters": {"classification": "parquet", "typeOfData": "file"},
        }

    def create_glue_database_schema(
        self, database_name: str, description: str, location_uri: str
    ) -> Dict[str, Any]:
        """Create Glue database schema"""
        return {
            "Name": database_name,
            "Description": description,
            "LocationUri": location_uri,
            "Parameters": {"classification": "parquet"},
        }

    def get_athena_query_results(self, query_id: str) -> Dict[str, Any]:
        """Get Athena query results"""
        try:
            response = self.athena_client.get_query_results(QueryExecutionId=query_id)
            return dict(response)
        except Exception as e:
            logger.error(f"Failed to get Athena query results: {e}")
            return {}

    def execute_athena_query(
        self, query: str, database: str, output_location: str
    ) -> str:
        """Execute Athena query and return query ID"""
        try:
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": database},
                ResultConfiguration={"OutputLocation": output_location},
            )
            return str(response["QueryExecutionId"])
        except Exception as e:
            logger.error(f"Failed to execute Athena query: {e}")
            raise

    def wait_for_athena_query(self, query_id: str, max_wait_time: int = 300) -> bool:
        """Wait for Athena query to complete"""
        import time

        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                response = self.athena_client.get_query_execution(
                    QueryExecutionId=query_id
                )
                status = response["QueryExecution"]["Status"]["State"]

                if status == "SUCCEEDED":
                    return True
                elif status in ["FAILED", "CANCELLED"]:
                    logger.error(
                        f"Athena query failed: {response['QueryExecution']['Status']}"
                    )
                    return False

                time.sleep(5)  # Wait 5 seconds before checking again

            except Exception as e:
                logger.error(f"Error checking Athena query status: {e}")
                return False

        logger.warning(f"Athena query timed out after {max_wait_time} seconds")
        return False

    def create_partitioned_path(
        self, base_path: str, partition_values: Dict[str, Any]
    ) -> str:
        """Create partitioned S3 path"""
        path_parts = [base_path]
        for key, value in partition_values.items():
            path_parts.append(f"{key}={value}")
        return "/".join(path_parts) + "/"

    def get_s3_object_count(self, bucket: str, prefix: str) -> int:
        """Get count of objects in S3 prefix"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return int(response.get("KeyCount", 0))
        except Exception as e:
            logger.error(f"Failed to get S3 object count: {e}")
            return 0

    def get_s3_object_size(self, bucket: str, prefix: str) -> int:
        """Get total size of objects in S3 prefix"""
        try:
            total_size = 0
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    total_size += obj["Size"]
            return total_size
        except Exception as e:
            logger.error(f"Failed to get S3 object size: {e}")
            return 0

    def create_data_lake_structure(
        self, bronze_bucket: str, silver_bucket: str, gold_bucket: str
    ) -> Dict[str, str]:
        """Create data lake directory structure"""
        structure = {
            "bronze_cdc": f"s3://{bronze_bucket}/cdc/",
            "bronze_logs": f"s3://{bronze_bucket}/logs/",
            "silver_cdc": f"s3://{silver_bucket}/cdc/",
            "silver_users": f"s3://{silver_bucket}/users/",
            "silver_tasks": f"s3://{silver_bucket}/tasks/",
            "gold_user_analytics": f"s3://{gold_bucket}/user_analytics/",
            "gold_task_analytics": f"s3://{gold_bucket}/task_analytics/",
            "gold_business_metrics": f"s3://{gold_bucket}/business_metrics/",
            "gold_athena_results": f"s3://{gold_bucket}/athena-results/",
        }

        return structure

    def validate_etl_pipeline(
        self, bronze_bucket: str, silver_bucket: str, gold_bucket: str
    ) -> Dict[str, Any]:
        """Validate ETL pipeline health"""
        validation_results = {
            "bronze_layer": {
                "cdc_events": self.get_s3_object_count(bronze_bucket, "cdc/"),
                "logs": self.get_s3_object_count(bronze_bucket, "logs/"),
                "total_size": self.get_s3_object_size(bronze_bucket, ""),
            },
            "silver_layer": {
                "cdc_events": self.get_s3_object_count(silver_bucket, "cdc/"),
                "users": self.get_s3_object_count(silver_bucket, "users/"),
                "tasks": self.get_s3_object_count(silver_bucket, "tasks/"),
                "total_size": self.get_s3_object_size(silver_bucket, ""),
            },
            "gold_layer": {
                "user_analytics": self.get_s3_object_count(
                    gold_bucket, "user_analytics/"
                ),
                "task_analytics": self.get_s3_object_count(
                    gold_bucket, "task_analytics/"
                ),
                "business_metrics": self.get_s3_object_count(
                    gold_bucket, "business_metrics/"
                ),
                "total_size": self.get_s3_object_size(gold_bucket, ""),
            },
        }

        return validation_results
