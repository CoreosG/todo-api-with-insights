import os
from aws_cdk import Duration, Stack, RemovalPolicy, CfnOutput, Tags
from aws_cdk.aws_apigatewayv2 import (
    HttpApi, HttpMethod, HttpStage, 
    CorsPreflightOptions, CorsHttpMethod # not used but would
)
from aws_cdk.aws_apigatewayv2_authorizers import HttpJwtAuthorizer
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.aws_cognito import (
    AuthFlow, SignInAliases, StandardAttributes, UserPool, 
    UserPoolClient, StandardAttribute
)
from aws_cdk.aws_iam import Role, ServicePrincipal, PolicyStatement, ManagedPolicy
from aws_cdk.aws_dynamodb import Table
from constructs import Construct

class ApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, table: Table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Save table reference
        self.table = table
        # Create Cognito User Pool
        self._create_cognito_user_pool()
        # Create Cognito User Pool Client
        self._create_cognito_user_pool_client()
        # Create IAM Role
        self._create_iam_role()
        # Create IAM Policy
        self._create_iam_policy()
        # Create IAM Role Policy
        self._create_iam_role_policy()
        # Create Lambda Function
        self._create_lambda_function()
        # Create API Gateway
        self._create_api_gateway()
        # Create Authorizer for API Gateway
        self._create_authorizer()
        # Create API Routes
        self._create_api_routes()
        # Create API Gateway Stage
        #self._create_api_gateway_stage() -- v2 creates default stage
        # Add resource tags
        self._add_resource_tags()
        # Create cloudformation outputs
        self._create_outputs()

    # Create Cognito User Pool
    def _create_cognito_user_pool(self) -> None:
        # Create Cognito User Pool
        self.user_pool = UserPool(
            self, "TodoUserPool",
            user_pool_name="todo-api-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases=SignInAliases(
                email=True,
                username=True,
                phone=False,
                ),
            auto_verify={"email": True, "phone": False},
            standard_attributes=StandardAttributes(
                email=StandardAttribute(required=True, mutable=True)
            ),
            removal_policy=RemovalPolicy.DESTROY, # DESTROY only for dev.
        )
    # Create Cognito User Pool Client
    def _create_cognito_user_pool_client(self) -> None:
        # Create Cognito User Pool Client
        self.user_pool_client = UserPoolClient(
            self, "TodoUserPoolClient",
            user_pool=self.user_pool,
            auth_flows=AuthFlow(
                user_srp=True, # User SRP authentication flow
                admin_user_password=True, # Admin user password authentication flow
                user_password=True, # User password authentication flow for testing
            ),
            access_token_validity=Duration.hours(1), # Access token validity duration
            id_token_validity=Duration.hours(1), # Token validity duration
            refresh_token_validity=Duration.days(30), # Refresh token validity duration
            prevent_user_existence_errors=True, # Prevent user existence errors
        )

    # Create IAM Role
    def _create_iam_role(self) -> None:
        # Create IAM Role
        self.lambda_role = Role(
            self, "LambdaExecutionRole",
            role_name="todo-api-role",
            assumed_by=ServicePrincipal("lambda.amazonaws.com"),
                managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )
    
    # Create IAM Policy
    def _create_iam_policy(self) -> None:
        # Create IAM Policy for DynamoDB access
        self.dynamodb_policy = PolicyStatement(
            actions=[
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
            ],
            resources=[
                self.table.table_arn,
                f"{self.table.table_arn}/index/*" # GSI
            ],
            conditions={
                "StringEquals": {
                    "dynamodb:LeadingKeys": ["USER#${cognito-identity.amazonaws.com:sub}"]
                }
            }
        )

    # Create IAM Role Policy
    def _create_iam_role_policy(self) -> None:
        # Attach DynamoDB Policy to Lambda Role
        self.lambda_role.add_to_policy(self.dynamodb_policy)

    # Create Lambda Function
    def _create_lambda_function(self) -> None:
        # Create Lambda function with FastAPI application
        self.lambda_function = PythonFunction(
            self, "TodoApiFunction",
            function_name="todo-api-function",
            runtime=Runtime.PYTHON_3_13,
            entry="../api",
            index="lambda_entry.py",
            handler="lambda_handler",
            environment={
                "DYNAMODB_TABLE_NAME": self.table.table_name,
                "ENVIRONMENT": self.node.try_get_context("environment") or "development",
                "USE_LOCAL_DYNAMODB": "false", # false for production, just to be sure.
                "LOCAL_USER": "false", # false for production, just to be sure.
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "DEBUG": "true", # true for development, in this challenge.
            },
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
             bundling={
               "asset_excludes": [
                   "__pycache__",
                   "*.pyc", 
                   "venv-api",
                   "tests",
                   "Makefile",
                   "pyproject.toml", 
                   "mypy.ini",
                   "requirements-dev.txt",
                   ".pytest_cache",
                   ".mypy_cache",
                   ".ruff_cache",
                   "*.md",
                   ".git*"
               ],
           },
        )
    
   # Create API Gateway
    def _create_api_gateway(self) -> None:
        # Create REST API Gateway
        self.api = HttpApi(
            self, "TodoApiGateway",
            api_name="todo-api-gateway",  # Changed from rest_api_name
            description="Todo API with Cognito authentication",
            cors_preflight=CorsPreflightOptions(
                allow_origins=["*"],  # allow all origins for development
                allow_methods=[
                    CorsHttpMethod.GET,
                    CorsHttpMethod.POST,
                    CorsHttpMethod.PUT,
                    CorsHttpMethod.DELETE,
                    CorsHttpMethod.OPTIONS
                ],  # Specify allowed HTTP methods using CorsHttpMethod enum
                allow_headers=["*"],  # allow all headers for development
                allow_credentials=False,  # Must be False when allow_origins is "*"
                max_age=Duration.seconds(600),
            ),

        )

    # Create Authorizer for API Gateway
    def _create_authorizer(self) -> None:
        # Create Cognito Authorizer for API Gateway
        self.authorizer = HttpJwtAuthorizer(
            "CognitoAuthorizer",
            self.user_pool.user_pool_provider_url,
            jwt_audience=[self.user_pool_client.user_pool_client_id]
        )
    
    # Create API Routes
    def _create_api_routes(self) -> None:
        # Create Lambda Proxy Integration
        lambda_integration = HttpLambdaIntegration(
            "LambdaIntegration",
            self.lambda_function
            )

        # Health endpoint (public)
        self.api.add_routes(
            path="/health",
            methods=[HttpMethod.GET],
            integration=lambda_integration,
        )
        
        # Proxy all other routes to Lambda function (protected)
        self.api.add_routes(
            path="/{proxy+}",
            methods=[HttpMethod.ANY],
            integration=lambda_integration,
            authorizer=self.authorizer,
        )

    # Create API Gateway Stage
    def _create_api_gateway_stage(self) -> None:
        # Create API Gateway Stage
        self.stage = HttpStage(
            self, "TodoApiStage",
            http_api=self.api,
            stage_name="dev",
        )
    
    # Add resource tags
    def _add_resource_tags(self) -> None:
        tags = {
            "Project": "todo-api-with-insights",
            "Owner": "development-team",
            "Environment": self.node.try_get_context("environment") or "development",
            "CostCenter": "engineering-platform",
        }
        for key, value in tags.items():
            Tags.of(self).add(key, value)

    # Create cloudformation outputs
    def _create_outputs(self) -> None:
        # Create cloudformation outputs
        CfnOutput(
            self, "ApiEndpoint",
            value=self.api.url,
            description="The API endpoint of the API Gateway"
        )
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="The ID of the Cognito User Pool"
        )
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="The ID of the Cognito User Pool Client"
        )
        CfnOutput(
            self, "LambdaFunctionName",
            value=self.lambda_function.function_name,
            description="The name of the Lambda Function"
        )
