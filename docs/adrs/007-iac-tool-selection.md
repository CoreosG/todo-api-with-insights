# ADR-007: Infrastructure as Code Tool Selection

**Date:** 2025-10-15
**Status:** Accepted

## Context and Problem Statement

The system requires automated infrastructure deployment to provision the complete serverless architecture defined across ADR-000 through ADR-006, including API Gateway, Lambda functions, DynamoDB, S3, Glue, Athena, CloudWatch, and associated IAM roles. The chosen IaC tool must support single-command deployment (`deploy` command), enable least-privilege IAM policies, implement comprehensive resource tagging (Project, Owner, Environment, CostCenter), and align with the Python/FastAPI stack from ADR-004 while maintaining cost optimization and serverless-first principles from ADR-000.

## Decision Drivers

* **Python Stack Integration**: Must seamlessly integrate with the Python/FastAPI codebase and enable programmatic infrastructure definition
* **AWS Service Native Support**: Need first-class support for all AWS services in the architecture (API Gateway, Lambda, DynamoDB, S3, Glue, Athena, CloudWatch, Firehose)
* **Single-Command Deployment**: Must support atomic deployments with rollback capabilities and minimal manual steps
* **Least-Privilege IAM**: Must enable granular permission policies and avoid over-privileged service roles
* **Cost Optimization**: Must support resource tagging, lifecycle policies, and cost tracking for all provisioned resources
* **Team Productivity**: Must provide clear error messages, comprehensive documentation, and maintainable code patterns

## Considered Options

* **Option A: AWS CDK** - Cloud Development Kit with Python bindings for AWS resource provisioning
* **Option B: Terraform** - Infrastructure as Code tool with AWS provider for multi-cloud deployments
* **Option C: CloudFormation** - Native AWS IaC service with JSON/YAML templates

## Decision Outcome

**Chosen option:** "AWS CDK"

### Rationale

AWS CDK provides superior Python integration for the FastAPI codebase, native AWS service support, and programmatic infrastructure definition that aligns perfectly with the serverless-first architecture. The CDK's constructs and high-level abstractions reduce boilerplate while maintaining granular control over resource configuration and security policies.

### Positive Consequences

* ✅ **Python-Native Development**: CDK applications written in Python integrate seamlessly with the FastAPI codebase and development workflow
* ✅ **AWS Service Integration**: Native support for all required services (Lambda, API Gateway, DynamoDB, S3, Glue, Athena, CloudWatch) with latest feature support
* ✅ **Type Safety**: Full type hints and IDE support for infrastructure code, reducing configuration errors
* ✅ **Single-Command Deployment**: `cdk deploy` provides atomic deployments with built-in rollback capabilities
* ✅ **Security-First Design**: Built-in support for least-privilege IAM policies and security best practices
* ✅ **Cost Optimization**: Native support for resource tagging, lifecycle policies, and CloudFormation drift detection

### Negative Consequences

* ❌ **AWS Platform Lock-in**: CDK applications are AWS-specific, limiting portability to other cloud providers
* ❌ **Learning Investment**: Team requires familiarity with CDK patterns and CloudFormation underlying mechanics
* ⚠️ **Bootstrap Requirements**: Requires CDK bootstrap stack in target AWS accounts (minimal operational overhead)

## Detailed Analysis

### Option A: AWS CDK (Chosen)

**Pros:**
- P1. **Python Integration**: Native Python SDK with full type hints and seamless import of application code
- P2. **Service Coverage**: Complete coverage of all required AWS services with latest features and best practices
- P3. **Developer Experience**: High-level constructs reduce boilerplate while maintaining granular control
- P4. **Security Integration**: Built-in security patterns and IAM policy generation with least-privilege defaults
- P5. **Deployment Pipeline**: `cdk deploy` with rollback support and comprehensive error reporting

**Cons:**
- C1. **Platform Dependency**: Applications are tightly coupled to AWS services and CDK framework
- C2. **Bootstrap Overhead**: Requires one-time CDK bootstrap in each target environment

**Evaluation:** **5/5 - Optimal Fit**. Provides the best balance of developer productivity, AWS integration, and operational capabilities for the serverless architecture.

### Option B: Terraform

**Pros:**
- P1. **Multi-Cloud Support**: Single tool for AWS and potential future cloud provider migrations
- P2. **Mature Ecosystem**: Extensive provider ecosystem with comprehensive AWS service coverage
- P3. **State Management**: Sophisticated state management with locking and remote backends
- P4. **Community Resources**: Large community with extensive modules and learning resources

**Cons:**
- C1. **Python Integration**: HCL syntax doesn't integrate as naturally with Python/FastAPI codebase
- C2. **AWS Service Parity**: Some AWS services may have delayed feature support compared to CDK
- C3. **Deployment Complexity**: `terraform apply` requires separate planning and application steps
- C4. **Security Patterns**: Manual implementation of security best practices vs. CDK's built-in patterns

**Evaluation:** **3/5 - Good Alternative**. Excellent for multi-cloud scenarios but provides less seamless integration with the Python-centric development workflow.

### Option C: CloudFormation

**Pros:**
- P1. **Native AWS Service**: Direct integration with AWS management console and service quotas
- P2. **No Bootstrap Required**: No additional setup beyond standard AWS account configuration
- P3. **Drift Detection**: Built-in detection of manual configuration changes

**Cons:**
- C1. **Template Complexity**: JSON/YAML templates become unwieldy for complex architectures
- C2. **Python Integration**: Limited integration with Python codebase and development workflow
- C3. **Error Handling**: Less developer-friendly error messages and debugging capabilities
- C4. **Maintenance Overhead**: Manual template management for large, evolving infrastructures

**Evaluation:** **2/5 - Limited Fit**. While native to AWS, lacks the developer experience and Python integration required for the FastAPI-centric development team.

## Infrastructure Architecture Implementation

### CDK Application Structure

**Core CDK Application (`infra/`):**
```python
# infra/app.py
from aws_cdk import App, Environment
from stacks.api_stack import ApiStack
from stacks.data_stack import DataStack
from stacks.etl_stack import EtlStack
from stacks.monitoring_stack import MonitoringStack

app = App()

# Environment configuration
env = Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"]
)

# Infrastructure stacks
api_stack = ApiStack(app, "TodoApiStack", env=env)
data_stack = DataStack(app, "TodoDataStack", env=env)
etl_stack = EtlStack(app, "TodoEtlStack", env=env)
monitoring_stack = MonitoringStack(app, "TodoMonitoringStack", env=env)

app.synth()
```

### Component Provisioning Strategy

**API Stack (from ADR-004):**
- **API Gateway**: REST API with CORS, throttling, and request validation
- **Lambda Functions**: FastAPI application deployment with provisioned concurrency
- **Cognito User Pool**: Authentication with JWT token configuration

**Data Stack (from ADR-001/ADR-003):**
- **DynamoDB Table**: Single-table design with GSI configuration and on-demand capacity
- **DynamoDB Streams**: CDC configuration for ETL pipeline triggers
- **IAM Roles**: Least-privilege policies for Lambda and API Gateway access

**ETL Stack (from ADR-005):**
- **S3 Buckets**: Bronze/Silver/Gold layer buckets with lifecycle policies
- **Firehose Delivery Streams**: Log and CDC data ingestion with Parquet conversion
- **Glue Jobs**: Spark-based transformation jobs with incremental processing
- **Athena Workgroups**: Query optimization and cost controls

**Monitoring Stack (from ADR-006):**
- **CloudWatch Dashboard**: Unified API and ETL health visualization
- **Log Groups**: Structured logging configuration with retention policies
- **Alarms**: Critical and warning thresholds with SNS notification topics
- **Custom Metrics**: Business metric collection and tracking

### Security and Cost Implementation

**Resource Tagging Strategy:**
```python
# Common tagging for all resources
def apply_common_tags(resource) -> None:
    Tags.of(resource).add("Project", "todo-api-with-insights")
    Tags.of(resource).add("Owner", "development-team")
    Tags.of(resource).add("Environment", app.node.try_get_context("environment") or "development")
    Tags.of(resource).add("CostCenter", "engineering-platform")
```

**Least-Privilege IAM Policies:**
```python
# Lambda execution role with minimal permissions
lambda_role = iam.Role(
    self, "ApiHandlerRole",
    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
    ]
)

# DynamoDB access policy
dynamodb_policy = iam.PolicyDocument(
    statements=[
        iam.PolicyStatement(
            actions=["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"],
            resources=[table.table_arn],
            conditions={"StringEquals": {"dynamodb:LeadingKeys": ["USER#${aws:userid}"]}}
        )
    ]
)
```

**Cost Optimization Features:**
- **S3 Lifecycle Policies**: Automatic transition to Glacier after 90 days
- **DynamoDB On-Demand Billing**: Pay-per-request scaling with usage monitoring
- **Lambda Reserved Concurrency**: Prevent cost overruns during traffic spikes
- **CloudWatch Cost Alarms**: Budget monitoring and spend alerts

## Integration with Architecture Components

### API Gateway Integration (ADR-004)
- REST API definition with method-level authorization
- CORS configuration for web application access
- Request/response logging with sampling for cost optimization

### Lambda Functions Integration (ADR-004/ADR-005)
- FastAPI application packaging and deployment configuration
- Environment variable management for database and service endpoints
- Cold start optimization with provisioned concurrency where needed

### Database Integration (ADR-001/ADR-003)
- DynamoDB table creation with single-table design and GSI configuration
- Stream specification for CDC processing
- Backup configuration and point-in-time recovery settings

### ETL Pipeline Integration (ADR-005)
- S3 bucket creation with appropriate encryption and lifecycle policies
- Firehose delivery stream configuration with data transformation
- Glue job definitions with Spark runtime and connection parameters

### Monitoring Integration (ADR-006)
- CloudWatch dashboard creation with pre-configured widgets
- Log group setup with appropriate retention and subscription filters
- Alarm creation with notification channels and escalation policies

## Deployment and Operations Strategy

**Single-Command Deployment:**
```bash
# Bootstrap CDK (one-time per environment)
cdk bootstrap

# Deploy all infrastructure
cdk deploy --all

# View proposed changes
cdk diff

# Destroy infrastructure (for teardown)
cdk destroy --all
```

**Environment Management:**
- **Development**: Feature branches deploy to isolated environments
- **Staging**: Integration testing environment with production-like configuration
- **Production**: Main branch deployments with additional approval requirements

**Rollback Strategy:**
- CDK maintains deployment history for easy rollback to previous versions
- CloudFormation drift detection identifies manual changes
- Automated backup verification for critical data resources

## Validation Approach

1. **Deployment Testing**: Validate single-command deployment and rollback capabilities across environments
2. **Resource Verification**: Confirm all architecture components are properly provisioned and configured
3. **Security Validation**: Audit IAM policies for least-privilege compliance and remove over-permissions
4. **Cost Impact Assessment**: Monitor resource costs during initial deployment and establish budget baselines
5. **Integration Testing**: Verify component interactions (API Gateway → Lambda → DynamoDB → ETL pipeline)
6. **Teardown Validation**: Confirm complete infrastructure removal with `cdk destroy` for cost control

## Links

* [Related ADR-000: Architecture Overview](000-architecture-overview.md)
* [Related ADR-001: Database Selection](001-database-selection.md)
* [Related ADR-002: Database Capacity Mode Selection](002-database-capacity-mode-selection.md)
* [Related ADR-003: Data Modeling Approach](003-data-modeling-approach.md)
* [Related ADR-005: ETL Method](005-etl-method.md)
* [Related ADR-006: Monitoring and Observability](006-monitoring-observability.md)
* [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
* [CDK Best Practices](https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html)

## References

* [AWS CDK Workshop](https://cdkworkshop.com/)
* [CDK Security Best Practices](https://docs.aws.amazon.com/cdk/v2/guide/security.html)
* [Infrastructure as Code Patterns](https://docs.aws.amazon.com/whitepapers/latest/introduction-devops-aws/infrastructure-as-code.html)
