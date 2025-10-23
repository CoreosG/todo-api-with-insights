import os
from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput, Tags
)
from aws_cdk.aws_s3 import (
    Bucket, BucketEncryption, BlockPublicAccess,
    LifecycleRule, StorageClass, Transition
)
from aws_cdk.aws_kinesisfirehose import (
    CfnDeliveryStream,
    CfnDeliveryStream as DeliveryStream
)
from aws_cdk.aws_glue import CfnDatabase, CfnCrawler, CfnJob
from aws_cdk.aws_athena import CfnWorkGroup
from aws_cdk.aws_iam import (
    Role, ServicePrincipal, PolicyStatement, ManagedPolicy, PolicyDocument
)
from aws_cdk.aws_lambda import Runtime, StartingPosition as LambdaStartingPosition
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.aws_lambda_event_sources import DynamoEventSource
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_s3_assets import Asset
from constructs import Construct
import os

class EtlStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, table: Table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Save table reference
        self.table = table
        
        # Create S3 buckets for data lake layers
        self._create_s3_buckets()
        
        # Create IAM roles for ETL services
        self._create_iam_roles()
        
        # Create Firehose delivery streams
        self._create_firehose_streams()
        
        # Create Glue database and catalog
        self._create_glue_database()
        
        # Create Glue jobs
        self._create_glue_jobs()
        
        # Create Athena workgroup
        self._create_athena_workgroup()
        
        # Create CDC Lambda function
        self._create_cdc_lambda()
        
        # Add resource tags
        self._add_resource_tags()
        
        # Create outputs
        self._create_outputs()

    def _create_s3_buckets(self) -> None:
        """Create S3 buckets for Bronze, Silver, and Gold data layers"""
        
        # Bronze layer - raw data from DynamoDB streams and logs
        self.bronze_bucket = Bucket(
            self, "BronzeBucket",
            bucket_name=f"todo-bronze-{self.account}-{self.region}",
            encryption=BucketEncryption.S3_MANAGED,
            block_public_access=BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,  # For development only
            auto_delete_objects=True,  # Empty bucket before deletion
            lifecycle_rules=[
                LifecycleRule(
                    id="BronzeLifecycle",
                    enabled=True,
                    transitions=[
                        Transition(
                            storage_class=StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        Transition(
                            storage_class=StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )
        
        # Silver layer - transformed data from Glue jobs
        self.silver_bucket = Bucket(
            self, "SilverBucket",
            bucket_name=f"todo-silver-{self.account}-{self.region}",
            encryption=BucketEncryption.S3_MANAGED,
            block_public_access=BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,  # For development only
            auto_delete_objects=True,  # Empty bucket before deletion
            lifecycle_rules=[
                LifecycleRule(
                    id="SilverLifecycle",
                    enabled=True,
                    transitions=[
                        Transition(
                            storage_class=StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ]
        )
        
        # Gold layer - analytics-optimized data
        self.gold_bucket = Bucket(
            self, "GoldBucket",
            bucket_name=f"todo-gold-{self.account}-{self.region}",
            encryption=BucketEncryption.S3_MANAGED,
            block_public_access=BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,  # For development only
            auto_delete_objects=True,  # Empty bucket before deletion
        )

    def _create_iam_roles(self) -> None:
        """Create IAM roles for ETL services"""
        
        # Firehose service role
        self.firehose_role = Role(
            self, "FirehoseRole",
            assumed_by=ServicePrincipal("firehose.amazonaws.com"),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
        )
        
        # Grant Firehose access to S3 buckets
        self.bronze_bucket.grant_read_write(self.firehose_role)
        self.silver_bucket.grant_read_write(self.firehose_role)
        
        # Glue service role
        self.glue_role = Role(
            self, "GlueRole",
            assumed_by=ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
            ],
        )
        
        # Grant Glue access to S3 buckets
        self.bronze_bucket.grant_read_write(self.glue_role)
        self.silver_bucket.grant_read_write(self.glue_role)
        self.gold_bucket.grant_read_write(self.glue_role)
        
        # Grant Glue access to DynamoDB table
        self.glue_role.add_to_policy(
            PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                resources=[
                    self.table.table_arn,
                    f"{self.table.table_arn}/index/*"
                ]
            )
        )
        
        # Athena service role with inline policy
        self.athena_role = Role(
            self, "AthenaRole",
            assumed_by=ServicePrincipal("athena.amazonaws.com"),
            inline_policies={
                "AthenaQueryExecutionPolicy": PolicyDocument(
                    statements=[
                        PolicyStatement(
                            actions=[
                                "s3:GetBucketLocation",
                                "s3:GetObject",
                                "s3:ListBucket",
                                "s3:ListBucketMultipartUploads",
                                "s3:ListMultipartUploadParts",
                                "s3:AbortMultipartUpload"
                            ],
                            resources=["*"]
                        ),
                        PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject"
                            ],
                            resources=[
                                f"{self.bronze_bucket.bucket_arn}/*",
                                f"{self.silver_bucket.bucket_arn}/*",
                                f"{self.gold_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                )
            },
        )
        
        # Grant Athena access to S3 buckets
        self.bronze_bucket.grant_read(self.athena_role)
        self.silver_bucket.grant_read(self.athena_role)
        self.gold_bucket.grant_read_write(self.athena_role)

    def _create_firehose_streams(self) -> None:
        """Create Firehose delivery streams for logs and CDC events"""
        
        # Logs delivery stream
        self.logs_stream = CfnDeliveryStream(
            self, "LogsDeliveryStream",
            delivery_stream_name="todo-logs-stream",
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=self.bronze_bucket.bucket_arn,
                prefix="logs/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
                error_output_prefix="errors/",
                buffering_hints=CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60,
                    size_in_m_bs=1
                ),
                compression_format="GZIP",
                role_arn=self.firehose_role.role_arn
            )
        )
        
        # CDC events delivery stream
        self.cdc_stream = CfnDeliveryStream(
            self, "CdcDeliveryStream",
            delivery_stream_name="todo-cdc-stream",
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=self.bronze_bucket.bucket_arn,
                prefix="cdc/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
                error_output_prefix="errors/",
                buffering_hints=CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60,
                    size_in_m_bs=1
                ),
                compression_format="GZIP",
                role_arn=self.firehose_role.role_arn
            )
        )

    def _create_glue_database(self) -> None:
        """Create Glue database and crawler for data catalog"""
        
        # Glue database
        self.glue_database = CfnDatabase(
            self, "GlueDatabase",
            catalog_id=self.account,
            database_input=CfnDatabase.DatabaseInputProperty(
                name="todo_analytics",
                description="Database for Todo API analytics data"
            )
        )
        
        # Glue crawler for Bronze layer
        self.bronze_crawler = CfnCrawler(
            self, "BronzeCrawler",
            name="todo-bronze-crawler",
            role=self.glue_role.role_arn,
            database_name=self.glue_database.ref,
            targets=CfnCrawler.TargetsProperty(
                s3_targets=[
                    CfnCrawler.S3TargetProperty(
                        path=f"s3://{self.bronze_bucket.bucket_name}/"
                    )
                ]
            )
        )

    def _create_glue_jobs(self) -> None:
        """Create Glue jobs for data transformation"""

        # Upload Glue job scripts as assets
        silver_script_asset = Asset(
            self, "SilverTransformationScript",
            path=os.path.join(os.path.dirname(__file__), "../../etl/glue_jobs/silver_transformation/silver_transformation.py")
        )

        gold_script_asset = Asset(
            self, "GoldAnalyticsScript",
            path=os.path.join(os.path.dirname(__file__), "../../etl/glue_jobs/gold_analytics/gold_analytics.py")
        )

        # Grant Glue role access to the script assets
        silver_script_asset.grant_read(self.glue_role)
        gold_script_asset.grant_read(self.glue_role)

        # Silver transformation job
        self.silver_job = CfnJob(
            self, "SilverTransformationJob",
            name="todo-silver-transformation",
            role=self.glue_role.role_arn,
            command=CfnJob.JobCommandProperty(
                name="glueetl",
                script_location=f"s3://{silver_script_asset.bucket.bucket_name}/{silver_script_asset.s3_object_key}",
                python_version="3"
            ),
            max_capacity=2,
            timeout=60,
            glue_version="4.0",
            default_arguments={
                "--BRONZE_BUCKET": self.bronze_bucket.bucket_name,
                "--SILVER_BUCKET": self.silver_bucket.bucket_name,
                "--DATABASE_NAME": self.glue_database.ref,
                "--TempDir": f"s3://{self.bronze_bucket.bucket_name}/temp/",
                "--job-language": "python",
                "--job-bookmark-option": "job-bookmark-enable"
            }
        )

        # Gold analytics job
        self.gold_job = CfnJob(
            self, "GoldAnalyticsJob",
            name="todo-gold-analytics",
            role=self.glue_role.role_arn,
            command=CfnJob.JobCommandProperty(
                name="glueetl",
                script_location=f"s3://{gold_script_asset.bucket.bucket_name}/{gold_script_asset.s3_object_key}",
                python_version="3"
            ),
            max_capacity=2,
            timeout=60,
            glue_version="4.0",
            default_arguments={
                "--SILVER_BUCKET": self.silver_bucket.bucket_name,
                "--GOLD_BUCKET": self.gold_bucket.bucket_name,
                "--DATABASE_NAME": self.glue_database.ref,
                "--TempDir": f"s3://{self.bronze_bucket.bucket_name}/temp/",
                "--job-language": "python",
                "--job-bookmark-option": "job-bookmark-enable"
            }
        )

    def _create_athena_workgroup(self) -> None:
        """Create Athena workgroup for query optimization"""
        
        self.athena_workgroup = CfnWorkGroup(
            self, "AthenaWorkgroup",
            name="todo-analytics-workgroup",
            description="Workgroup for Todo API analytics queries",
            work_group_configuration={
                "result_configuration": {
                    "output_location": f"s3://{self.gold_bucket.bucket_name}/athena-results/",
                    "encryption_configuration": {
                        "encryption_option": "SSE_S3"
                    }
                },
                "enforce_work_group_configuration": True,
                "publish_cloud_watch_metrics_enabled": True
            }
        )

    def _create_cdc_lambda(self) -> None:
        """Create Lambda function for DynamoDB Streams CDC processing"""
        
        # IAM role for CDC Lambda
        self.cdc_lambda_role = Role(
            self, "CdcLambdaRole",
            assumed_by=ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
        )
        
        # Grant CDC Lambda access to DynamoDB streams
        self.cdc_lambda_role.add_to_policy(
            PolicyStatement(
                actions=[
                    "dynamodb:DescribeStream",
                    "dynamodb:GetRecords",
                    "dynamodb:GetShardIterator",
                    "dynamodb:ListStreams"
                ],
                resources=[self.table.table_stream_arn]
            )
        )
        
        # Grant CDC Lambda access to Firehose
        self.cdc_lambda_role.add_to_policy(
            PolicyStatement(
                actions=[
                    "firehose:PutRecord",
                    "firehose:PutRecordBatch"
                ],
                resources=[self.cdc_stream.attr_arn]
            )
        )
        
        # Create CDC Lambda function
        self.cdc_lambda = PythonFunction(
            self, "CdcLambda",
            function_name="todo-cdc-processor",
            runtime=Runtime.PYTHON_3_13,
            entry="../etl/lambda_cdc",
            index="src/cdc_handler.py",
            handler="lambda_handler",
            role=self.cdc_lambda_role,
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "FIREHOSE_STREAM_NAME": self.cdc_stream.delivery_stream_name,
                "BRONZE_BUCKET": self.bronze_bucket.bucket_name,
                "TABLE_NAME": self.table.table_name
            }
        )

        # Add DynamoDB stream as event source
        self.cdc_lambda.add_event_source(
            DynamoEventSource(
                table=self.table,
                starting_position=LambdaStartingPosition.LATEST,
                batch_size=100,
                bisect_batch_on_error=True,
                retry_attempts=3
            )
        )

    def _add_resource_tags(self) -> None:
        """Add resource tags to all ETL components"""
        tags = {
            "Project": "todo-api-with-insights",
            "Owner": "development-team",
            "Environment": self.node.try_get_context("environment") or "development",
            "CostCenter": "engineering-platform",
        }
        for key, value in tags.items():
            Tags.of(self).add(key, value)

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for ETL stack"""
        CfnOutput(
            self, "BronzeBucketName",
            value=self.bronze_bucket.bucket_name,
            description="S3 bucket for Bronze layer data"
        )
        CfnOutput(
            self, "SilverBucketName", 
            value=self.silver_bucket.bucket_name,
            description="S3 bucket for Silver layer data"
        )
        CfnOutput(
            self, "GoldBucketName",
            value=self.gold_bucket.bucket_name,
            description="S3 bucket for Gold layer data"
        )
        CfnOutput(
            self, "CdcLambdaFunctionName",
            value=self.cdc_lambda.function_name,
            description="Lambda function for CDC processing"
        )
        CfnOutput(
            self, "GlueDatabaseName",
            value=self.glue_database.ref,
            description="Glue database for data catalog"
        )
        CfnOutput(
            self, "AthenaWorkgroupName",
            value=self.athena_workgroup.name,
            description="Athena workgroup for analytics queries"
        )
