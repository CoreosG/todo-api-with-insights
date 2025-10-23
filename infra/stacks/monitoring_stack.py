import os
from aws_cdk import (
    Stack, Duration, CfnOutput, Tags
)
from aws_cdk.aws_cloudwatch import (
    Dashboard, GraphWidget, Metric, Alarm, 
    ComparisonOperator, TreatMissingData
)
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_sns import Topic, Subscription, SubscriptionProtocol
from aws_cdk.aws_iam import (
    Role, ServicePrincipal, PolicyStatement, ManagedPolicy
)
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct

class MonitoringStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create monitoring components
        self._create_sns_topic()
        self._create_cloudwatch_dashboard()
        self._create_api_alarms()
        self._create_etl_alarms()
        self._create_cost_alarms()
        self._create_custom_metrics_lambda()
        
        # Add resource tags
        self._add_resource_tags()
        
        # Create outputs
        self._create_outputs()

    def _create_sns_topic(self) -> None:
        """Create SNS topic for alerts"""
        
        self.alert_topic = Topic(
            self, "AlertTopic",
            display_name="Todo API Alerts",
            topic_name="todo-api-alerts"
        )
        
        # Add email subscription if provided
        alert_email = self.node.try_get_context("alert_email")
        if alert_email:
            self.alert_topic.add_subscription(
                Subscription(
                    protocol=SubscriptionProtocol.EMAIL,
                    endpoint=alert_email
                )
            )

    def _create_cloudwatch_dashboard(self) -> None:
        """Create comprehensive CloudWatch dashboard for monitoring"""

        self.dashboard = Dashboard(
            self, "MonitoringDashboard",
            dashboard_name="TodoApiMonitoring"
        )

        # ===========================================
        # API METRICS
        # ===========================================

        # API Health Widget
        api_health_widget = GraphWidget(
            title="API Health Overview",
            left=[
                Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Count",
                    dimensions_map={"ApiName": "TodoApi"},
                    statistic="Sum"
                ),
                Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="4XXError",
                    dimensions_map={"ApiName": "TodoApi"},
                    statistic="Sum"
                ),
                Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="5XXError",
                    dimensions_map={"ApiName": "TodoApi"},
                    statistic="Sum"
                )
            ],
            right=[
                Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Latency",
                    dimensions_map={"ApiName": "TodoApi"},
                    statistic="Average"
                )
            ],
            width=12,
            height=6
        )

        # Lambda Performance Widget
        lambda_performance_widget = GraphWidget(
            title="Lambda Performance",
            left=[
                Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={"FunctionName": "todo-api-handler"},
                    statistic="Average"
                ),
                Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={"FunctionName": "todo-api-handler"},
                    statistic="Sum"
                ),
                Metric(
                    namespace="AWS/Lambda",
                    metric_name="Throttles",
                    dimensions_map={"FunctionName": "todo-api-handler"},
                    statistic="Sum"
                )
            ],
            right=[
                Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions_map={"FunctionName": "todo-api-handler"},
                    statistic="Sum"
                )
            ],
            width=12,
            height=6
        )

        # ===========================================
        # ETL PIPELINE METRICS
        # ===========================================

        # ETL Pipeline Health Widget
        etl_pipeline_widget = GraphWidget(
            title="ETL Pipeline Health",
            left=[
                Metric(
                    namespace="AWS/Firehose",
                    metric_name="DeliveryToS3.Success",
                    dimensions_map={"DeliveryStreamName": "todo-cdc-stream"},
                    statistic="Sum"
                ),
                Metric(
                    namespace="AWS/Firehose",
                    metric_name="DeliveryToS3.DataFreshness",
                    dimensions_map={"DeliveryStreamName": "todo-cdc-stream"},
                    statistic="Average"
                )
            ],
            right=[
                Metric(
                    namespace="AWS/Glue",
                    metric_name="glue.driver.aggregate.numCompletedTasks",
                    dimensions_map={"JobName": "todo-silver-transformation"},
                    statistic="Sum"
                ),
                Metric(
                    namespace="AWS/Glue",
                    metric_name="glue.driver.aggregate.numFailedTasks",
                    dimensions_map={"JobName": "todo-silver-transformation"},
                    statistic="Sum"
                )
            ],
            width=12,
            height=6
        )

        # CDC Lambda Performance Widget
        cdc_lambda_widget = GraphWidget(
            title="CDC Lambda Performance",
            left=[
                Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={"FunctionName": "todo-cdc-processor"},
                    statistic="Average"
                ),
                Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={"FunctionName": "todo-cdc-processor"},
                    statistic="Sum"
                )
            ],
            right=[
                Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions_map={"FunctionName": "todo-cdc-processor"},
                    statistic="Sum"
                )
            ],
            width=12,
            height=6
        )

        # ===========================================
        # DATABASE METRICS
        # ===========================================

        # DynamoDB Performance Widget
        dynamodb_performance_widget = GraphWidget(
            title="DynamoDB Performance",
            left=[
                Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ConsumedReadCapacityUnits",
                    dimensions_map={"TableName": "todo-app-data"},
                    statistic="Sum"
                ),
                Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ConsumedWriteCapacityUnits",
                    dimensions_map={"TableName": "todo-app-data"},
                    statistic="Sum"
                )
            ],
            right=[
                Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ThrottledRequests",
                    dimensions_map={"TableName": "todo-app-data"},
                    statistic="Sum"
                ),
                Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="SuccessfulRequestLatency",
                    dimensions_map={"TableName": "todo-app-data"},
                    statistic="Average"
                )
            ],
            width=12,
            height=6
        )

        # ===========================================
        # CUSTOM BUSINESS METRICS
        # ===========================================

        # User Activity Widget
        user_activity_widget = GraphWidget(
            title="User Activity Metrics",
            left=[
                Metric(
                    namespace="TodoApi/CustomMetrics",
                    metric_name="TotalUsers",
                    statistic="Maximum"
                ),
                Metric(
                    namespace="TodoApi/CustomMetrics",
                    metric_name="ActiveUsers",
                    statistic="Maximum"
                )
            ],
            right=[
                Metric(
                    namespace="TodoApi/CustomMetrics",
                    metric_name="TotalTasks",
                    statistic="Maximum"
                ),
                Metric(
                    namespace="TodoApi/CustomMetrics",
                    metric_name="CompletedTasks",
                    statistic="Maximum"
                )
            ],
            width=12,
            height=6
        )

        # Task Productivity Widget
        task_productivity_widget = GraphWidget(
            title="Task Productivity",
            left=[
                Metric(
                    namespace="TodoApi/CustomMetrics",
                    metric_name="CompletionRate",
                    statistic="Maximum"
                ),
                Metric(
                    namespace="TodoApi/CustomMetrics",
                    metric_name="AvgTasksPerUser",
                    statistic="Maximum"
                )
            ],
            width=12,
            height=6
        )

        # ===========================================
        # COST MONITORING
        # ===========================================

        # Cost Overview Widget
        cost_widget = GraphWidget(
            title="Service Costs (USD)",
            left=[
                Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    dimensions_map={"Currency": "USD", "ServiceName": "AmazonDynamoDB"},
                    statistic="Maximum"
                ),
                Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    dimensions_map={"Currency": "USD", "ServiceName": "AWSLambda"},
                    statistic="Maximum"
                ),
                Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    dimensions_map={"Currency": "USD", "ServiceName": "AmazonS3"},
                    statistic="Maximum"
                )
            ],
            width=12,
            height=6
        )

        # Add widgets to dashboard in organized sections
        # Row 1: API Health
        self.dashboard.add_widgets(api_health_widget, lambda_performance_widget)

        # Row 2: ETL Pipeline
        self.dashboard.add_widgets(etl_pipeline_widget, cdc_lambda_widget)

        # Row 3: Database
        self.dashboard.add_widgets(dynamodb_performance_widget)

        # Row 4: Business Metrics
        self.dashboard.add_widgets(user_activity_widget, task_productivity_widget)

        # Row 5: Cost Monitoring
        self.dashboard.add_widgets(cost_widget)

    def _create_api_alarms(self) -> None:
        """Create alarms for API monitoring"""
        
        # High error rate alarm
        self.high_error_rate_alarm = Alarm(
            self, "HighErrorRateAlarm",
            metric=Metric(
                namespace="AWS/ApiGateway",
                metric_name="4XXError",
                dimensions_map={"ApiName": "TodoApi"}
            ),
            threshold=10,
            evaluation_periods=2,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description="High 4XX error rate detected"
        )
        
        # Lambda error alarm
        self.lambda_error_alarm = Alarm(
            self, "LambdaErrorAlarm",
            metric=Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": "todo-api-handler"}
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description="Lambda function errors detected"
        )
        
        # Lambda duration alarm
        self.lambda_duration_alarm = Alarm(
            self, "LambdaDurationAlarm",
            metric=Metric(
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions_map={"FunctionName": "todo-api-handler"}
            ),
            threshold=5000,  # 5 seconds
            evaluation_periods=2,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description="Lambda function taking too long"
        )
        
        # Add SNS actions to alarms
        sns_action = SnsAction(self.alert_topic)
        self.high_error_rate_alarm.add_alarm_action(sns_action)
        self.lambda_error_alarm.add_alarm_action(sns_action)
        self.lambda_duration_alarm.add_alarm_action(sns_action)

    def _create_etl_alarms(self) -> None:
        """Create alarms for ETL pipeline monitoring"""
        
        # Firehose delivery failure alarm
        self.firehose_delivery_failure_alarm = Alarm(
            self, "FirehoseDeliveryFailureAlarm",
            metric=Metric(
                namespace="AWS/Firehose",
                metric_name="DeliveryToS3Failed",
                dimensions_map={"DeliveryStreamName": "todo-cdc-stream"}
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description="Firehose delivery failures detected"
        )
        
        # Glue job failure alarm
        self.glue_job_failure_alarm = Alarm(
            self, "GlueJobFailureAlarm",
            metric=Metric(
                namespace="AWS/Glue",
                metric_name="glue.driver.aggregate.numFailedTasks",
                dimensions_map={"JobName": "todo-silver-transformation"}
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description="Glue job failures detected"
        )
        
        # Add SNS actions to alarms
        sns_action = SnsAction(self.alert_topic)
        self.firehose_delivery_failure_alarm.add_alarm_action(sns_action)
        self.glue_job_failure_alarm.add_alarm_action(sns_action)

    def _create_cost_alarms(self) -> None:
        """Create cost monitoring alarms"""
        
        # DynamoDB cost alarm
        self.dynamodb_cost_alarm = Alarm(
            self, "DynamoDBCostAlarm",
            metric=Metric(
                namespace="AWS/Billing",
                metric_name="EstimatedCharges",
                dimensions_map={"Currency": "USD", "ServiceName": "AmazonDynamoDB"}
            ),
            threshold=50,  # $50
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description="DynamoDB costs exceeding threshold"
        )
        
        # Lambda cost alarm
        self.lambda_cost_alarm = Alarm(
            self, "LambdaCostAlarm",
            metric=Metric(
                namespace="AWS/Billing",
                metric_name="EstimatedCharges",
                dimensions_map={"Currency": "USD", "ServiceName": "AWSLambda"}
            ),
            threshold=20,  # $20
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description="Lambda costs exceeding threshold"
        )
        
        # Add SNS actions to alarms
        sns_action = SnsAction(self.alert_topic)
        self.dynamodb_cost_alarm.add_alarm_action(sns_action)
        self.lambda_cost_alarm.add_alarm_action(sns_action)

    def _create_custom_metrics_lambda(self) -> None:
        """Create Lambda function for custom metrics collection"""
        
        # IAM role for custom metrics Lambda
        self.custom_metrics_role = Role(
            self, "CustomMetricsRole",
            assumed_by=ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Grant CloudWatch metrics permissions
        self.custom_metrics_role.add_to_policy(
            PolicyStatement(
                actions=[
                    "cloudwatch:PutMetricData"
                ],
                resources=["*"]
            )
        )
        
        # Grant DynamoDB read permissions
        self.custom_metrics_role.add_to_policy(
            PolicyStatement(
                actions=[
                    "dynamodb:Scan",
                    "dynamodb:Query"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/todo-app-data",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/todo-app-data/index/*"
                ]
            )
        )
        
        # Create custom metrics Lambda function
        self.custom_metrics_lambda = PythonFunction(
            self, "CustomMetricsLambda",
            function_name="todo-custom-metrics",
            runtime=Runtime.PYTHON_3_13,
            entry="../etl/lambda_custom_metrics",
            index="src/custom_metrics.py",
            handler="lambda_handler",
            role=self.custom_metrics_role,
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "TABLE_NAME": "todo-app-data",
                "NAMESPACE": "TodoApi/CustomMetrics"
            }
        )

    def _add_resource_tags(self) -> None:
        """Add resource tags to all monitoring components"""
        tags = {
            "Project": "todo-api-with-insights",
            "Owner": "development-team",
            "Environment": self.node.try_get_context("environment") or "development",
            "CostCenter": "engineering-platform",
        }
        for key, value in tags.items():
            Tags.of(self).add(key, value)

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for monitoring stack"""
        CfnOutput(
            self, "DashboardUrl",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
            description="CloudWatch Dashboard URL"
        )
        CfnOutput(
            self, "AlertTopicArn",
            value=self.alert_topic.topic_arn,
            description="SNS topic for alerts"
        )
        CfnOutput(
            self, "CustomMetricsFunctionName",
            value=self.custom_metrics_lambda.function_name,
            description="Lambda function for custom metrics"
        )
