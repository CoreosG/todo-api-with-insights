# API Setup and Testing Guide

This comprehensive guide covers the complete setup, testing, and development workflow for the Todo API with Insights system.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Development Environment Setup](#development-environment-setup)
3. [API Implementation Overview](#api-implementation-overview)
4. [Testing Strategies](#testing-strategies)
5. [Running Tests](#running-tests)
6. [Local Development](#local-development)
7. [Troubleshooting](#troubleshooting)

## System Architecture

The Todo API follows a serverless-first architecture with the following components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│  AWS Lambda     │───▶│    DynamoDB     │
│   (Cognito)     │    │  (FastAPI)      │    │  (Single Table) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │   DynamoDB      │
         │                       │              │   Streams       │
         │                       │              └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │   S3 (Bronze)   │
         │                       │              │   (Raw Data)    │
         │                       │              └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │   Glue (Silver) │
         │                       │              │   (Transform)   │
         │                       │              └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │   Athena       │
         │                       │              │   (Gold/Analytics)│
         │                       │              └─────────────────┘
```

### Key Components

- **API Gateway**: HTTP API v2.0 with Cognito JWT authorizer
- **Lambda**: FastAPI application with Mangum adapter
- **DynamoDB**: Single-table design with user-scoped partition keys
- **ETL Pipeline**: Real-time CDC with Lambda, S3, Glue, and Athena
- **Monitoring**: CloudWatch dashboards and alarms

## Development Environment Setup

### Prerequisites

- **Python 3.11+** (recommended: 3.13)
- **Node.js 18+** (for CDK deployment)
- **AWS CLI** (configured with appropriate credentials)
- **Docker** (for local DynamoDB testing)
- **Git**

### 1. Clone and Setup

```bash
git clone <repository-url>
cd todo-api-with-insights
```

### 2. API Virtual Environment

```bash
cd api
python -m venv venv-api

# Windows
venv-api\Scripts\activate

# Linux/Mac
source venv-api/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

Set environment variables using command line (no `.env` file needed):

```bash
# API Configuration
export DEBUG=true
export LOG_LEVEL=INFO

# Database Configuration (for local development)
export USE_LOCAL_DYNAMODB=true
export DYNAMODB_ENDPOINT=http://localhost:8000

# local user for testing with uvicorn
export LOCAL_USER=true

# AWS Configuration (for local development)
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export AWS_DEFAULT_REGION=us-east-1


```

**Note:** Environment variables are set per terminal session. Use `export` (Linux/Mac) or `$env:` (PowerShell) as needed for your workflow.

### 4. Local DynamoDB Setup

```bash
# Start local DynamoDB
docker run -d -p 8000:8000 amazon/dynamodb-local

# Verify it's running
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

## API Implementation Overview

### Architecture Layers

The API follows a 5-layer architecture as defined in ADR-004:

```
┌─────────────────────────────────────────────────────────────┐
│                    Entrypoint Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │   API Gateway   │  │   Lambda        │  │   Mangum     │  │
│  │   (Cognito)     │  │   (FastAPI)     │  │   Adapter    │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Controller Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │  TaskController │  │  UserController │  │  Auth        │  │
│  │  (CRUD)         │  │  (Auto-create)  │  │  (JWT)       │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │  TaskService    │  │  UserService    │  │  Idempotency  │  │
│  │  (Business)     │  │  (Auto-create)  │  │  Service     │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Repository Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │  TaskRepository│  │  UserRepository │  │  Idempotency │  │
│  │  (DynamoDB)     │  │  (DynamoDB)     │  │  Repository │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │  DynamoDB       │  │  Single Table   │  │  GSI Indexes │  │
│  │  (On-Demand)    │  │  (User-scoped)  │  │  (Queries)   │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

1. **JWT Authentication**: Extracts user context from API Gateway JWT claims
2. **User Auto-Creation**: Users are created automatically from JWT claims
3. **Idempotency**: Prevents duplicate operations with Idempotency-Key headers
4. **User Isolation**: All operations are automatically scoped to the authenticated user
5. **Single Table Design**: Efficient DynamoDB schema with user-scoped partition keys

### API Endpoints

#### Tasks
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/tasks` - List user's tasks
- `GET /api/v1/tasks/{task_id}` - Get specific task
- `PUT /api/v1/tasks/{task_id}` - Update task
- `DELETE /api/v1/tasks/{task_id}` - Delete task

#### Users
- `GET /api/v1/users/` - Get user profile
- `PUT /api/v1/users/` - Update user profile
- `DELETE /api/v1/users/` - Delete user

#### Health
- `GET /health` - Health check endpoint

## Testing Strategies

The API implements a comprehensive testing strategy with multiple approaches:

### 1. Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation
**Backend**: Mocked DynamoDB (moto)
**Speed**: Fast (< 1 second per test)

```bash
# Run unit tests
python -m pytest tests/unit/ -v
```

**Test Files**:
- `test_task_models.py` - Pydantic model validation
- `test_task_repository.py` - Database operations (mocked)
- `test_task_service.py` - Business logic
- `test_task_controller.py` - API endpoints
- `test_dependencies.py` - Authentication and utilities

### 2. Integration Tests with Mocked Services (`tests/integration/test_api_gateway_integration.py`)

**Purpose**: Test complete Lambda execution flow with API Gateway events
**Backend**: Mocked services (no real database)
**Speed**: Medium (1-2 seconds per test)

```bash
# You can run scripts available on api/tests/scripts
Run api/tests/scripts/test_api_gateway_integration.bat (ps1,sh)
# Alternatively you can run API Gateway integration tests with
python -m pytest tests/integration/test_api_gateway_integration.py -v
# But you need to set some environment variables
```

**Key Features**:
- Tests Mangum handler with real API Gateway events
- Simulates JWT authentication flow
- Tests complete request/response cycle
- Validates user context extraction
- Tests idempotency handling

### 3. Integration Tests with Real Database (`tests/integration/test_api_gateway_integration_with_db.py`)

**Purpose**: Test complete system with real DynamoDB
**Backend**: Local DynamoDB instance
**Speed**: Slower (2-5 seconds per test)

```bash
# Start local DynamoDB
docker run -d -p 8000:8000 amazon/dynamodb-local

# Run tests using python script available, it sets environment variables.
python api/tests/scripts/run_db_integration_tests.py
# Alternatively tou can run tests directly (no environment variables set)
python -m pytest tests/integration/test_api_gateway_integration_with_db.py -v
```

**Key Features**:
- Tests with real DynamoDB operations
- Validates data persistence
- Tests table creation and schema
- Validates user isolation
- Tests error handling with real database

### 4. Test Helpers

**API Gateway Events** (`tests/helpers/api_gateway_events.py`):
- `create_authenticated_api_gateway_event()` - Creates realistic API Gateway events
- `create_task_create_event()` - Task creation events
- `create_task_get_event()` - Task retrieval events
- `create_health_check_event()` - Health check events

## Running Tests

### Quick Start Scripts

#### Windows PowerShell
```powershell
# From api directory
powershell -ExecutionPolicy Bypass -File "tests/scripts/test_api_gateway_integration.ps1"
```

#### Windows Command Prompt
```cmd
# From api directory
tests\scripts\test_api_gateway_integration.bat
```

#### Linux/Mac Bash
```bash
# From api directory
./tests/scripts/test_api_gateway_integration.sh
```

### Manual Test Execution

#### 1. Unit Tests (Fast, Mocked)
```bash
cd api
python -m pytest tests/unit/ -v
```

#### 2. API Gateway Integration Tests (Mocked Services)
```bash
cd api
python -m pytest tests/integration/test_api_gateway_integration.py -v
```

#### 3. Integration Tests with Real Database
```bash
# Start local DynamoDB
docker run -d -p 8000:8000 amazon/dynamodb-local

# Set environment variables
export USE_LOCAL_DYNAMODB=true
export DYNAMODB_ENDPOINT=http://localhost:8000

# Run tests
cd api
python -m pytest tests/integration/test_api_gateway_integration_with_db.py -v
```

#### 4. All Tests
```bash
cd api
python -m pytest tests/ -v --cov=src
```

### Test Scripts

#### Database Integration Test Runner
```bash
# Run the comprehensive database integration test script
python tests/scripts/run_db_integration_tests.py
```

This script:
- Sets up environment variables
- Checks DynamoDB connectivity
- Runs comprehensive integration tests
- Provides troubleshooting tips

## Local Development

### Running the API Locally

```bash
cd api
pip install -r ./requirements.txt
make serve-local
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json


### Code Quality

#### Linting and Formatting
```bash
cd api
make lint-all  # Runs black, mypy, and ruff
```

#### Manual Checks
```bash
# Format code
black .

# Type checking
mypy .

# Linting
ruff check . --fix
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

#### 2. Database Connection Issues
```bash
# Check if DynamoDB is running
docker ps | grep dynamodb

# Test connection
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

#### 3. Test Failures
```bash
# Run with verbose output
python -m pytest tests/ -v -s

# Run specific test
python -m pytest tests/integration/test_api_gateway_integration.py::TestAPIGatewayAuthentication::test_user_context_extraction_from_jwt -v
```

#### 4. Environment Variables
```bash
# Check environment variables
echo $USE_LOCAL_DYNAMODB
echo $DYNAMODB_ENDPOINT

# Set for current session
export USE_LOCAL_DYNAMODB=true
export DYNAMODB_ENDPOINT=http://localhost:8000
```

### Debug Mode

```bash
# Run tests with debug output
python -m pytest tests/ -v -s --tb=long

# Run with pdb for interactive debugging
python -m pytest tests/ -v -s --pdb
```

### DynamoDB Local Issues

#### Check if DynamoDB is running
```bash
# Check container status
docker ps | grep dynamodb

# Check logs
docker logs <container_id>
```

#### Reset DynamoDB
```bash
# Stop and remove container
docker stop <container_id>
docker rm <container_id>

# Start fresh
docker run -d -p 8000:8000 amazon/dynamodb-local
```

#### Check table creation
```bash
# List tables
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Describe table
aws dynamodb describe-table --table-name todo-app-data --endpoint-url http://localhost:8000
```

## Production Considerations

### Security
- JWT tokens are validated by API Gateway
- User context is extracted from JWT claims
- All operations are user-scoped
- Idempotency prevents duplicate operations

### Performance
- Single-table DynamoDB design for efficiency
- On-demand capacity mode for serverless scaling
- Async/await patterns for concurrent operations
- Connection pooling for database operations

### Monitoring
- Structured JSON logging with request IDs
- CloudWatch integration for metrics and alarms
- Error tracking and alerting
- Performance monitoring

### Cost Optimization
- Serverless architecture (pay-per-use)
- DynamoDB on-demand billing
- Lambda cold start optimization
- Efficient data storage patterns

## Deployment

### Infrastructure Deployment with CDK

#### Prerequisites for CDK
- **Node.js 18+** (for CDK deployment)
- **AWS CDK CLI**: `npm install -g aws-cdk`
- **CDK Bootstrap** (run once per AWS account/region)

#### Deploy All Stacks
```bash
cd infra
cdk deploy --all
```

#### Deploy Specific Stacks
```bash
cd infra
cdk deploy TodoApiStack     # API Gateway, Lambda, Cognito
cdk deploy TodoDataStack     # DynamoDB, Lambda CDC, S3, Firehose (buffer)
cdk deploy TodoEtlStack      # Glue jobs, Athena
cdk deploy TodoMonitoringStack  # CloudWatch, Alarms
```

#### Environment-Specific Deployments
```bash
# Development
export CDK_DEPLOY_ENV=dev
cdk deploy --all --context environment=dev

# Production
export CDK_DEPLOY_ENV=prod
cdk deploy --all --context environment=prod
```

### Future Enhancements

#### Potential CI/CD Setup
This project is designed to work well with CI/CD pipelines. Future enhancements could include:

- **GitHub Actions** for automated testing on pull requests
- **Pre-commit hooks** for code quality checks before commits
- **Automated deployment** pipelines for staging and production environments

The testing infrastructure is already compatible with these tools - the environment variables and test commands are designed to work in CI/CD environments.

## Next Steps

1. **Deploy to AWS**: Use CDK to deploy the complete infrastructure
2. **Set up CI/CD**: Configure automated testing and deployment
3. **Monitor Production**: Set up CloudWatch dashboards and alarms
4. **Scale Testing**: Test with higher loads and concurrent users
5. **Security Review**: Conduct security audit and penetration testing

## Additional Resources

- [ADR Documentation](../adrs/) - Architecture decision records
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Test Reports](../API_GATEWAY_INTEGRATION_TESTING_REPORT.md) - Detailed test results
- [Development Runbooks](../README.md) - Complete development documentation
