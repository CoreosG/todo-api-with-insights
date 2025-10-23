# Development Runbooks

This directory contains comprehensive runbooks for setting up, developing, and testing the Todo API with Insights system.

## Main Documentation

1. **[API Setup and Testing Guide](./API_SETUP_AND_TESTING.md)** - **START HERE** - Complete guide covering setup, testing, development, and deployment
2. **[API Layer Testing Runbook](./API_LAYER_TESTING.md)** - **API LAYER ONLY** - Focused guide for testing ApiStack and DataStack with curl/PowerShell commands

## Quick Start

### 1. Initial Setup
```bash
# Clone repository
git clone https://github.com/CoreosG/todo-api-with-insights
cd todo-api-with-insights

# Set up API environment
cd api
python -m venv venv-api
source venv-api/bin/activate  # On Windows: venv-api\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Local DynamoDB
```bash
# Start local DynamoDB for testing
docker run -d -p 8000:8000 amazon/dynamodb-local
```

### 3. Run Tests
```bash
# Unit tests (fast, mocked)
python -m pytest tests/unit/ -v

# API Gateway integration tests (mocked services)
python -m pytest tests/integration/test_api_gateway_integration.py -v

# Integration tests with real database
export USE_LOCAL_DYNAMODB=true
export DYNAMODB_ENDPOINT=http://localhost:8000
python -m pytest tests/integration/test_api_gateway_integration_with_db.py -v
```

### 4. Run API Locally
```bash
# Start the API server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Visit API documentation
open http://localhost:8000/docs
```

## Documentation Overview

### [API Setup and Testing Guide](./API_SETUP_AND_TESTING.md)
**Complete Development Guide**

This comprehensive guide covers:
- **System Architecture**: Complete overview of the serverless architecture
- **Development Setup**: Step-by-step environment configuration
- **Testing Strategies**: All testing approaches (unit, integration, API Gateway)
- **Local Development**: Running and testing the API locally
- **Deployment**: CDK infrastructure deployment and CI/CD
- **Troubleshooting**: Common issues and solutions
- **Production Considerations**: Security, performance, and monitoring

**Use this guide for**:
- Initial project setup and development
- Understanding the complete system architecture
- Learning all testing approaches and strategies
- Local development and debugging
- Deployment and production setup
- Troubleshooting any issues

## System Architecture

The Todo API follows a serverless-first architecture:

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

## Key Features

- **JWT Authentication**: Extracts user context from API Gateway JWT claims
- **User Auto-Creation**: Users are created automatically from JWT claims
- **Idempotency**: Prevents duplicate operations with Idempotency-Key headers
- **User Isolation**: All operations are automatically scoped to the authenticated user
- **Single Table Design**: Efficient DynamoDB schema with user-scoped partition keys

## Testing Approaches

### 1. Unit Tests (Fast, Mocked)
- **Purpose**: Test individual components in isolation
- **Backend**: Mocked DynamoDB (moto)
- **Speed**: Fast (< 1 second per test)
- **Command**: `python -m pytest tests/unit/ -v`

### 2. API Gateway Integration Tests (Mocked Services)
- **Purpose**: Test complete Lambda execution flow with API Gateway events
- **Backend**: Mocked services (no real database)
- **Speed**: Medium (1-2 seconds per test)
- **Command**: `python -m pytest tests/integration/test_api_gateway_integration.py -v`

### 3. Integration Tests with Real Database
- **Purpose**: Test complete system with real DynamoDB
- **Backend**: Local DynamoDB instance
- **Speed**: Slower (2-5 seconds per test)
- **Command**: `python -m pytest tests/integration/test_api_gateway_integration_with_db.py -v`

## Quick Commands

### Development
```bash
# Start API server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start local DynamoDB
docker run -d -p 8000:8000 amazon/dynamodb-local

# Check DynamoDB status
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

### Testing
```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests (mocked)
python -m pytest tests/integration/test_api_gateway_integration.py -v

# Integration tests (real DB)
export USE_LOCAL_DYNAMODB=true
export DYNAMODB_ENDPOINT=http://localhost:8000
python -m pytest tests/integration/test_api_gateway_integration_with_db.py -v

# All tests
python -m pytest tests/ -v --cov=src
```

### Code Quality
```bash
# Format code
black .

# Type checking
mypy .

# Linting
ruff check . --fix

# All quality checks
make lint-all
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Connection**: Check if DynamoDB is running
3. **Test Failures**: Run with verbose output for debugging
4. **Environment Variables**: Verify proper environment setup

### Debug Commands

```bash
# Run tests with debug output
python -m pytest tests/ -v -s --tb=long

# Run with interactive debugging
python -m pytest tests/ -v -s --pdb

# Check DynamoDB status
docker ps | grep dynamodb
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

## Quick Reference

### Development Commands
```bash
# Start local development server
make serve-local  # Sets all env vars and starts uvicorn

# Run all tests
python -m pytest tests/ -v --cov=src

# Run specific test categories
python -m pytest tests/unit/ -v                    # Fast unit tests
python -m pytest tests/integration/test_api_gateway_integration.py -v  # API Gateway tests
python -m pytest tests/integration/test_api_gateway_integration_with_db.py -v  # Real DB tests
```

### API Endpoints (when server is running)
- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`
- **Task Operations**: `http://localhost:8000/api/v1/tasks`

## Additional Resources

- [ADR Documentation](../adrs/) - Architecture decision records
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when server is running)
- [Test Reports](../API_GATEWAY_INTEGRATION_TESTING_REPORT.md) - Detailed test results
- [Infrastructure Setup](../infra/) - CDK infrastructure code

## Support

For issues and questions:
1. Check the troubleshooting section in the [API Setup and Testing Guide](./API_SETUP_AND_TESTING.md)
2. Review the test output for specific error messages
3. Check the API documentation for endpoint details
4. Review the ADR documentation for architectural decisions

