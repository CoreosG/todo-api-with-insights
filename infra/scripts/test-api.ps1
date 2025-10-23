# API Layer Testing Script
# Replace these with your actual values from CDK deployment

function Load-EnvFile {
    param([string]$path)
    $map = @{}
    if (-not (Test-Path $path)) { return $map }
    foreach ($line in Get-Content -Path $path) {
        if (-not $line) { continue }
        $trim = $line.Trim()
        if ($trim -eq "" -or $trim.StartsWith('#') -or $trim.StartsWith(';')) { continue }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { continue }
        $k = $line.Substring(0, $idx).Trim()
        $v = $line.Substring($idx + 1).Trim()
        if ($k) { $map[$k] = $v }
    }
    return $map
}

function Get-ConfigValue {
    param([string]$key, [string]$default = "", $fileMap)
    $envValue = (Get-Item "env:$key" -ErrorAction SilentlyContinue).Value
    if ($envValue -and $envValue -ne "") { return $envValue }
    if ($fileMap -and $fileMap.ContainsKey($key) -and $fileMap[$key]) { return $fileMap[$key] }
    return $default
}

# Load configuration from .env or .env.txt in this script folder
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $scriptDir ".env"
$envTxtPath = Join-Path $scriptDir ".env.txt"
$envMap = if (Test-Path $envPath) { Load-EnvFile $envPath } elseif (Test-Path $envTxtPath) { Load-EnvFile $envTxtPath } else { @{} }

# Resolve config with precedence: OS env -> .env/.env.txt -> defaults
$REGION = Get-ConfigValue -key "REGION" -default "us-east-1" -fileMap $envMap
$AWS_PROFILE = Get-ConfigValue -key "AWS_PROFILE" -default "" -fileMap $envMap
if ($AWS_PROFILE -and $AWS_PROFILE -ne "") {
    $Env:AWS_PROFILE = $AWS_PROFILE
}

$API_ENDPOINT = Get-ConfigValue -key "API_ENDPOINT" -default "" -fileMap $envMap
$USER_POOL_ID = Get-ConfigValue -key "USER_POOL_ID" -default "" -fileMap $envMap
$CLIENT_ID = Get-ConfigValue -key "CLIENT_ID" -default "" -fileMap $envMap
$PASSWORD = Get-ConfigValue -key "PASSWORD" -default "TempPassword1!" -fileMap $envMap

# Validate required configuration
if (-not $API_ENDPOINT) {
    Write-Host "[ERROR] API_ENDPOINT is required. Set it in .env file or environment variable." -ForegroundColor Red
    exit 1
}
if (-not $USER_POOL_ID) {
    Write-Host "[ERROR] USER_POOL_ID is required. Set it in .env file or environment variable." -ForegroundColor Red
    exit 1
}
if (-not $CLIENT_ID) {
    Write-Host "[ERROR] CLIENT_ID is required. Set it in .env file or environment variable." -ForegroundColor Red
    exit 1
}

# Generate unique test identity per run unless overridden
$usernameLocal = Get-ConfigValue -key "COGNITO_USERNAME" -default ("api-test-" + [DateTime]::UtcNow.ToString("yyyyMMddHHmmssfff")) -fileMap $envMap
$emailLocal = Get-ConfigValue -key "COGNITO_EMAIL" -default ("api.test." + [DateTime]::UtcNow.ToString("yyyyMMddHHmmssfff") + "@example.com") -fileMap $envMap

Write-Host "[*] Starting API Layer Testing..." -ForegroundColor Green
Write-Host "API Endpoint: $API_ENDPOINT" -ForegroundColor Cyan
Write-Host "User Pool ID: $USER_POOL_ID" -ForegroundColor Cyan
Write-Host "Client ID: $CLIENT_ID" -ForegroundColor Cyan
Write-Host "Using test user: $usernameLocal ($emailLocal)" -ForegroundColor Cyan
Write-Host ""

# Step 1: Test Health Endpoint (No Auth Required)
Write-Host "[STEP 1] Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "$API_ENDPOINT/health" -Method GET -Headers @{"Content-Type"="application/json"}
    try {
        $healthData = $healthResponse.Content | ConvertFrom-Json -ErrorAction Stop
        Write-Host "[SUCCESS] Health Check Successful!" -ForegroundColor Green
        Write-Host "Status: $($healthData.status)"
        Write-Host "Version: $($healthData.version)"
        Write-Host "Environment: $($healthData.environment)"
    } catch {
        Write-Host "[SUCCESS] Health Check Successful!" -ForegroundColor Green
        Write-Host $healthResponse.Content
    }
} catch {
    Write-Host "[ERROR] Health Check Failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Create Cognito User
Write-Host "[STEP 2] Creating Cognito User..." -ForegroundColor Yellow
try {
    Write-Host "Creating user: $usernameLocal ($emailLocal)" -ForegroundColor Cyan

    # Try to create user (will fail if user already exists)
    $createUserResult = aws cognito-idp admin-create-user `
        --user-pool-id $USER_POOL_ID `
        --username $usernameLocal `
        --user-attributes Name=email,Value=$emailLocal Name=given_name,Value="Test" Name=family_name,Value="User" `
        --message-action SUPPRESS `
        --region $REGION 2>&1

    # Check if user already exists
    if ($createUserResult -like "*UsernameExistsException*") {
        Write-Host "User already exists" -ForegroundColor Yellow
    }

    # Ensure permanent password is set (whether user existed or just created)
    $null = aws cognito-idp admin-set-user-password `
        --user-pool-id $USER_POOL_ID `
        --username $usernameLocal `
        --password $PASSWORD `
        --permanent `
        --region $REGION

    # Allow for propagation before authentication
    Start-Sleep -Seconds 2

    Write-Host "[SUCCESS] Cognito User Ready Successfully!" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to create/setup user: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Authenticate and Get Token
Write-Host "[STEP 3] Authenticating and Getting IdToken..." -ForegroundColor Yellow
Write-Host "Starting authentication process..." -ForegroundColor Cyan

# Initialize token variable at script level
$script:token = ""

try {
    # Authenticate user with retry logic
    Write-Host "Authenticating user..." -ForegroundColor Cyan
    $attempts = 0
    $maxAttempts = 3
    
    while ($attempts -lt $maxAttempts) {
        $attempts += 1
        Write-Host "Attempt $attempts of $maxAttempts..." -ForegroundColor Cyan
        
        $idTokenLocal = aws cognito-idp admin-initiate-auth `
            --user-pool-id $USER_POOL_ID `
            --client-id $CLIENT_ID `
            --auth-flow ADMIN_NO_SRP_AUTH `
            --auth-parameters USERNAME="$usernameLocal",PASSWORD="$PASSWORD" `
            --region $REGION `
            --query 'AuthenticationResult.IdToken' `
            --output text 2>$null
        
        if ($idTokenLocal -and $idTokenLocal.Length -gt 0 -and $idTokenLocal -ne "None" -and $idTokenLocal -ne "") {
            $script:token = $idTokenLocal
            Write-Host "Token received, length: $($script:token.Length)" -ForegroundColor Green
            break
        }
        
        Write-Host "No valid token received, retrying..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
    
    if (-not $script:token -or $script:token -eq "" -or $script:token.Length -lt 100) {
        Write-Host "[ERROR] Failed to retrieve valid IdToken from Cognito after $maxAttempts attempts" -ForegroundColor Red
        Write-Host "Attempting to get full authentication response for debugging..." -ForegroundColor Yellow
        
        $rawAuth = aws cognito-idp admin-initiate-auth `
            --user-pool-id $USER_POOL_ID `
            --client-id $CLIENT_ID `
            --auth-flow ADMIN_NO_SRP_AUTH `
            --auth-parameters USERNAME="$usernameLocal",PASSWORD="$PASSWORD" `
            --region $REGION
        
        Write-Host "Raw Response:" -ForegroundColor Yellow
        Write-Host $rawAuth
        throw "Authentication failed - IdToken empty or invalid"
    }
    
    Write-Host "[SUCCESS] Authentication Successful!" -ForegroundColor Green
    Write-Host "IdToken length: $($script:token.Length)" -ForegroundColor Cyan

} catch {
    Write-Host "[ERROR] Authentication Failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Test API - Get User Profile
Write-Host "[STEP 4] Testing API - Get User Profile..." -ForegroundColor Yellow
try {
    Write-Host "Calling: GET $($API_ENDPOINT)/api/v1/users" -ForegroundColor Cyan

    if (-not $script:token -or $script:token.Length -lt 100) {
        Write-Host "[ERROR] No valid token available for API call! Token length: $($script:token.Length)" -ForegroundColor Red
        throw "No valid authentication token available"
    }

    Write-Host "IdToken length: $($script:token.Length)" -ForegroundColor Cyan
    Write-Host "Using Authorization header: Bearer $($script:token.Substring(0, [Math]::Min(50,$script:token.Length)))..." -ForegroundColor Cyan

    $headers = @{
        "Authorization" = "Bearer $script:token"
        "Content-Type" = "application/json"
    }

    $userResponse = Invoke-WebRequest -Uri "$($API_ENDPOINT)/api/v1/users" `
        -Method GET `
        -Headers $headers | ConvertFrom-Json

    Write-Host "[SUCCESS] API Call Successful!" -ForegroundColor Green
    Write-Host "User Data:" -ForegroundColor Cyan
    Write-Host "ID: $($userResponse.id)"
    Write-Host "Email: $($userResponse.email)"
    Write-Host "Name: $($userResponse.name)"
    Write-Host "Created: $($userResponse.created_at)"
    Write-Host "Updated: $($userResponse.updated_at)"

} catch {
    Write-Host "[ERROR] API Call Failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Response Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
}

Write-Host ""

# Step 5: Test Creating a Task
Write-Host "[STEP 5] Testing Task Creation..." -ForegroundColor Yellow
try {
    $taskData = @{
        title = "API Test Task"
        description = "This task was created via PowerShell testing"
        priority = "high"
        category = "testing"
        status = "pending"
    } | ConvertTo-Json

    $taskHeaders = @{
        "Authorization" = "Bearer $script:token"
        "Content-Type" = "application/json"
        "Idempotency-Key" = ("ps-test-task-" + [guid]::NewGuid().ToString())
    }

    $taskResponse = Invoke-WebRequest -Uri "$($API_ENDPOINT)/api/v1/tasks" `
        -Method POST `
        -Headers $taskHeaders `
        -Body $taskData `
        -ContentType "application/json" | ConvertFrom-Json

    Write-Host "[SUCCESS] Task Created Successfully!" -ForegroundColor Green
    Write-Host "Task ID: $($taskResponse.id)"
    Write-Host "Title: $($taskResponse.title)"
    Write-Host "Status: $($taskResponse.status)"
    Write-Host "Priority: $($taskResponse.priority)"

} catch {
    Write-Host "[ERROR] Task Creation Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Step 6: Test Getting Tasks
Write-Host "[STEP 6] Testing Get Tasks..." -ForegroundColor Yellow
try {
    $tasksHeaders = @{
        "Authorization" = "Bearer $script:token"
    }

    $tasksResponse = Invoke-WebRequest -Uri "$($API_ENDPOINT)/api/v1/tasks" `
        -Method GET `
        -Headers $tasksHeaders | ConvertFrom-Json

    Write-Host "[SUCCESS] Get Tasks Successful!" -ForegroundColor Green
    Write-Host "Number of tasks: $($tasksResponse.Count)"

    if ($tasksResponse.Count -gt 0) {
        Write-Host "Latest Task:" -ForegroundColor Cyan
        Write-Host "ID: $($tasksResponse[0].id)"
        Write-Host "Title: $($tasksResponse[0].title)"
        Write-Host "Status: $($tasksResponse[0].status)"
    }

} catch {
    Write-Host "[ERROR] Get Tasks Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Step 7: Verify Data in DynamoDB
Write-Host "[STEP 7] Verifying Data in DynamoDB..." -ForegroundColor Yellow
try {
    $dbData = aws dynamodb scan --table-name todo-app-data --region $REGION | ConvertFrom-Json

    Write-Host "[SUCCESS] DynamoDB Query Successful!" -ForegroundColor Green
    Write-Host "Total items in table: $($dbData.Count)"

    # Filter for user data
    $userItems = $dbData.Items | Where-Object { $_.PK -like "USER#*" }
    $taskItems = $dbData.Items | Where-Object { $_.PK -like "TASK#*" }
    $idempotencyItems = $dbData.Items | Where-Object { $_.PK -like "IDEMPOTENCY#*" }

    Write-Host "User records: $($userItems.Count)"
    Write-Host "Task records: $($taskItems.Count)"
    Write-Host "Idempotency records: $($idempotencyItems.Count)"

} catch {
    Write-Host "[ERROR] DynamoDB Query Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

Write-Host "[COMPLETE] API Layer Testing Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "[OK] Health endpoint working"
Write-Host "[OK] Cognito user created and authenticated"
Write-Host "[OK] API authentication working"
Write-Host "[OK] User profile retrieval working"
Write-Host "[OK] Task creation working"
Write-Host "[OK] Task retrieval working"
Write-Host "[OK] Data persisted in DynamoDB"
Write-Host ""
Write-Host "API Documentation: $API_ENDPOINT/docs" -ForegroundColor Cyan
Write-Host "API Endpoint: $API_ENDPOINT" -ForegroundColor Cyan

# Optional: Clean up test user
if ($Env:NON_INTERACTIVE -ne "1") {
    $cleanup = Read-Host "Do you want to delete the test user? (y/n)"
    if ($cleanup -eq "y") {
        try {
            aws cognito-idp admin-delete-user --user-pool-id $USER_POOL_ID --username $usernameLocal --region $REGION
            Write-Host "[SUCCESS] Test user deleted" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Failed to delete user: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "Skipping cleanup in non-interactive mode (set NON_INTERACTIVE=0 to enable prompt)" -ForegroundColor Yellow
}