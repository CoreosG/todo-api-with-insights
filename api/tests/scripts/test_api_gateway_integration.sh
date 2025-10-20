#!/bin/bash

# Script to run comprehensive API Gateway integration tests
# Tests the Todo API with realistic API Gateway authentication simulation

echo "🚀 Running API Gateway Integration Tests"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Please run this script from the api directory"
    exit 1
fi

# Set environment variables for testing
export USE_LOCAL_DYNAMODB=true
export DYNAMODB_ENDPOINT=http://localhost:8000

echo "📋 Test Configuration:"
echo "  - USE_LOCAL_DYNAMODB: $USE_LOCAL_DYNAMODB"
echo "  - DYNAMODB_ENDPOINT: $DYNAMODB_ENDPOINT"
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "❌ Error: pytest is not installed. Please install it first:"
    echo "   pip install pytest pytest-asyncio"
    exit 1
fi

# Run the comprehensive API Gateway integration tests
echo "🧪 Running comprehensive API Gateway integration tests..."
pytest tests/integration/test_api_gateway_integration.py -v --tb=short

# Check the exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All API Gateway integration tests passed!"
    echo ""
    echo "📊 Test Summary:"
    echo "  ✅ API Gateway payload extraction works correctly"
    echo "  ✅ User auto-creation from JWT claims functions"
    echo "  ✅ Task CRUD operations work with real database"
    echo "  ✅ Idempotency prevents duplicate operations"
    echo "  ✅ Proper error responses for invalid requests"
    echo "  ✅ User-scoped access control works"
    echo "  ✅ Data persists correctly in DynamoDB"
    echo ""
    echo "🎉 API Gateway integration testing complete!"
else
    echo ""
    echo "❌ Some tests failed. Please check the output above for details."
    exit 1
fi
