from aws_cdk import Stack, RemovalPolicy, CfnOutput
from aws_cdk.aws_dynamodb import (
    PointInTimeRecoverySpecification, Table, Attribute, AttributeType, ProjectionType, BillingMode, StreamViewType
)
from constructs import Construct

class DataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB table with single-table design
        self.table = Table(
            self, "TodoTable",
            table_name="todo-app-data",
            partition_key=Attribute(name="PK", type=AttributeType.STRING),
            sort_key=Attribute(name="SK", type=AttributeType.STRING),
            billing_mode=BillingMode.PAY_PER_REQUEST,
            stream=StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY, # DESTROY only for dev.
            point_in_time_recovery_specification=PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
            ),
        )

        # Create Global Secondary Indexes
        self._add_global_secondary_indexes()
        # Add resource tags
        self._add_resource_tags()
        # Create cloudformation outputs
        self._create_outputs()

    # Add GSI
    def _add_global_secondary_indexes(self) -> None:
        # Add GSI1 - User Tasks by Status
        self.table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=Attribute(name="GSI1PK", type=AttributeType.STRING),
            sort_key=Attribute(name="GSI1SK", type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
        # Add GSI2 - User Tasks by Due Date
        self.table.add_global_secondary_index(
            index_name="GSI2",
            partition_key=Attribute(name="GSI2PK", type=AttributeType.STRING),
            sort_key=Attribute(name="GSI2SK", type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
        # Add GSI3 - User Tasks by Priority
        self.table.add_global_secondary_index(
            index_name="GSI3",
            partition_key=Attribute(name="GSI3PK", type=AttributeType.STRING),
            sort_key=Attribute(name="GSI3SK", type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
        # Add GSI4 - User Tasks by Category
        self.table.add_global_secondary_index(
            index_name="GSI4",
            partition_key=Attribute(name="GSI4PK", type=AttributeType.STRING),
            sort_key=Attribute(name="GSI4SK", type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
    
    # Add resource tags
    def _add_resource_tags(self) -> None:
        # Add resource tags
        for key, value in {
            "Project": "todo-api-with-insights",
            "Owner": "development-team",
            "Environment": self.node.try_get_context("environment") or "development",
            "CostCenter": "engineering-platform",
        }.items():
            self.table.node.default_child.add_property_override("Tags", [{"Key": key, "Value": value}])

    # Create cloudformation outputs
    def _create_outputs(self) -> None:
        # Create cloudformation outputs
        CfnOutput(self, "TodoTableArn", value=self.table.table_arn, description="The ARN of the DynamoDB table")
        CfnOutput(self, "TodoTableName", value=self.table.table_name, description="The name of the DynamoDB table")
        CfnOutput(self, "TodoTableStreamArn", value=self.table.table_stream_arn, description="The ARN of the DynamoDB table stream")
