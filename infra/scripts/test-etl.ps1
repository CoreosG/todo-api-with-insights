# ETL Testing Script
# Creates multiple users and spams task creation/updates to generate CDC events for ETL testing

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

# ETL-specific configuration
$NUM_USERS = [int](Get-ConfigValue -key "NUM_USERS" -default "3" -fileMap $envMap)
$TASKS_PER_USER = [int](Get-ConfigValue -key "TASKS_PER_USER" -default "5" -fileMap $envMap)
$UPDATES_PER_TASK = [int](Get-ConfigValue -key "UPDATES_PER_TASK" -default "3" -fileMap $envMap)

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

Write-Host "[*] Starting ETL Testing..." -ForegroundColor Green
Write-Host "API Endpoint: $API_ENDPOINT" -ForegroundColor Cyan
Write-Host "User Pool ID: $USER_POOL_ID" -ForegroundColor Cyan
Write-Host "Client ID: $CLIENT_ID" -ForegroundColor Cyan
Write-Host "Users to create: $NUM_USERS" -ForegroundColor Cyan
Write-Host "Tasks per user: $TASKS_PER_USER" -ForegroundColor Cyan
Write-Host "Updates per task: $UPDATES_PER_TASK" -ForegroundColor Cyan
Write-Host ""

# Function to create/authenticate a user and return token
function Get-UserToken {
    param([string]$username, [string]$email)

    Write-Host "Setting up user: $username ($email)" -ForegroundColor Cyan

    # Create user if doesn't exist
    try {
        $createResult = aws cognito-idp admin-create-user `
            --user-pool-id $USER_POOL_ID `
            --username $username `
            --user-attributes Name=email,Value=$email Name=given_name,Value="ETL" Name=family_name,Value="Test" `
            --message-action SUPPRESS `
            --region $REGION 2>&1

        if ($createResult -like "*UsernameExistsException*") {
            Write-Host "  User already exists" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Warning: User creation check failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    # Set permanent password
    try {
        $null = aws cognito-idp admin-set-user-password `
            --user-pool-id $USER_POOL_ID `
            --username $username `
            --password $PASSWORD `
            --permanent `
            --region $REGION
    } catch {
        Write-Host "  Warning: Password set failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    # Authenticate and get token
    $attempts = 0
    $maxAttempts = 3
    $token = ""

    while ($attempts -lt $maxAttempts -and -not $token) {
        $attempts += 1
        Write-Host "  Authentication attempt $attempts..." -ForegroundColor Cyan

        try {
            $authResult = aws cognito-idp admin-initiate-auth `
                --user-pool-id $USER_POOL_ID `
                --client-id $CLIENT_ID `
                --auth-flow ADMIN_NO_SRP_AUTH `
                --auth-parameters USERNAME="$username",PASSWORD="$PASSWORD" `
                --region $REGION `
                --query 'AuthenticationResult.IdToken' `
                --output text 2>$null

            if ($authResult -and $authResult -ne "None" -and $authResult.Length -gt 100) {
                $token = $authResult
                Write-Host "  Token obtained successfully" -ForegroundColor Green
                break
            }
        } catch {
            Write-Host "  Auth attempt failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }

        if (-not $token) {
            Start-Sleep -Seconds 2
        }
    }

    if (-not $token) {
        Write-Host "  Failed to authenticate user after $maxAttempts attempts" -ForegroundColor Red
        return $null
    }

    return $token
}

# Function to create a task
function Create-Task {
    param([string]$token, [int]$taskNumber, [string]$userId)

    $taskData = @{
        title = "ETL Test Task #$taskNumber"
        description = "Generated task for ETL testing - User: $userId - Created at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        priority = @("low", "medium", "high")[$taskNumber % 3]
        category = @("work", "personal", "shopping", "health")[$taskNumber % 4]
        status = "pending"
    } | ConvertTo-Json

    $idempotencyKey = "etl-task-create-$userId-$taskNumber-$(Get-Date -Format 'yyyyMMddHHmmssfff')"

    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
        "Idempotency-Key" = $idempotencyKey
    }

    try {
        $response = Invoke-WebRequest -Uri "$($API_ENDPOINT)/api/v1/tasks" `
            -Method POST `
            -Headers $headers `
            -Body $taskData `
            -ContentType "application/json" | ConvertFrom-Json

        return $response.id
    } catch {
        Write-Host "  Failed to create task: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# Function to update a task multiple times
function Update-Task {
    param([string]$token, [string]$taskId, [int]$updates, [string]$userId)

    $statuses = @("pending", "in_progress", "completed")
    $priorities = @("low", "medium", "high")

    for ($i = 1; $i -le $updates; $i++) {
        $updateData = @{
            title = "ETL Test Task - Updated #$i"
            description = "Updated task for ETL testing - User: $userId - Update: $i - Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
            priority = $priorities[$i % 3]
            status = $statuses[$i % 3]
        } | ConvertTo-Json

        $idempotencyKey = "etl-task-update-$taskId-$i-$(Get-Date -Format 'yyyyMMddHHmmssfff')"

        $headers = @{
            "Authorization" = "Bearer $token"
            "Content-Type" = "application/json"
            "Idempotency-Key" = $idempotencyKey
        }

        try {
            $response = Invoke-WebRequest -Uri "$($API_ENDPOINT)/api/v1/tasks/$taskId" `
                -Method PUT `
                -Headers $headers `
                -Body $updateData `
                -ContentType "application/json" | ConvertFrom-Json

            Write-Host "    Task $taskId updated ($i/$updates)" -ForegroundColor Gray
        } catch {
            Write-Host "    Failed to update task $taskId (attempt $i): $($_.Exception.Message)" -ForegroundColor Yellow
        }

        # Small delay between updates
        Start-Sleep -Milliseconds 500
    }
}

# Main ETL testing logic
$totalTasksCreated = 0
$totalUpdatesPerformed = 0
$userTokens = @{}

# Step 1: Create users and get tokens
Write-Host "[STEP 1] Creating Users and Obtaining Tokens..." -ForegroundColor Yellow

for ($userNum = 1; $userNum -le $NUM_USERS; $userNum++) {
    $username = "etl-user-$userNum-$(Get-Date -Format 'yyyyMMddHHmmss')"
    $email = "etl.user$userNum.$(Get-Date -Format 'yyyyMMddHHmmssfff')@example.com"

    Write-Host "Creating user $userNum/$NUM_USERS..." -ForegroundColor Cyan

    $token = Get-UserToken -username $username -email $email
    if ($token) {
        $userTokens[$username] = @{ Token = $token; Email = $email; UserNum = $userNum }
        Write-Host "  User $userNum ready with token" -ForegroundColor Green
    } else {
        Write-Host "  Failed to set up user $userNum" -ForegroundColor Red
    }

    # Small delay between users
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "[STEP 2] Creating and Updating Tasks for ETL Data Generation..." -ForegroundColor Yellow

# Step 2: For each user, create tasks and update them
foreach ($userEntry in $userTokens.GetEnumerator()) {
    $username = $userEntry.Key
    $userData = $userEntry.Value
    $token = $userData.Token
    $userNum = $userData.UserNum

    Write-Host "Processing user $userNum ($username)..." -ForegroundColor Cyan

    $taskIds = @()

    # Create tasks for this user
    for ($taskNum = 1; $taskNum -le $TASKS_PER_USER; $taskNum++) {
        Write-Host "  Creating task $taskNum/$TASKS_PER_USER..." -ForegroundColor Gray

        $taskId = Create-Task -token $token -taskNumber $taskNum -userId $username
        if ($taskId) {
            $taskIds += $taskId
            $totalTasksCreated++
            Write-Host "    Created task: $taskId" -ForegroundColor Green

            # Update the task multiple times
            Update-Task -token $token -taskId $taskId -updates $UPDATES_PER_TASK -userId $username
            $totalUpdatesPerformed += $UPDATES_PER_TASK
        } else {
            Write-Host "    Failed to create task $taskNum" -ForegroundColor Red
        }

        # Small delay between task creation
        Start-Sleep -Milliseconds 200
    }

    Write-Host "  User $userNum completed: $($taskIds.Count) tasks created" -ForegroundColor Green
    Write-Host ""
}

# Step 3: Verify data in DynamoDB
Write-Host "[STEP 3] Verifying Data Generation in DynamoDB..." -ForegroundColor Yellow

try {
    $dbData = aws dynamodb scan --table-name todo-app-data --region $REGION | ConvertFrom-Json

    Write-Host "[SUCCESS] DynamoDB Query Successful!" -ForegroundColor Green

    $userItems = $dbData.Items | Where-Object { $_.PK -like "USER#" }
    $taskItems = $dbData.Items | Where-Object { $_.PK -like "TASK#" }
    $idempotencyItems = $dbData.Items | Where-Object { $_.PK -like "IDEMPOTENCY#" }

    Write-Host "Current table statistics:" -ForegroundColor Cyan
    Write-Host "  Total items: $($dbData.Count)"
    Write-Host "  User records: $($userItems.Count)"
    Write-Host "  Task records: $($taskItems.Count)"
    Write-Host "  Idempotency records: $($idempotencyItems.Count)"

} catch {
    Write-Host "[ERROR] DynamoDB Query Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "[COMPLETE] ETL Testing Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "=== ETL TEST SUMMARY ===" -ForegroundColor Cyan
Write-Host "Users created: $($userTokens.Count)"
Write-Host "Tasks created: $totalTasksCreated"
Write-Host "Task updates performed: $totalUpdatesPerformed"
Write-Host "Expected CDC events generated: $(($totalTasksCreated * ($UPDATES_PER_TASK + 1)) + $userTokens.Count)"
Write-Host ""
Write-Host "This should trigger the ETL pipeline:"
Write-Host "  - Bronze layer: CDC events from DynamoDB streams"
Write-Host "  - Silver layer: Transformed user/task data"
Write-Host "  - Gold layer: Analytics and business metrics"
Write-Host ""
Write-Host "Check CloudWatch logs and S3 buckets for ETL processing results." -ForegroundColor Yellow

# Optional: Clean up test users
if ($Env:NON_INTERACTIVE -ne "1") {
    $cleanup = Read-Host "Do you want to delete the test users? (y/n)"
    if ($cleanup -eq "y") {
        foreach ($userEntry in $userTokens.GetEnumerator()) {
            $username = $userEntry.Key
            try {
                aws cognito-idp admin-delete-user --user-pool-id $USER_POOL_ID --username $username --region $REGION
                Write-Host "[SUCCESS] Deleted user: $username" -ForegroundColor Green
            } catch {
                Write-Host "[ERROR] Failed to delete user $username : $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
} else {
    Write-Host "Skipping cleanup in non-interactive mode (set NON_INTERACTIVE=0 to enable prompt)" -ForegroundColor Yellow
}
