# API Layer Testing Runbook

## Overview

This runbook provides a focused guide for setting up and testing the Todo API layer (ApiStack and DataStack only). It includes step-by-step commands using both curl and PowerShell Invoke-WebRequest (Windows) or bash scripts (Linux/Mac) to test the API endpoints, Cognito authentication, and user management.

Important: This API uses a Cognito User Pool authorizer. Use the IdToken (not the AccessToken) in the Authorization Bearer header for API calls.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Deployment](#infrastructure-deployment)
3. [Testing Health Endpoint](#testing-health-endpoint)
4. [Cognito User Management](#cognito-user-management)
5. [Authentication and Token Retrieval](#authentication-and-token-retrieval)
6. [API Testing with Authentication](#api-testing-with-authentication)
7. [Troubleshooting](#troubleshooting)
8. [Cleanup](#cleanup)

## Prerequisites

### 1. AWS Setup

- **AWS CLI** installed and configured with appropriate credentials
- **AWS Account** with necessary permissions (CDK deployment, Cognito, Lambda, API Gateway, DynamoDB)
- **CDK CLI** installed: `npm install -g aws-cdk`

### 2. Environment Setup

```bash
# Navigate to project root
cd todo-api-with-insights

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

### Step 2: Deploy Data Stack (DynamoDB)

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

### Step 3: Deploy API Stack (API Gateway, Lambda, Cognito)

```bash
# Deploy API stack (includes Cognito, API Gateway, Lambda)
cdk deploy TodoApiStack --require-approval never
```

**Expected Output:**
```
✅ TodoApiStack

Outputs:
TodoApiStack.ApiEndpoint = https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/
TodoApiStack.UserPoolId = us-east-1_YOUR-USER-POOL-ID
TodoApiStack.UserPoolClientId = YOUR-CLIENT-ID
TodoApiStack.LambdaFunctionName = todo-api-function
```

**Verification:**
- **API Gateway**: Check AWS Console → API Gateway → APIs → `todo-api`
- **Cognito**: Check AWS Console → Cognito → User pools → `todo-api-user-pool`
- **Lambda**: Check AWS Console → Lambda → Functions → `todo-api-function`

## Testing Health Endpoint

### Step 4: Test Public Health Endpoint

The `/health` endpoint should be publicly accessible without authentication.

#### Using curl (Linux/Mac/Bash):

```bash
# Test health endpoint (no authentication required)
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health

# Pretty print JSON response
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health | jq .
```

#### Using PowerShell (Windows):

```powershell
# Test health endpoint (no authentication required)
Invoke-WebRequest -Uri https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health -Method GET

# Pretty print JSON response
(Invoke-WebRequest -Uri https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health -Method GET).Content | ConvertFrom-Json
```

#### Using Bash (Linux/Mac):

```bash
# Test health endpoint (no authentication required)
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health

# Pretty print JSON response
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/health | jq .
```

**Expected Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development"
}
```

**Troubleshooting:**
- If you get `{"message":"Not Found"}`, check API Gateway routes in AWS Console
- Verify Lambda function logs in CloudWatch

## Cognito User Management

### Step 5: Create a Cognito User

Create a test user in the Cognito User Pool using AWS CLI:

#### Set Variables (Bash)

```bash
# Set variables from CDK output (replace with your actual values)
API_ENDPOINT="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
USER_POOL_ID="us-east-1_YOUR-USER-POOL-ID"
CLIENT_ID="YOUR-CLIENT-ID"
REGION="us-east-1"
```

#### Set Variables (Bash)

```bash
# Set variables from CDK output (replace with your actual values)
export API_ENDPOINT="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
export USER_POOL_ID="us-east-1_YOUR-USER-POOL-ID"
export CLIENT_ID="YOUR-CLIENT-ID"
export REGION="us-east-1"
```

#### Set Variables (PowerShell)

```powershell
# Set variables from CDK output (replace with your actual values)
$Env:API_ENDPOINT = "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
$Env:USER_POOL_ID = "us-east-1_YOUR-USER-POOL-ID"
$Env:CLIENT_ID = "YOUR-CLIENT-ID"
$Env:REGION = "us-east-1"
```

#### Create User (Bash/Linux/Mac):

```bash
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

#### Create User (Bash/Linux/Mac):

```bash
# Create user in Cognito
aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "test-user-001" \
  --user-attributes Name=email,Value="test.user@example.com" Name=given_name,Value="Test" Name=family_name,Value="User" \
  --message-action SUPPRESS \
  --region us-east-1

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "test-user-001" \
  --password "TempPassword1!" \
  --permanent \
  --region us-east-1
```

#### Create User (PowerShell/Windows):

```powershell
# Create user in Cognito
aws cognito-idp admin-create-user --user-pool-id $Env:USER_POOL_ID --username "test-user-001" --user-attributes Name=email,Value="test.user@example.com" Name=given_name,Value="Test" Name=family_name,Value="User" --message-action SUPPRESS --region us-east-1

# Set permanent password
aws cognito-idp admin-set-user-password --user-pool-id $Env:USER_POOL_ID --username "test-user-001" --password "TempPassword1!" --permanent
```

#### Verify User Creation:

```bash
# List users to verify creation (Bash)
aws cognito-idp list-users --user-pool-id "$USER_POOL_ID" --region us-east-1

# List users to verify creation (PowerShell)
aws cognito-idp list-users --user-pool-id $Env:USER_POOL_ID --region us-east-1
```

## Authentication and Token Retrieval

### Step 6: Authenticate and Get Token

Get an IdToken for API calls (required by the API Gateway Cognito authorizer):

#### Using curl and jq (Linux/Mac/Bash):

```bash
# Authenticate user and get tokens (outputs JSON)
AUTH_RESPONSE=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id "$USER_POOL_ID" \
  --client-id "$CLIENT_ID" \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME="test-user-001",PASSWORD="TempPassword1!" \
  --region us-east-1)

# Extract Id token
ID_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.IdToken')
echo "IdToken length: ${#ID_TOKEN}"

# Optional: export for reuse in this shell
export ID_TOKEN

# Optionally get RefreshToken
REFRESH_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.RefreshToken // empty')
```

#### Using Bash (Linux/Mac):

```bash
# Authenticate user and get tokens (outputs JSON)
AUTH_RESPONSE=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id "$USER_POOL_ID" \
  --client-id "$CLIENT_ID" \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME="test-user-001",PASSWORD="TempPassword1!" \
  --region us-east-1)

# Extract Id token
ID_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.IdToken')
echo "IdToken length: ${#ID_TOKEN}"

# Optional: export for reuse in this shell
export ID_TOKEN

# Optionally get RefreshToken
REFRESH_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.RefreshToken // empty')
```

#### Using PowerShell (Windows):

```powershell
# Authenticate user and get tokens (string JSON)
$Env:AUTH_RESPONSE = $(aws cognito-idp admin-initiate-auth `
  --user-pool-id $Env:USER_POOL_ID `
  --client-id $Env:CLIENT_ID `
  --auth-flow ADMIN_NO_SRP_AUTH `
  --auth-parameters USERNAME="test-user-001",PASSWORD="TempPassword1!" `
  --region us-east-1)

# Parse and extract IdToken
$authObj = $Env:AUTH_RESPONSE | ConvertFrom-Json
$Env:ID_TOKEN = $authObj.AuthenticationResult.IdToken
Write-Host "IdToken length: $($Env:ID_TOKEN.Length)"

# Optional: refresh token
$Env:REFRESH_TOKEN = $authObj.AuthenticationResult.RefreshToken
```

## API Testing with Authentication

### Step 7: Test API Endpoints with Authentication

#### Get User Profile

Test the user endpoint to verify authentication and user auto-creation:

**Using curl (Linux/Mac/Bash):**

```bash
# Get user profile (this will auto-create user if not exists)
curl -X GET \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/users \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json"

# Pretty print response
curl -X GET \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/users \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" | jq .
```

**Using Bash (Linux/Mac):**

```bash
# Get user profile (this will auto-create user if not exists)
curl -X GET \
  "$API_ENDPOINT/api/v1/users" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json"

# Pretty print response
curl -X GET \
  "$API_ENDPOINT/api/v1/users" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" | jq .
```

**Using PowerShell (Windows):**

```powershell
# Get user profile (this will auto-create user if not exists)
Invoke-WebRequest -Uri "$Env:API_ENDPOINT/api/v1/users" -Method GET -Headers @{"Authorization"="Bearer $Env:ID_TOKEN";"Content-Type"="application/json"}

# Pretty print response
(Invoke-WebRequest -Uri "$Env:API_ENDPOINT/api/v1/users" `
  -Method GET `
  -Headers @{
    "Authorization" = "Bearer $ID_TOKEN"
    "Content-Type" = "application/json"
  }).Content | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "email": "testuser@example.com",
  "name": "Test User",
  "id": "COGNITO-USER-ID",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

#### Create a Task

Test task creation with idempotency:

**Using curl:**

```bash
# Create a task
curl -X POST \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: task-creation-123" \
  -d '{
    "title": "Test Task from Runbook",
    "description": "This is a test task created via the API testing runbook",
    "priority": "medium",
    "category": "testing",
    "status": "pending"
  }' | jq .
```

**Using Bash:**

```bash
# Create a task
curl -X POST \
  "$API_ENDPOINT/api/v1/tasks" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: task-creation-123" \
  -d '{
    "title": "Test Task from Runbook",
    "description": "This is a test task created via the API testing runbook",
    "priority": "medium",
    "category": "testing",
    "status": "pending"
  }' | jq .
```

**Using PowerShell:**

```powershell
# Create a task
$taskData = @{
    title = "Test Task from Runbook"
    description = "This is a test task created via the API testing runbook"
    priority = "medium"
    category = "testing"
    status = "pending"
} | ConvertTo-Json

Invoke-WebRequest -Uri "$Env:API_ENDPOINT/api/v1/tasks" `
  -Method POST `
  -Headers @{
    "Authorization" = "Bearer $ID_TOKEN"
    "Content-Type" = "application/json"
    "Idempotency-Key" = "task-creation-123"
  } `
  -Body $taskData `
  -ContentType "application/json" | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "id": "task-uuid",
  "title": "Test Task from Runbook",
  "description": "This is a test task created via the API testing runbook",
  "status": "pending",
  "priority": "medium",
  "category": "testing",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

#### Get User's Tasks

**Using curl:**

```bash
# Get all tasks for the user
curl -X GET \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer $ID_TOKEN" | jq .

# Get tasks by status
curl -X GET \
  "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks?status=pending" \
  -H "Authorization: Bearer $ID_TOKEN" | jq .
```

**Using Bash:**

```bash
# Get all tasks for the user
curl -X GET \
  "$API_ENDPOINT/api/v1/tasks" \
  -H "Authorization: Bearer $ID_TOKEN" | jq .

# Get tasks by status
curl -X GET \
  "$API_ENDPOINT/api/v1/tasks?status=pending" \
  -H "Authorization: Bearer $ID_TOKEN" | jq .
```

**Using PowerShell:**

```powershell
# Get all tasks for the user
Invoke-WebRequest -Uri "$Env:API_ENDPOINT/api/v1/tasks" `
  -Method GET `
  -Headers @{ "Authorization" = "Bearer $ID_TOKEN" } | ConvertFrom-Json

# Get tasks by status
Invoke-WebRequest -Uri "$Env:API_ENDPOINT/api/v1/tasks?status=pending" `
  -Method GET `
  -Headers @{ "Authorization" = "Bearer $ID_TOKEN" } | ConvertFrom-Json
```

#### Test Idempotency

Test the idempotency feature by making the same request twice:

**Using Bash:**

```bash
# First request
curl -X POST \
  "$API_ENDPOINT/api/v1/tasks" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idempotency-test-456" \
  -d '{
    "title": "Idempotency Test Task",
    "description": "This task tests idempotency",
    "priority": "high"
  }' | jq .

# Second request with same Idempotency-Key (should return same response)
curl -X POST \
  "$API_ENDPOINT/api/v1/tasks" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idempotency-test-456" \
  -d '{
    "title": "Idempotency Test Task",
    "description": "This task tests idempotency",
    "priority": "high"
  }' | jq .
```

**Using PowerShell:**

```powershell
# First request
curl -X POST \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idempotency-test-456" \
  -d '{
    "title": "Idempotency Test Task",
    "description": "This task tests idempotency",
    "priority": "high"
  }' | jq .

# Second request with same Idempotency-Key (should return same response)
curl -X POST \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idempotency-test-456" \
  -d '{
    "title": "Idempotency Test Task",
    "description": "This task tests idempotency",
    "priority": "high"
  }' | jq .
```

#### Test Authentication Failure

**Using curl:**

```bash
# Try to access API without token (should fail)
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks

# Try with invalid token (should fail)
curl -X GET \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer invalid-token"
```

**Using Bash:**

```bash
# Try to access API without token (should fail)
curl -X GET https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks

# Try with invalid token (should fail)
curl -X GET \
  https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks \
  -H "Authorization: Bearer invalid-token"
```

**Using PowerShell:**

```powershell
# Try to access API without token (should fail)
try {
    Invoke-WebRequest -Uri https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks -Method GET
} catch {
    Write-Host "Expected error: $($_.Exception.Message)"
}

# Try with invalid token (should fail)
try {
    Invoke-WebRequest -Uri https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/api/v1/tasks `
      -Method GET `
      -Headers @{ "Authorization" = "Bearer invalid-token" }
} catch {
    Write-Host "Expected error: $($_.Exception.Message)"
}
```

**Expected Response:** `401 Unauthorized`

### Scripted Testing

You can automate end-to-end API layer testing using the provided scripts for both Windows and Unix/Linux/Mac systems.

#### Windows (PowerShell)

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

# Option 2: Use a .env.txt file in this folder (OS env takes precedence)
# Create a file named ".env.txt" with lines like:
# API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
# REGION=us-east-1
# USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
# CLIENT_ID=YOUR-CLIENT-ID
# PASSWORD=TempPassword1!
# COGNITO_USERNAME=   # optional; if blank, script will auto-generate
# COGNITO_EMAIL=      # optional; if blank, script will auto-generate

# Run non-interactively
$Env:NON_INTERACTIVE = "1"
./test-api.ps1
```

#### Linux/Mac (Bash)

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

# Option 2: Use a .env or .env.txt file in this folder (OS env takes precedence)
# Create a file named ".env" or ".env.txt" with lines like:
# API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
# REGION=us-east-1
# USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
# CLIENT_ID=YOUR-CLIENT-ID
# PASSWORD=TempPassword1!
# COGNITO_USERNAME=   # optional; if blank, script will auto-generate
# COGNITO_EMAIL=      # optional; if blank, script will auto-generate

# Make script executable (first time only)
chmod +x test-api.sh

# Run non-interactively
export NON_INTERACTIVE=1
./test-api.sh
```

**Notes for Both Scripts:**
- OS environment variables take precedence over .env/.env.txt values.
- The scripts auto-generate a unique username/email each run unless set explicitly.
- Ensure your AWS CLI is authenticated and pointed to the correct region/account.
- **✅ Scripts Status: FULLY WORKING** - Both scripts successfully test all API endpoints with proper IdToken authentication.
- Requires `jq` for JSON parsing on Unix systems (install with: `apt-get install jq` on Ubuntu/Debian, `brew install jq` on Mac)

## Verification Steps

### Step 8: Verify Data Persistence

#### Check DynamoDB Data

```bash
# Query DynamoDB table to see created data
aws dynamodb scan --table-name todo-app-data --region us-east-1 | jq '.Items'

# PowerShell version
aws dynamodb scan --table-name todo-app-data --region us-east-1 | ConvertFrom-Json | Select-Object -ExpandProperty Items
```

**Expected Data:**
- `USER#COGNITO-USER-ID` entries for user data
- `TASK#COGNITO-USER-ID` entries for task data
- `IDEMPOTENCY#REQUEST-ID` entries for idempotency records

#### Check CloudWatch Logs

```bash
# View Lambda function logs
aws logs tail /aws/lambda/todo-api-function --region us-east-1 --follow

# PowerShell version
aws logs tail /aws/lambda/todo-api-function --region us-east-1 --follow
```

#### Check API Gateway Metrics

- AWS Console → API Gateway → APIs → `todo-api` → Monitor

## Troubleshooting

### Common Issues

#### 1. "Not Found" Error on Health Endpoint
**Symptoms:** `/health` returns `{"message":"Not Found"}`

**Solutions:**
```bash
# Check API Gateway routes
aws apigatewayv2 get-routes --api-id YOUR-API-ID --region us-east-1

# Check Lambda function logs
aws logs tail /aws/lambda/todo-api-function --region us-east-1

# Redeploy API stack
cd infra
cdk deploy TodoApiStack --require-approval never
```

#### 2. Authentication Failures
**Symptoms:** `401 Unauthorized` or token-related errors

**Solutions:**
```bash
# Verify Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --region us-east-1

# Check user exists
aws cognito-idp list-users --user-pool-id $USER_POOL_ID --region us-east-1

# Regenerate token (repeat Step 6)
```

#### 3. Lambda Function Errors
**Symptoms:** `500 Internal Server Error`

**Solutions:**
```bash
# Check Lambda function logs for detailed error messages
aws logs tail /aws/lambda/todo-api-function --region us-east-1

# Verify function configuration
aws lambda get-function --function-name todo-api-function --region us-east-1 | jq '.Configuration'
```

#### 4. DynamoDB Access Issues
**Symptoms:** Database operation failures

**Solutions:**
```bash
# Check table exists
aws dynamodb describe-table --table-name todo-app-data --region us-east-1

# Check IAM role permissions
aws iam get-role --role-name TodoApiStack-LambdaExecutionRole --region us-east-1 | jq '.Role.AssumeRolePolicyDocument'
```

### Debug Commands

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
cd infra
cdk destroy TodoApiStack

# Destroy data stack
cdk destroy TodoDataStack
```

### Clean Up Cognito Users

```bash
# Delete test users
aws cognito-idp admin-delete-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --region us-east-1

# PowerShell version
aws cognito-idp admin-delete-user `
  --user-pool-id $USER_POOL_ID `
  --username $USERNAME `
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

## Support

For issues not covered in this runbook:

1. Check CloudWatch logs for detailed error messages
2. Verify CDK deployment completed successfully
3. Check AWS service status for regional outages
4. Review the ADRs in `docs/adrs/` for architectural context

## Next Steps

After successfully testing the API layer:

1. **Deploy ETL Stack**: Add the ETL pipeline (S3, Glue, Athena) for data analytics
2. **Set up Monitoring**: Deploy CloudWatch dashboards and alarms
3. **Performance Testing**: Test with higher loads and concurrent users
4. **Security Review**: Conduct security audit and penetration testing

## Variable Reference

Replace these placeholders with your actual values:

- `YOUR-API-ID` - From `TodoApiStack.ApiEndpoint` output
- `YOUR-USER-POOL-ID` - From `TodoApiStack.UserPoolId` output
- `YOUR-CLIENT-ID` - From `TodoApiStack.UserPoolClientId` output
- `COGNITO-USER-ID` - The sub claim from your JWT token
- `ID_TOKEN` - JWT Id token from authentication step (use for Authorization header)
