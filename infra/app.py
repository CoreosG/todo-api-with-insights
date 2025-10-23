import os
from aws_cdk import App, Environment

# Create the CDK app
app = App()

# Configure environment (AWS CLI)
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)

# Import stacks - must be imported after app creation
from stacks.api_stack import ApiStack
from stacks.data_stack import DataStack
from stacks.etl_stack import EtlStack
from stacks.monitoring_stack import MonitoringStack


# DataStack must be created first (DynamoDB table)
data_stack = DataStack(
    app,
    "TodoDataStack",
    env=env,
)

# ApiStack depends on DataStack (references the DynamoDB table)
api_stack = ApiStack(
    app,
    "TodoApiStack",
    data_stack.table, # Pass table name for IAM and environment
    env=env,
    description="Cognito, Lambda, API Gateway for Todo API",
)

# ETL Stack depends on DataStack (references the DynamoDB table)
etl_stack = EtlStack(
    app,
    "TodoEtlStack",
    data_stack.table, # Pass table reference for CDC processing
    env=env,
    description="ETL pipeline for data lake and analytics",
)

# Monitoring Stack (can be created independently)
monitoring_stack = MonitoringStack(
    app,
    "TodoMonitoringStack",
    env=env,
    description="CloudWatch monitoring and alerting",
)

# Add stack dependencies
api_stack.add_dependency(data_stack)
etl_stack.add_dependency(data_stack)

# Synthesize the CloudFormation templates
app.synth()