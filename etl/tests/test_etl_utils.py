"""Unit tests for ETL utilities."""

from datetime import datetime
from unittest.mock import Mock, patch

from shared.utils.etl_utils import ETLUtils


class TestETLUtils:
    """Test cases for ETLUtils class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.etl_utils = ETLUtils(region="us-east-1")

    def test_create_s3_path(self):
        """Test S3 path creation with partitioning."""
        bucket = "test-bucket"
        prefix = "data"
        year, month, day = 2024, 1, 15

        result = self.etl_utils.create_s3_path(bucket, prefix, year, month, day)

        expected = "s3://test-bucket/data/year=2024/month=01/day=15/"
        assert result == expected

    def test_get_partition_values(self):
        """Test partition values extraction from date."""
        test_date = datetime(2024, 1, 15)

        result = self.etl_utils.get_partition_values(test_date)

        expected = {"year": 2024, "month": 1, "day": 15}
        assert result == expected

    def test_validate_data_quality_success(self):
        """Test successful data quality validation."""
        data = {"user_id": "123", "email": "test@example.com", "age": 25}
        rules = {
            "required_fields": ["user_id", "email"],
            "data_types": {"user_id": "string", "email": "string", "age": "int"},
            "constraints": {"age": {"min": 0, "max": 120}},
        }

        result = self.etl_utils.validate_data_quality(data, rules)

        assert result is True

    def test_validate_data_quality_missing_field(self):
        """Test data quality validation with missing required field."""
        data = {
            "user_id": "123"
            # Missing email field
        }
        rules = {
            "required_fields": ["user_id", "email"],
            "data_types": {"user_id": "string", "email": "string"},
        }

        result = self.etl_utils.validate_data_quality(data, rules)

        assert result is False

    def test_validate_data_quality_wrong_type(self):
        """Test data quality validation with wrong data type."""
        data = {"user_id": "123", "age": "not_a_number"}  # Should be int
        rules = {
            "required_fields": ["user_id"],
            "data_types": {"user_id": "string", "age": "int"},
        }

        result = self.etl_utils.validate_data_quality(data, rules)

        assert result is False

    def test_validate_data_quality_constraint_violation(self):
        """Test data quality validation with constraint violation."""
        data = {"user_id": "123", "age": 150}  # Above max constraint
        rules = {
            "required_fields": ["user_id"],
            "data_types": {"user_id": "string", "age": "int"},
            "constraints": {"age": {"min": 0, "max": 120}},
        }

        result = self.etl_utils.validate_data_quality(data, rules)

        assert result is False

    def test_transform_dynamodb_item_string(self):
        """Test DynamoDB item transformation for string values."""
        item = {"user_id": {"S": "123"}, "email": {"S": "test@example.com"}}

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"user_id": "123", "email": "test@example.com"}
        assert result == expected

    def test_transform_dynamodb_item_number(self):
        """Test DynamoDB item transformation for number values."""
        item = {"age": {"N": "25"}, "score": {"N": "95.5"}}

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"age": 25, "score": 95.5}
        assert result == expected

    def test_transform_dynamodb_item_boolean(self):
        """Test DynamoDB item transformation for boolean values."""
        item = {"is_active": {"BOOL": True}, "is_verified": {"BOOL": False}}

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"is_active": True, "is_verified": False}
        assert result == expected

    def test_transform_dynamodb_item_null(self):
        """Test DynamoDB item transformation for null values."""
        item = {"optional_field": {"NULL": True}}

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"optional_field": None}
        assert result == expected

    def test_transform_dynamodb_item_list(self):
        """Test DynamoDB item transformation for list values."""
        item = {"tags": {"L": [{"S": "urgent"}, {"S": "important"}]}}

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"tags": ["urgent", "important"]}
        assert result == expected

    def test_transform_dynamodb_item_map(self):
        """Test DynamoDB item transformation for map values."""
        item = {
            "address": {
                "M": {"street": {"S": "123 Main St"}, "city": {"S": "New York"}}
            }
        }

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"address": {"street": "123 Main St", "city": "New York"}}
        assert result == expected

    def test_transform_dynamodb_item_string_set(self):
        """Test DynamoDB item transformation for string set values."""
        item = {"categories": {"SS": ["work", "personal"]}}

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"categories": ["work", "personal"]}
        assert result == expected

    def test_transform_dynamodb_item_number_set(self):
        """Test DynamoDB item transformation for number set values."""
        item = {"scores": {"NS": ["85", "92", "78"]}}

        result = self.etl_utils.transform_dynamodb_item(item)

        expected = {"scores": [85, 92, 78]}
        assert result == expected

    @patch("shared.utils.etl_utils.boto3.client")
    def test_glue_schema_creation(self, mock_boto3_client):
        """Test Glue schema creation."""
        mock_glue_client = Mock()
        mock_boto3_client.return_value = mock_glue_client

        database_name = "test_database"
        table_name = "test_table"
        schema = [
            {"Name": "user_id", "Type": "string"},
            {"Name": "email", "Type": "string"},
        ]
        partition_keys = ["year", "month"]
        location = "s3://test-bucket/data/"

        result = self.etl_utils.create_glue_table_schema(
            table_name, database_name, schema, partition_keys, location
        )

        assert result["Name"] == table_name
        assert result["DatabaseName"] == database_name
        assert len(result["StorageDescriptor"]["Columns"]) == 2
        assert len(result["PartitionKeys"]) == 2

    def test_athena_query_execution(self):
        """Test Athena query execution."""
        # Mock the athena_client on the instance
        with patch.object(self.etl_utils, 'athena_client') as mock_athena_client:
            mock_athena_client.start_query_execution.return_value = {
                "QueryExecutionId": "test-query-id"
            }

            query = "SELECT * FROM test_table LIMIT 10"
            database = "test_database"
            output_location = "s3://test-bucket/results/"

            result = self.etl_utils.execute_athena_query(query, database, output_location)

            assert result == "test-query-id"
            mock_athena_client.start_query_execution.assert_called_once()

    def test_validate_data_lake_structure_success(self):
        """Test successful ETL pipeline validation."""
        with patch.object(self.etl_utils, "s3_client") as mock_s3:
            mock_s3.list_objects_v2.return_value = {
                "Contents": [
                    {"Key": "cdc/year=2024/month=01/day=15/data.parquet"},
                    {"Key": "logs/year=2024/month=01/day=15/logs.json"},
                ],
                "KeyCount": 2,
            }
            mock_s3.head_object.return_value = {"ContentLength": 1024}

            bronze_bucket = "test-bronze-bucket"
            silver_bucket = "test-silver-bucket"
            gold_bucket = "test-gold-bucket"

            result = self.etl_utils.validate_etl_pipeline(
                bronze_bucket, silver_bucket, gold_bucket
            )

            assert "bronze_layer" in result
            assert "silver_layer" in result
            assert "gold_layer" in result
            assert result["bronze_layer"]["cdc_events"] == 2

    def test_validate_data_lake_structure_missing_layers(self):
        """Test ETL pipeline validation with missing data."""
        with patch.object(self.etl_utils, "s3_client") as mock_s3:
            mock_s3.list_objects_v2.return_value = {
                "Contents": [],
                "KeyCount": 0,
            }
            mock_s3.head_object.return_value = {"ContentLength": 0}

            bronze_bucket = "test-bronze-bucket"
            silver_bucket = "test-silver-bucket"
            gold_bucket = "test-gold-bucket"

            result = self.etl_utils.validate_etl_pipeline(
                bronze_bucket, silver_bucket, gold_bucket
            )

            assert "bronze_layer" in result
            assert result["bronze_layer"]["cdc_events"] == 0
