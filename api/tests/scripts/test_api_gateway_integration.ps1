# API Gateway Integration Test Script for Windows PowerShell
# Run this script from the api directory

Write-Host "🚀 Running API Gateway Integration Tests" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Check if we're in the right directory
if (!(Test-Path "src/main.py")) {
    Write-Host "❌ Error: Please run this script from the api directory" -ForegroundColor Red
    Write-Host "   Current directory: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "   Expected file: src/main.py" -ForegroundColor Yellow
    exit 1
}

# Set environment variables for testing
$env:USE_LOCAL_DYNAMODB = "true"
$env:DYNAMODB_ENDPOINT = "http://localhost:8000"

Write-Host "📋 Test Configuration:" -ForegroundColor Cyan
Write-Host "  - USE_LOCAL_DYNAMODB: $env:USE_LOCAL_DYNAMODB" -ForegroundColor Cyan
Write-Host "  - DYNAMODB_ENDPOINT: $env:DYNAMODB_ENDPOINT" -ForegroundColor Cyan
Write-Host ""

# Check if pytest is available
try {
    $pytestVersion = & python -m pytest --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "pytest not found"
    }
    Write-Host "✅ pytest is available: $($pytestVersion.Trim())" -ForegroundColor Green
}
catch {
    Write-Host "❌ Error: pytest is not installed or not in PATH" -ForegroundColor Red
    Write-Host "   Please install pytest and pytest-asyncio:" -ForegroundColor Yellow
    Write-Host "   pip install pytest pytest-asyncio" -ForegroundColor Yellow
    exit 1
}

# Run the comprehensive API Gateway integration tests
Write-Host "🧪 Running comprehensive API Gateway integration tests..." -ForegroundColor Yellow

try {
    $startTime = Get-Date
    & python -m pytest "tests/integration/test_api_gateway_integration.py" -v --tb=short
    $exitCode = $LASTEXITCODE
    $endTime = Get-Date
    $duration = $endTime - $startTime
}
catch {
    Write-Host "❌ Error running tests: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Check the exit code and display results
if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ All API Gateway integration tests passed!" -ForegroundColor Green
    Write-Host "   Duration: $($duration.TotalSeconds.ToString("F2")) seconds" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📊 Test Summary:" -ForegroundColor Cyan
    Write-Host "  ✅ API Gateway payload extraction works correctly" -ForegroundColor Green
    Write-Host "  ✅ User auto-creation from JWT claims functions" -ForegroundColor Green
    Write-Host "  ✅ Task CRUD operations work with real database" -ForegroundColor Green
    Write-Host "  ✅ Idempotency prevents duplicate operations" -ForegroundColor Green
    Write-Host "  ✅ Proper error responses for invalid requests" -ForegroundColor Green
    Write-Host "  ✅ User-scoped access control works" -ForegroundColor Green
    Write-Host "  ✅ Data persists correctly in DynamoDB" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 API Gateway integration testing complete!" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "❌ Some tests failed (Exit code: $exitCode)" -ForegroundColor Red
    Write-Host "   Duration: $($duration.TotalSeconds.ToString("F2")) seconds" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🔍 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "   - Check the test output above for specific error details" -ForegroundColor White
    Write-Host "   - Ensure all dependencies are installed" -ForegroundColor White
    Write-Host "   - Verify DynamoDB is running (if using real database tests)" -ForegroundColor White
    Write-Host "   - Check API_GATEWAY_INTEGRATION_TESTING_REPORT.md for known issues" -ForegroundColor White
    Write-Host ""
    Write-Host "📞 For help, check the test file or documentation." -ForegroundColor Cyan
    exit $exitCode
}
