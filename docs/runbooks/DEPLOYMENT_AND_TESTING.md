# Deployment and Testing Runbook

## Overview

This runbook provides a comprehensive guide for deploying the Todo API with Insights infrastructure and performing end-to-end testing including user creation, authentication, and API operations. Both Windows (PowerShell) and Unix/Linux/Mac (Bash) testing scripts are available.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Deployment](#infrastructure-deployment)
3. [Testing Health Endpoints](#testing-health-endpoints)
4. [Cognito User Management](#cognito-user-management)
5. [API Authentication and Testing](#api-authentication-and-testing)
6. [Troubleshooting](#troubleshooting)
7. [Cleanup](#cleanup)

## Prerequisites

### 1. AWS Setup

- **AWS CLI** installed and configured with appropriate credentials
- **AWS Account** with necessary permissions (CDK deployment, Cognito, Lambda, API Gateway, DynamoDB)
- **CDK CLI** installed: `npm install -g aws-cdk`

### 2. Environment Setup

```bash
# Navigate to project root
cd todo-api-with-insights

# Activate Python virtual environment (if using)
# source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\Activate.ps1  # Windows

# Verify AWS CLI configuration
aws sts get-caller-identity

# Verify CDK installation
cdk --version
```

### 3. Required Tools

- **curl** or **Postman** for API testing
- **jq** for JSON parsing (optional but recommended)
- **Python 3.8+** for local development

## Infrastructure Deployment

### Step 1: Bootstrap CDK (First Time Only)

```bash
# Bootstrap CDK in your AWS account (one-time setup per region)
cdk bootstrap aws://YOUR-ACCOUNT-ID/us-east-1
```

### Step 2: Deploy Data Stack

Deploy the DynamoDB infrastructure first:

```bash
# Navigate to infrastructure directory
cd infra

# Activate the CDK virtual environment
.\venv-infra\Scripts\Activate.ps1  # Windows
# source venv-infra/bin/activate    # Linux/Mac

# Deploy data stack (DynamoDB table)
cdk deploy TodoDataStack --require-approval never
```

**Expected Output:**
```
✅ TodoDataStack

Outputs:
TodoDataStack.ExportsOutputFnGetAttTodoTable585F1D6BArn557654A3 = arn:aws:dynamodb:us-east-1:YOUR-ACCOUNT:table/todo-app-data
TodoDataStack.ExportsOutputRefTodoTable585F1D6BBAE41B2C = todo-app-data
```

**Verification:**
- Check AWS Console: DynamoDB → Tables → `todo-app-data` should exist
- Table should have partition key `PK` and sort key `SK`
- Point-in-time recovery should be enabled

### Step 3: Deploy API Stack

Deploy the API infrastructure (Cognito, API Gateway, Lambda):

```bash
# Deploy API stack (includes Cognito, API Gateway, Lambda)
cdk deploy TodoApiStack --require-approval never
```

**Expected Output:**
```
✅ TodoApiStack

Outputs:
TodoApiStack.ApiUrl = https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/
TodoApiStack.UserPoolId = us-east-1_YOUR-USER-POOL-ID
TodoApiStack.UserPoolClientId = YOUR-CLIENT-ID
```

**Verification:**
- **API Gateway**: Check AWS Console → API Gateway → APIs → `todo-api`
- **Cognito**: Check AWS Console → Cognito → User pools → `todo-api-user-pool`
- **Lambda**: Check AWS Console → Lambda → Functions → `todo-api-function`

## Testing Health Endpoints

### Step 4: Test Public Health Endpoint

The `/health` endpoint should be publicly accessible without authentication:

```bash
# Test health endpoint (no authentication required)
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health

# Or using PowerShell
Invoke-WebRequest -Uri https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health -Method GET
```

**Expected Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "production"
}
```

**Troubleshooting:**
- If you get `{"message":"Not Found"}`, check API Gateway routes in AWS Console
- Verify Lambda function logs in CloudWatch

## Cognito User Management

### Step 5: Create a Cognito User

Create a test user in the Cognito User Pool:

```bash
# Set variables from CDK output 
USER_POOL_ID="us-east-1_YOUR-USER-POOL-ID"
CLIENT_ID="YOUR-CLIENT-ID"
USERNAME="testuser@example.com"
PASSWORD="TempPassword123!"
FIRST_NAME="Test"
LAST_NAME="User"

# Create user in Cognito
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --user-attributes Name=email,Value=$USERNAME Name=given_name,Value=$FIRST_NAME Name=family_name,Value=$LAST_NAME \
  --message-action SUPPRESS \
  --region us-east-1

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --password $PASSWORD \
  --permanent \
  --region us-east-1
```

**Verification:**
```bash
# List users to verify creation
aws cognito-idp list-users --user-pool-id $USER_POOL_ID --region us-east-1
```

## API Authentication and Testing

### Step 6: Authenticate and Get Token

Get an IdToken for API calls (required by API Gateway Cognito authorizer):

```bash
# Authenticate user and get tokens
AUTH_RESPONSE=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD \
  --region us-east-1)

# Extract Id token
ID_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.IdToken')

echo "IdToken length: ${#ID_TOKEN}"
```

**Note:** Store the access token securely for API calls.

### Step 7: Test API Endpoints with Authentication

#### Create a Task

```bash
# Create a task
CREATE_TASK_RESPONSE=$(curl -X POST \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-idempotencykey-34343" \
  -d '{
    "title": "Test Task",
    "description": "This is a test task created via API",
    "priority": "medium",
    "category": "testing"
  }')

echo "Create Task Response:"
echo $CREATE_TASK_RESPONSE | jq .
```

**Expected Response:**
```json
{
  "id": "task-uuid",
  "title": "Test Task",
  "description": "This is a test task created via API",
  "status": "pending",
  "priority": "medium",
  "category": "testing",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

#### Get Tasks

```bash
# Get all tasks for the user
GET_TASKS_RESPONSE=$(curl -X GET \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer $ID_TOKEN")

echo "Get Tasks Response:"
echo $GET_TASKS_RESPONSE | jq .
```

**Expected Response:**
```json
{
  "tasks": [
    {
      "id": "task-uuid",
      "title": "Test Task",
      "description": "This is a test task created via API",
      "status": "pending",
      "priority": "medium",
      "category": "testing",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### Test Authentication (Unauthorized Access)

```bash
# Try to access API without token (should fail)
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks

# Expected: 401 Unauthorized
```

## Additional API Testing

### Step 8: Optional Scripted Testing and Other Endpoints

You can also use the provided scripts for end-to-end testing with environment-based configuration. Both Windows (PowerShell) and Unix/Linux/Mac (Bash) versions are available:

#### Windows (PowerShell):

```powershell
# From project root
cd infra\scripts

# Option 1: Set variables via OS environment
$Env:API_ENDPOINT = "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
$Env:USER_POOL_ID = "us-east-1_YOUR-USER-POOL-ID"
$Env:CLIENT_ID = "YOUR-CLIENT-ID"
$Env:REGION = "us-east-1"
# Optional AWS profile
# $Env:AWS_PROFILE = "your-profile-name"

# Option 2: Create a .env.txt file in this folder (OS env takes precedence)
# API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
# REGION=us-east-1
# USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
# CLIENT_ID=YOUR-CLIENT-ID
# PASSWORD=TempPassword1!
# COGNITO_USERNAME=
# COGNITO_EMAIL=

$Env:NON_INTERACTIVE = "1"
./test-api.ps1
```

#### Linux/Mac (Bash):

```bash
# From project root
cd infra/scripts

# Option 1: Set variables via OS environment
export API_ENDPOINT="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
export USER_POOL_ID="us-east-1_YOUR-USER-POOL-ID"
export CLIENT_ID="YOUR-CLIENT-ID"
export REGION="us-east-1"
# Optional AWS profile
# export AWS_PROFILE="your-profile-name"

# Option 2: Create a .env or .env.txt file in this folder (OS env takes precedence)
# API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
# REGION=us-east-1
# USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
# CLIENT_ID=YOUR-CLIENT-ID
# PASSWORD=TempPassword1!
# COGNITO_USERNAME=
# COGNITO_EMAIL=

export NON_INTERACTIVE=1
./test-api.sh
```

**✅ Scripts Status: FULLY WORKING** - Both scripts successfully automate complete API layer testing with IdToken authentication.

#### Create User

```bash
# Create another user <Users are generated automatically when calling the API>
# This endpoint is redundant since users are created seamlessly when callin the API
CREATE_USER_RESPONSE=$(curl -X POST \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/users \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "name": "New User"
  }')

echo "Create User Response:"
echo $CREATE_USER_RESPONSE | jq .
```

#### Get User Tasks by Status

```bash
# Get pending tasks only
PENDING_TASKS=$(curl -X GET \
  "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks?status=pending" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "Pending Tasks:"
echo $PENDING_TASKS | jq .
```

## Verification Steps

### Step 9: Verify Data Persistence

1. **Check DynamoDB Data:**
   ```bash
   # Query DynamoDB table
   aws dynamodb scan --table-name todo-app-data --region us-east-1 | jq '.Items'
   ```

2. **Check CloudWatch Logs:**
   ```bash
   # View Lambda function logs
   aws logs tail /aws/lambda/todo-api-function --region us-east-1 --follow
   ```

3. **Check API Gateway Metrics:**
   - AWS Console → API Gateway → APIs → `todo-api` → Monitor

## Troubleshooting

### Common Issues

#### 1. "Not Found" Error on Health Endpoint
**Symptoms:** `/health` returns `{"message":"Not Found"}`

**Causes:**
- API Gateway route not configured correctly
- Lambda function not deployed properly

**Solutions:**
```bash
# Check API Gateway routes
aws apigatewayv2 get-routes --api-id YOUR-API-ID --region us-east-1

# Check Lambda function logs
aws logs tail /aws/lambda/todo-api-function --region us-east-1

# Redeploy API stack
cdk deploy TodoApiStack --require-approval never
```

#### 2. Authentication Failures
**Symptoms:** `401 Unauthorized` or token-related errors

**Causes:**
- Invalid or expired token
- Incorrect User Pool/Client configuration

**Solutions:**
```bash
# Verify Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --region us-east-1

# Regenerate token
# Follow Step 6 again
```

#### 3. Lambda Function Errors
**Symptoms:** `500 Internal Server Error`

**Causes:**
- Import errors in Lambda function
- Missing dependencies

**Solutions:**
```bash
# Check Lambda function logs for detailed error messages
aws logs tail /aws/lambda/todo-api-function --region us-east-1

# Verify function configuration
aws lambda get-function --function-name todo-api-function --region us-east-1
```

#### 4. DynamoDB Access Issues
**Symptoms:** Database operation failures

**Causes:**
- IAM permissions
- Table not created

**Solutions:**
```bash
# Check table exists
aws dynamodb describe-table --table-name todo-app-data --region us-east-1

# Check IAM role permissions
aws iam get-role --role-name TodoApiStack-ApiHandlerRole --region us-east-1
```

### Debugging Commands

```bash
# Check all API Gateway APIs
aws apigatewayv2 get-apis --region us-east-1

# Check Lambda function configuration
aws lambda get-function --function-name todo-api-function --region us-east-1 | jq '.Configuration'

# Check CloudWatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/lambda --region us-east-1

# Check Cognito user pools
aws cognito-idp list-user-pools --max-results 10 --region us-east-1

# Check DynamoDB tables
aws dynamodb list-tables --region us-east-1
```

## Cleanup

### Destroy Infrastructure

**⚠️ Warning:** This will delete all data and cannot be undone.

```bash
# Destroy API stack first (due to dependencies)
cdk destroy TodoApiStack

# Destroy data stack
cdk destroy TodoDataStack

# Clean up CDK bootstrap (if needed)
cdk destroy --all
```

### Clean Up Cognito Users

```bash
# Delete test users
aws cognito-idp admin-delete-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --region us-east-1
```

## Security Considerations

1. **Token Security:** Never log or expose access tokens in logs
2. **User Data:** The runbook creates test users - delete them after testing
3. **Permissions:** Ensure your AWS credentials have minimal required permissions
4. **Cost Monitoring:** Monitor AWS costs during testing, especially Lambda and API Gateway usage

## Performance Benchmarks

- **Health Check Response:** < 100ms
- **API Response Time:** < 500ms for typical operations
- **Lambda Cold Start:** < 1 second (with provisioned concurrency if needed)

## ETL Pipeline Testing

### ETL Pipeline Overview

The ETL (Extract, Transform, Load) pipeline processes data from DynamoDB streams and creates a data lake with Bronze, Silver, and Gold layers for analytics and reporting.

### ETL Components

- **Bronze Layer**: Raw data from DynamoDB streams and application logs
- **Silver Layer**: Cleaned and transformed data from Bronze layer
- **Gold Layer**: Analytics-optimized data with business metrics and KPIs
- **Kinesis Firehose**: Real-time data ingestion from DynamoDB streams
- **AWS Glue**: ETL jobs for data transformation
- **S3 Buckets**: Data lake storage (Bronze, Silver, Gold layers)
- **Athena**: Query engine for analytics
- **Lambda Functions**: CDC processing and custom metrics collection

### ETL Testing Steps

#### 1. Deploy ETL Stack

```bash
# Navigate to infrastructure directory
cd infra

# Deploy ETL stack (includes S3, Firehose, Glue, Athena)
cdk deploy TodoEtlStack --require-approval never
```

**Expected Output:**
```
✅ TodoEtlStack

Outputs:
TodoEtlStack.BronzeBucketName = todo-bronze-YOUR-ACCOUNT-us-east-1
TodoEtlStack.SilverBucketName = todo-silver-YOUR-ACCOUNT-us-east-1
TodoEtlStack.GoldBucketName = todo-gold-YOUR-ACCOUNT-us-east-1
TodoEtlStack.FirehoseStreamName = todo-cdc-stream
TodoEtlStack.GlueDatabaseName = todo_analytics
TodoEtlStack.AthenaWorkgroupName = todo-analytics-workgroup
```

#### 2. Deploy Monitoring Stack

```bash
# Deploy monitoring stack (includes CloudWatch dashboard and alarms)
cdk deploy TodoMonitoringStack --require-approval never
```

**Expected Output:**
```
✅ TodoMonitoringStack

Outputs:
TodoMonitoringStack.DashboardName = todo-api-dashboard
TodoMonitoringStack.AlertTopicArn = arn:aws:sns:us-east-1:YOUR-ACCOUNT:todo-api-alerts
```

#### 3. Test ETL Pipeline

##### Enable DynamoDB Streams

```bash
# Enable DynamoDB streams on the table
aws dynamodb update-table \
  --table-name todo-app-data \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --region us-east-1
```

##### Create Test Data

The ETL testing script (`test-etl.ps1` for Windows or `test-etl.sh` for Linux/Mac) automates the creation of test data to trigger CDC events. It creates multiple users, generates tasks for each user, and performs multiple updates to each task to simulate real-world usage patterns.

**Configuration Setup:**

Create a `.env` or `.env.txt` file in the `infra/scripts/` directory with the same configuration as the API testing:

```bash
# infra/scripts/.env
API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
REGION=us-east-1
USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
CLIENT_ID=YOUR-CLIENT-ID
PASSWORD=TempPassword1!
# Optional: Customize ETL data generation
NUM_USERS=3
TASKS_PER_USER=5
UPDATES_PER_TASK=3
```

**Windows (PowerShell):**

```powershell
# Navigate to scripts directory
cd infra\scripts

# Option 1: Set variables via OS environment
$Env:API_ENDPOINT = "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
$Env:USER_POOL_ID = "us-east-1_YOUR-USER-POOL-ID"
$Env:CLIENT_ID = "YOUR-CLIENT-ID"
$Env:REGION = "us-east-1"
# Optional AWS profile
# $Env:AWS_PROFILE = "your-profile-name"

# Option 2: Create .env.txt file in this folder (OS env takes precedence)
# API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
# REGION=us-east-1
# USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
# CLIENT_ID=YOUR-CLIENT-ID
# PASSWORD=TempPassword1!
# NUM_USERS=3
# TASKS_PER_USER=5
# UPDATES_PER_TASK=3

# Run ETL testing script
./test-etl.ps1
```

**Linux/Mac (Bash):**

```bash
# Navigate to scripts directory
cd infra/scripts

# Option 1: Set variables via OS environment
export API_ENDPOINT="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
export USER_POOL_ID="us-east-1_YOUR-USER-POOL-ID"
export CLIENT_ID="YOUR-CLIENT-ID"
export REGION="us-east-1"
# Optional AWS profile
# export AWS_PROFILE="your-profile-name"

# Option 2: Create .env file in this folder (OS env takes precedence)
# API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
# REGION=us-east-1
# USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
# CLIENT_ID=YOUR-CLIENT-ID
# PASSWORD=TempPassword1!
# NUM_USERS=3
# TASKS_PER_USER=5
# UPDATES_PER_TASK=3

# Run ETL testing script
./test-etl.sh
```

**Script Features:**
- Creates multiple Cognito users automatically
- Generates tasks for each user with varied priorities and categories
- Performs multiple updates to each task to simulate real usage
- Uses unique idempotency keys to avoid duplicate processing
- Provides detailed progress reporting and statistics

**Expected Output:**
```
[*] Starting ETL Testing...
API Endpoint: https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
Users to create: 3
Tasks per user: 5
Updates per task: 3

[STEP 1] Creating Users and Obtaining Tokens...
Creating user 1/3...
Setting up user: etl-user-1-20250101120000 (etl.user1.1234567890@example.com)
Token obtained successfully
User 1 ready with token

[STEP 2] Creating and Updating Tasks for ETL Data Generation...
Processing user 1 (etl-user-1-20250101120000)...
Creating task 1/5...
Created task: task-uuid-1
Task task-uuid-1 updated (1/3)
Task task-uuid-1 updated (2/3)
Task task-uuid-1 updated (3/3)
...

[STEP 3] Verifying Data Generation in DynamoDB...
Current table statistics:
  Total items: 50
  User records: 3
  Task records: 15
  Idempotency records: 18

[COMPLETE] ETL Testing Complete!
Users created: 3
Tasks created: 15
Task updates performed: 45
Expected CDC events generated: 63
```

**This will generate DynamoDB stream events that trigger the ETL pipeline:**
- Bronze layer: Raw CDC events from DynamoDB streams
- Silver layer: Cleaned and transformed user/task data
- Gold layer: Analytics and business metrics

##### Monitor ETL Pipeline

```bash
# Check S3 buckets for data
aws s3 ls s3://todo-bronze-YOUR-ACCOUNT-us-east-1/cdc/ --region us-east-1
aws s3 ls s3://todo-silver-YOUR-ACCOUNT-us-east-1/ --region us-east-1
aws s3 ls s3://todo-gold-YOUR-ACCOUNT-us-east-1/ --region us-east-1

# Check CloudWatch logs for ETL jobs
aws logs tail /aws/lambda/todo-cdc-function --region us-east-1
aws logs tail /aws/lambda/todo-custom-metrics-function --region us-east-1
```

##### Run Glue Jobs

```bash
# Start Silver transformation job
aws glue start-job-run \
  --job-name todo-silver-transformation \
  --arguments '{
    "--BRONZE_BUCKET": "todo-bronze-YOUR-ACCOUNT-us-east-1",
    "--SILVER_BUCKET": "todo-silver-YOUR-ACCOUNT-us-east-1",
    "--DATABASE_NAME": "todo_analytics"
  }' \
  --region us-east-1

# Start Gold analytics job
aws glue start-job-run \
  --job-name todo-gold-analytics \
  --arguments '{
    "--SILVER_BUCKET": "todo-silver-YOUR-ACCOUNT-us-east-1",
    "--GOLD_BUCKET": "todo-gold-YOUR-ACCOUNT-us-east-1",
    "--DATABASE_NAME": "todo_analytics"
  }' \
  --region us-east-1
```

##### Query Analytics Data

```bash
# Query user analytics
aws athena start-query-execution \
  --query-string "SELECT * FROM todo_analytics.user_analytics LIMIT 10" \
  --work-group todo-analytics-workgroup \
  --result-configuration 'OutputLocation=s3://todo-gold-YOUR-ACCOUNT-us-east-1/athena-results/' \
  --region us-east-1

# Query task analytics
aws athena start-query-execution \
  --query-string "SELECT * FROM todo_analytics.task_analytics LIMIT 10" \
  --work-group todo-analytics-workgroup \
  --result-configuration 'OutputLocation=s3://todo-gold-YOUR-ACCOUNT-us-east-1/athena-results/' \
  --region us-east-1
```

#### 4. Monitor ETL Health

##### Check CloudWatch Dashboard

```bash
# Open CloudWatch dashboard in AWS Console
# Navigate to CloudWatch → Dashboards → todo-api-dashboard
# Review ETL metrics and health
```

##### Check Alarms

```bash
# List CloudWatch alarms
aws cloudwatch describe-alarms --region us-east-1 | jq '.MetricAlarms[] | select(.AlarmName | contains("todo"))'
```

##### Check Custom Metrics

```bash
# List custom metrics
aws cloudwatch list-metrics --namespace "TodoApi/CustomMetrics" --region us-east-1
```

### ETL Troubleshooting

#### Common ETL Issues

1. **No Data in Bronze Layer**
   - Check DynamoDB streams are enabled
   - Verify Lambda function logs
   - Check Firehose delivery stream status

2. **Glue Job Failures**
   - Check Glue job logs in CloudWatch
   - Verify S3 permissions
   - Check data format compatibility

3. **Athena Query Failures**
   - Verify Glue table schemas
   - Check S3 data format
   - Verify Athena workgroup permissions

#### ETL Debugging Commands

```bash
# Check DynamoDB streams
aws dynamodb describe-table --table-name todo-app-data --region us-east-1 | jq '.Table.StreamSpecification'

# Check Firehose delivery stream
aws firehose describe-delivery-stream --delivery-stream-name todo-cdc-stream --region us-east-1

# Check Glue jobs
aws glue get-jobs --region us-east-1 | jq '.JobList[] | select(.Name | contains("todo"))'

# Check Athena workgroup
aws athena get-work-group --work-group todo-analytics-workgroup --region us-east-1
```

### ETL Cleanup

```bash
# Destroy ETL stack
cdk destroy TodoEtlStack

# Destroy monitoring stack
cdk destroy TodoMonitoringStack

# Clean up S3 buckets manually (if needed)
aws s3 rm s3://todo-bronze-YOUR-ACCOUNT-us-east-1 --recursive
aws s3 rm s3://todo-silver-YOUR-ACCOUNT-us-east-1 --recursive
aws s3 rm s3://todo-gold-YOUR-ACCOUNT-us-east-1 --recursive
```

## Support

For issues not covered in this runbook:
1. Check CloudWatch logs for detailed error messages
2. Verify CDK deployment completed successfully
3. Check AWS service status for regional outages
4. Review the ADRs in `docs/adrs/` for architectural context
5. Check ETL runbook in `docs/runbooks/ETL/ETL_RUNBOOK.md` for ETL-specific issues
