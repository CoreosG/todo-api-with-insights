# Testing Scripts

This directory contains automated testing scripts for the Todo API layer and ETL pipeline.

## Available Scripts

### Windows (PowerShell)
- `test-api.ps1` - Comprehensive API testing script for Windows PowerShell
- `test-etl.ps1` - ETL pipeline testing script that generates CDC events

### Unix/Linux/Mac (Bash)
- `test-api.sh` - Comprehensive API testing script for Bash (Linux/Mac/WSL)
- `test-etl.sh` - ETL pipeline testing script that generates CDC events

## Features

### API Testing Scripts (`test-api.*`)
Test the Todo API layer functionality:

1. **Health Check** - Tests public health endpoint without authentication
2. **User Management** - Creates and configures Cognito users
3. **Authentication** - Obtains IdToken for API access
4. **API Testing** - Tests user profile, task creation, and task retrieval
5. **Data Verification** - Validates data persistence in DynamoDB
6. **Cleanup** - Optional removal of test users

### ETL Testing Scripts (`test-etl.*`)
Test the ETL pipeline by generating CDC events:

1. **Multi-User Creation** - Creates multiple Cognito users for testing
2. **Mass Task Generation** - Creates many tasks per user to generate data
3. **Task Updates** - Updates tasks multiple times to create CDC events
4. **Data Verification** - Validates data generation in DynamoDB
5. **ETL Pipeline Triggering** - Generates events that should flow through Bronze → Silver → Gold layers
6. **Cleanup** - Optional removal of test users

## Configuration

Both scripts support multiple configuration methods (in order of precedence):

1. **Environment Variables** - Set directly in your shell
2. **Environment Files** - `.env` (bash) or `.env.txt` (both) in the scripts directory
3. **Defaults** - Built-in default values

### Required Variables

```bash
API_ENDPOINT=https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com
USER_POOL_ID=us-east-1_YOUR-USER-POOL-ID
CLIENT_ID=YOUR-CLIENT-ID
REGION=us-east-1
```

### Optional Variables

```bash
PASSWORD=TempPassword1!
AWS_PROFILE=your-profile-name
COGNITO_USERNAME=test-user-$(date +%Y%m%d%H%M%S)  # Auto-generated if not set
COGNITO_EMAIL=test.user.$(date +%Y%m%d%H%M%S)@example.com  # Auto-generated if not set
NON_INTERACTIVE=1  # Skip cleanup prompts

# ETL Testing specific variables
NUM_USERS=3  # Number of users to create for ETL testing
TASKS_PER_USER=5  # Number of tasks to create per user
UPDATES_PER_TASK=3  # Number of updates per task to generate CDC events
```

## Usage

### Windows (PowerShell)

```powershell
# Navigate to scripts directory
cd infra\scripts

# Option 1: Set environment variables
$Env:API_ENDPOINT = "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
$Env:USER_POOL_ID = "us-east-1_YOUR-USER-POOL-ID"
$Env:CLIENT_ID = "YOUR-CLIENT-ID"

# Option 2: Create .env.txt file with variables (see above)

# Run script
$Env:NON_INTERACTIVE = "1"  # Optional: skip cleanup prompts
.\test-api.ps1
```

### Linux/Mac (Bash)

```bash
# Navigate to scripts directory
cd infra/scripts

# Option 1: Set environment variables
export API_ENDPOINT="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
export USER_POOL_ID="us-east-1_YOUR-USER-POOL-ID"
export CLIENT_ID="YOUR-CLIENT-ID"

# Option 2: Create .env file with variables (see above)

# Make script executable (first time only)
chmod +x test-api.sh

# Run script
export NON_INTERACTIVE=1  # Optional: skip cleanup prompts
./test-api.sh
```

### ETL Testing Scripts

#### Windows (PowerShell)

```powershell
# Navigate to scripts directory
cd infra\scripts

# Option 1: Set environment variables
$Env:API_ENDPOINT = "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
$Env:USER_POOL_ID = "us-east-1_YOUR-USER-POOL-ID"
$Env:CLIENT_ID = "YOUR-CLIENT-ID"
$Env:NUM_USERS = "3"  # Optional: number of users to create
$Env:TASKS_PER_USER = "5"  # Optional: tasks per user
$Env:UPDATES_PER_TASK = "3"  # Optional: updates per task

# Option 2: Create .env.txt file with variables (see above)

# Run script
$Env:NON_INTERACTIVE = "1"  # Optional: skip cleanup prompts
.\test-etl.ps1
```

#### Linux/Mac (Bash)

```bash
# Navigate to scripts directory
cd infra/scripts

# Option 1: Set environment variables
export API_ENDPOINT="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com"
export USER_POOL_ID="us-east-1_YOUR-USER-POOL-ID"
export CLIENT_ID="YOUR-CLIENT-ID"
export NUM_USERS=3  # Optional: number of users to create
export TASKS_PER_USER=5  # Optional: tasks per user
export UPDATES_PER_TASK=3  # Optional: updates per task

# Option 2: Create .env file with variables (see above)

# Make script executable (first time only)
chmod +x test-etl.sh

# Run script
export NON_INTERACTIVE=1  # Optional: skip cleanup prompts
./test-etl.sh
```

## Prerequisites

### For Both Scripts
- AWS CLI installed and configured
- Appropriate AWS permissions (Cognito, API Gateway, Lambda, DynamoDB)
- Network access to AWS services

### For Bash Script (Linux/Mac)
- `jq` installed for JSON parsing:
  - Ubuntu/Debian: `sudo apt-get install jq`
  - macOS: `brew install jq`
  - CentOS/RHEL: `sudo yum install jq`

## Output

Both scripts provide colored output indicating:

- ✅ **Success** - Green text for successful operations
- ⚠️ **Warning** - Yellow text for informational messages
- ❌ **Error** - Red text for failures

### Sample Output
```
[*] Starting API Layer Testing...
API Endpoint: https://abc123.execute-api.us-east-1.amazonaws.com
User Pool ID: us-east-1_EXAMPLE
Client ID: example_client_id
Using test user: api-test-20231022123456789 (api.test.20231022123456789@example.com)

[STEP 1] Testing Health Endpoint...
[SUCCESS] Health Check Successful!
Status: ok
Version: 0.1.0
Environment: development

[STEP 2] Creating Cognito User...
Creating user: api-test-20231022123456789 (api.test.20231022123456789@example.com)
[SUCCESS] Cognito User Ready Successfully!

[... additional steps ...]

[COMPLETE] API Layer Testing Complete!

=== SUMMARY ===
[OK] Health endpoint working
[OK] Cognito user created and authenticated
[OK] API authentication working
[OK] User profile retrieval working
[OK] Task creation working
[OK] Task retrieval working
[OK] Data persisted in DynamoDB

API Documentation: https://abc123.execute-api.us-east-1.amazonaws.com/docs
API Endpoint: https://abc123.execute-api.us-east-1.amazonaws.com
```

### ETL Testing Sample Output
```
[*] Starting ETL Testing...
API Endpoint: https://abc123.execute-api.us-east-1.amazonaws.com
User Pool ID: us-east-1_EXAMPLE
Client ID: example_client_id
Users to create: 3
Tasks per user: 5
Updates per task: 3

[STEP 1] Creating Users and Obtaining Tokens...
Creating user 1/3...
Setting up user: etl-user-1-20231022123456 (etl.user1.20231022123456000@example.com)
  Token obtained successfully
  User 1 ready with token
...

[STEP 2] Creating and Updating Tasks for ETL Data Generation...
Processing user 1 (etl-user-1-20231022123456)...
  Creating task 1/5...
    Created task: 12345678-1234-1234-1234-123456789abc
    Task 12345678-1234-1234-1234-123456789abc updated (1/3)
    Task 12345678-1234-1234-1234-123456789abc updated (2/3)
    Task 12345678-1234-1234-1234-123456789abc updated (3/3)
...

[STEP 3] Verifying Data Generation in DynamoDB...
[SUCCESS] DynamoDB Query Successful!
Current table statistics:
  Total items in table: 87
  User records: 3
  Task records: 15
  Idempotency records: 69

[COMPLETE] ETL Testing Complete!

=== ETL TEST SUMMARY ===
Users created: 3
Tasks created: 15
Task updates performed: 45
Expected CDC events generated: 63

This should trigger the ETL pipeline:
  - Bronze layer: CDC events from DynamoDB streams
  - Silver layer: Transformed user/task data
  - Gold layer: Analytics and business metrics

Check CloudWatch logs and S3 buckets for ETL processing results.
```

## Troubleshooting

### Common Issues

1. **"jq: command not found"** (Bash script only)
   - Install jq as described in prerequisites

2. **"Unable to locate credentials"**
   - Configure AWS CLI: `aws configure`
   - Or set AWS_PROFILE environment variable

3. **"User already exists"**
   - This is normal - script handles existing users
   - Or use a different username in configuration

4. **"Access Denied" errors**
   - Verify AWS credentials and permissions
   - Check if you're in the correct AWS account/region

5. **"Connection refused" or "timeout"**
   - Verify API_ENDPOINT is correct
   - Check if the API Gateway is deployed and accessible

### Getting Help

1. Check AWS CloudWatch logs for the Lambda function
2. Verify CDK deployment completed successfully
3. Review the detailed runbooks in `docs/runbooks/`

## Files

- `test-api.ps1` - Windows PowerShell API testing script
- `test-api.sh` - Unix/Linux/Mac bash API testing script
- `test-etl.ps1` - Windows PowerShell ETL testing script
- `test-etl.sh` - Unix/Linux/Mac bash ETL testing script
- `README.md` - This documentation file
- `.env.example` - Example environment file (create your own `.env` or `.env.txt`)
