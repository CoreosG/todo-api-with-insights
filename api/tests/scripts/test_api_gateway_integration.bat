@echo off
REM API Gateway Integration Test Script for Windows Command Prompt
REM Run this script from the api directory

echo 🚀 Running API Gateway Integration Tests
echo ========================================

REM Check if we're in the right directory
if not exist "src\main.py" (
    echo ❌ Error: Please run this script from the api directory
    echo    Current directory: %CD%
    echo    Expected file: src\main.py
    pause
    exit /b 1
)

REM Set environment variables for testing
set USE_LOCAL_DYNAMODB=true
set DYNAMODB_ENDPOINT=http://localhost:8000

echo 📋 Test Configuration:
echo   - USE_LOCAL_DYNAMODB: %USE_LOCAL_DYNAMODB%
echo   - DYNAMODB_ENDPOINT: %DYNAMODB_ENDPOINT%
echo.

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: pytest is not installed or not in PATH
    echo    Please install pytest and pytest-asyncio:
    echo    pip install pytest pytest-asyncio
    pause
    exit /b 1
)

echo ✅ pytest is available
echo.

REM Run the comprehensive API Gateway integration tests
echo 🧪 Running comprehensive API Gateway integration tests...
python -m pytest "tests/integration/test_api_gateway_integration.py" -v --tb=short

REM Check the exit code and display results
if %errorlevel% equ 0 (
    echo.
    echo ✅ All API Gateway integration tests passed!
    echo.
    echo 📊 Test Summary:
    echo   ✅ API Gateway payload extraction works correctly
    echo   ✅ User auto-creation from JWT claims functions
    echo   ✅ Task CRUD operations work with real database
    echo   ✅ Idempotency prevents duplicate operations
    echo   ✅ Proper error responses for invalid requests
    echo   ✅ User-scoped access control works
    echo   ✅ Data persists correctly in DynamoDB
    echo.
    echo 🎉 API Gateway integration testing complete!
    echo.
    echo 💡 Next steps:
    echo    - Review test results above
    echo    - Check API_GATEWAY_INTEGRATION_TESTING_REPORT.md for details
    echo    - Ready for production deployment!
) else (
    echo.
    echo ❌ Some tests failed (Exit code: %errorlevel%)
    echo.
    echo 🔍 Troubleshooting:
    echo    - Check the test output above for specific error details
    echo    - Ensure all dependencies are installed
    echo    - Verify DynamoDB is running (if using real database tests)
    echo    - Check API_GATEWAY_INTEGRATION_TESTING_REPORT.md for known issues
    echo.
    echo 📞 For help, check the test file or documentation.
    pause
    exit /b %errorlevel%
)

pause
