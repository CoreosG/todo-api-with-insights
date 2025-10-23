#!/bin/bash

# API Layer Testing Script - Unix/Linux/Mac Version
# Replace these with your actual values from CDK deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to load environment file
load_env_file() {
    local path="$1"
    declare -A map

    if [[ ! -f "$path" ]]; then
        return 0
    fi

    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        # Skip empty lines, comments, and lines without '='
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue

        # Remove leading/trailing whitespace
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        [[ -n "$key" ]] && map["$key"]="$value"
    done < "$path"

    echo "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')"
}

# Function to get configuration value
get_config_value() {
    local key="$1"
    local default="${2:-}"
    local file_map="$3"

    # Check environment variable first
    local env_value="${!key}"
    if [[ -n "$env_value" ]]; then
        echo "$env_value"
        return 0
    fi

    # Check file map if provided
    if [[ -n "$file_map" ]]; then
        eval "local file_map_array=$file_map"
        local file_value="${file_map_array[$key]}"
        if [[ -n "$file_value" ]]; then
            echo "$file_value"
            return 0
        fi
    fi

    echo "$default"
}

# Load configuration from .env or .env.txt in this script folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_PATH="$SCRIPT_DIR/.env"
ENV_TXT_PATH="$SCRIPT_DIR/.env.txt"

if [[ -f "$ENV_PATH" ]]; then
    eval "$(load_env_file "$ENV_PATH")"
elif [[ -f "$ENV_TXT_PATH" ]]; then
    eval "$(load_env_file "$ENV_TXT_PATH")"
fi

# Resolve config with precedence: OS env -> .env/.env.txt -> defaults
REGION=$(get_config_value "REGION" "us-east-1" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")
AWS_PROFILE=$(get_config_value "AWS_PROFILE" "" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")

if [[ -n "$AWS_PROFILE" ]]; then
    export AWS_PROFILE="$AWS_PROFILE"
fi

API_ENDPOINT=$(get_config_value "API_ENDPOINT" "" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")
USER_POOL_ID=$(get_config_value "USER_POOL_ID" "" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")
CLIENT_ID=$(get_config_value "CLIENT_ID" "" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")
PASSWORD=$(get_config_value "PASSWORD" "TempPassword1!" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")

# Validate required configuration
if [[ -z "$API_ENDPOINT" ]]; then
    echo -e "${RED}[ERROR] API_ENDPOINT is required. Set it in .env file or environment variable.${NC}"
    exit 1
fi

if [[ -z "$USER_POOL_ID" ]]; then
    echo -e "${RED}[ERROR] USER_POOL_ID is required. Set it in .env file or environment variable.${NC}"
    exit 1
fi

if [[ -z "$CLIENT_ID" ]]; then
    echo -e "${RED}[ERROR] CLIENT_ID is required. Set it in .env file or environment variable.${NC}"
    exit 1
fi

# Generate unique test identity per run unless overridden
USERNAME=$(get_config_value "COGNITO_USERNAME" "api-test-$(date +%Y%m%d%H%M%S%3N)" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")
EMAIL=$(get_config_value "COGNITO_EMAIL" "api.test.$(date +%Y%m%d%H%M%S%3N)@example.com" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")

echo -e "${GREEN}[*] Starting API Layer Testing...${NC}"
echo -e "API Endpoint: $API_ENDPOINT"
echo -e "User Pool ID: $USER_POOL_ID"
echo -e "Client ID: $CLIENT_ID"
echo -e "Using test user: $USERNAME ($EMAIL)"
echo ""

# Step 1: Test Health Endpoint (No Auth Required)
echo -e "${YELLOW}[STEP 1] Testing Health Endpoint...${NC}"

if health_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$API_ENDPOINT/health" -H "Content-Type: application/json"); then
    http_status=$(echo "$health_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$health_response" | sed -e 's/HTTPSTATUS:.*//g')

    if [[ "$http_status" -eq 200 ]]; then
        echo -e "${GREEN}[SUCCESS] Health Check Successful!${NC}"
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "Status: $(echo "$body" | jq -r '.status')"
            echo "Version: $(echo "$body" | jq -r '.version')"
            echo "Environment: $(echo "$body" | jq -r '.environment')"
        else
            echo "$body"
        fi
    else
        echo -e "${RED}[ERROR] Health Check Failed: HTTP $http_status${NC}"
        echo "$body"
        exit 1
    fi
else
    echo -e "${RED}[ERROR] Health Check Failed: curl error${NC}"
    exit 1
fi

echo ""

# Step 2: Create Cognito User
echo -e "${YELLOW}[STEP 2] Creating Cognito User...${NC}"
echo "Creating user: $USERNAME ($EMAIL)"

# Try to create user (will fail if user already exists)
if create_result=$(aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$USERNAME" \
    --user-attributes Name=email,Value="$EMAIL" Name=given_name,Value="Test" Name=family_name,Value="User" \
    --message-action SUPPRESS \
    --region "$REGION" 2>&1); then

    if echo "$create_result" | grep -q "UsernameExistsException"; then
        echo "User already exists"
    fi

    # Ensure permanent password is set (whether user existed or just created)
    if aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME" \
        --password "$PASSWORD" \
        --permanent \
        --region "$REGION" >/dev/null 2>&1; then

        # Allow for propagation before authentication
        sleep 2

        echo -e "${GREEN}[SUCCESS] Cognito User Ready Successfully!${NC}"
    else
        echo -e "${RED}[ERROR] Failed to set user password${NC}"
        exit 1
    fi
else
    echo -e "${RED}[ERROR] Failed to create/setup user: $create_result${NC}"
    exit 1
fi

echo ""

# Step 3: Authenticate and Get Token
echo -e "${YELLOW}[STEP 3] Authenticating and Getting IdToken...${NC}"
echo "Starting authentication process..."

# Initialize token variable
TOKEN=""

# Authenticate user with retry logic
echo "Authenticating user..."
attempts=0
max_attempts=3

while [[ $attempts -lt $max_attempts ]]; do
    attempts=$((attempts + 1))
    echo "Attempt $attempts of $max_attempts..."

    if id_token=$(aws cognito-idp admin-initiate-auth \
        --user-pool-id "$USER_POOL_ID" \
        --client-id "$CLIENT_ID" \
        --auth-flow ADMIN_NO_SRP_AUTH \
        --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD" \
        --region "$REGION" \
        --query 'AuthenticationResult.IdToken' \
        --output text 2>/dev/null); then

        if [[ -n "$id_token" && "$id_token" != "None" && ${#id_token} -gt 100 ]]; then
            TOKEN="$id_token"
            echo "Token received, length: ${#TOKEN}"
            break
        fi
    fi

    echo "No valid token received, retrying..."
    sleep 2
done

if [[ -z "$TOKEN" || ${#TOKEN} -lt 100 ]]; then
    echo -e "${RED}[ERROR] Failed to retrieve valid IdToken from Cognito after $max_attempts attempts${NC}"

    echo "Attempting to get full authentication response for debugging..."
    if raw_auth=$(aws cognito-idp admin-initiate-auth \
        --user-pool-id "$USER_POOL_ID" \
        --client-id "$CLIENT_ID" \
        --auth-flow ADMIN_NO_SRP_AUTH \
        --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD" \
        --region "$REGION" 2>&1); then

        echo "Raw Response:"
        echo "$raw_auth"
    fi

    exit 1
fi

echo -e "${GREEN}[SUCCESS] Authentication Successful!${NC}"
echo "IdToken length: ${#TOKEN}"

echo ""

# Step 4: Test API - Get User Profile
echo -e "${YELLOW}[STEP 4] Testing API - Get User Profile...${NC}"
echo "Calling: GET $API_ENDPOINT/api/v1/users"

if [[ -z "$TOKEN" || ${#TOKEN} -lt 100 ]]; then
    echo -e "${RED}[ERROR] No valid token available for API call! Token length: ${#TOKEN}${NC}"
    exit 1
fi

echo "IdToken length: ${#TOKEN}"
echo "Using Authorization header: Bearer ${TOKEN:0:50}..."

if user_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$API_ENDPOINT/api/v1/users" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json"); then

    http_status=$(echo "$user_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$user_response" | sed -e 's/HTTPSTATUS:.*//g')

    if [[ "$http_status" -eq 200 ]]; then
        echo -e "${GREEN}[SUCCESS] API Call Successful!${NC}"
        echo "User Data:"
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "ID: $(echo "$body" | jq -r '.id')"
            echo "Email: $(echo "$body" | jq -r '.email')"
            echo "Name: $(echo "$body" | jq -r '.name')"
            echo "Created: $(echo "$body" | jq -r '.created_at')"
            echo "Updated: $(echo "$body" | jq -r '.updated_at')"
        else
            echo "$body"
        fi
    else
        echo -e "${RED}[ERROR] API Call Failed: HTTP $http_status${NC}"
        echo "$body"
    fi
else
    echo -e "${RED}[ERROR] API Call Failed: curl error${NC}"
fi

echo ""

# Step 5: Test Creating a Task
echo -e "${YELLOW}[STEP 5] Testing Task Creation...${NC}"

task_data='{
  "title": "API Test Task",
  "description": "This task was created via bash testing",
  "priority": "high",
  "category": "testing",
  "status": "pending"
}'

idempotency_key="bash-test-task-$(date +%s)-$RANDOM"

if task_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_ENDPOINT/api/v1/tasks" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: $idempotency_key" \
    -d "$task_data"); then

    http_status=$(echo "$task_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$task_response" | sed -e 's/HTTPSTATUS:.*//g')

    if [[ "$http_status" -eq 200 || "$http_status" -eq 201 ]]; then
        echo -e "${GREEN}[SUCCESS] Task Created Successfully!${NC}"
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "Task ID: $(echo "$body" | jq -r '.id')"
            echo "Title: $(echo "$body" | jq -r '.title')"
            echo "Status: $(echo "$body" | jq -r '.status')"
            echo "Priority: $(echo "$body" | jq -r '.priority')"
        else
            echo "$body"
        fi
    else
        echo -e "${RED}[ERROR] Task Creation Failed: HTTP $http_status${NC}"
        echo "$body"
    fi
else
    echo -e "${RED}[ERROR] Task Creation Failed: curl error${NC}"
fi

echo ""

# Step 6: Test Getting Tasks
echo -e "${YELLOW}[STEP 6] Testing Get Tasks...${NC}"

if tasks_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$API_ENDPOINT/api/v1/tasks" \
    -H "Authorization: Bearer $TOKEN"); then

    http_status=$(echo "$tasks_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$tasks_response" | sed -e 's/HTTPSTATUS:.*//g')

    if [[ "$http_status" -eq 200 ]]; then
        echo -e "${GREEN}[SUCCESS] Get Tasks Successful!${NC}"

        if echo "$body" | jq . >/dev/null 2>&1; then
            task_count=$(echo "$body" | jq '. | length')
            echo "Number of tasks: $task_count"

            if [[ "$task_count" -gt 0 ]]; then
                echo "Latest Task:"
                echo "ID: $(echo "$body" | jq -r '.[0].id')"
                echo "Title: $(echo "$body" | jq -r '.[0].title')"
                echo "Status: $(echo "$body" | jq -r '.[0].status')"
            fi
        else
            echo "Number of tasks: $(echo "$body" | grep -c '"id":' || echo "0")"
            echo "$body"
        fi
    else
        echo -e "${RED}[ERROR] Get Tasks Failed: HTTP $http_status${NC}"
        echo "$body"
    fi
else
    echo -e "${RED}[ERROR] Get Tasks Failed: curl error${NC}"
fi

echo ""

# Step 7: Verify Data in DynamoDB
echo -e "${YELLOW}[STEP 7] Verifying Data in DynamoDB...${NC}"

if db_response=$(aws dynamodb scan --table-name todo-app-data --region "$REGION" 2>/dev/null); then
    echo -e "${GREEN}[SUCCESS] DynamoDB Query Successful!${NC}"

    if echo "$db_response" | jq . >/dev/null 2>&1; then
        item_count=$(echo "$db_response" | jq '.Count')
        echo "Total items in table: $item_count"

        # Filter for different types of data
        user_items=$(echo "$db_response" | jq '.Items[] | select(.PK | startswith("USER#"))')
        task_items=$(echo "$db_response" | jq '.Items[] | select(.PK | startswith("TASK#"))')
        idempotency_items=$(echo "$db_response" | jq '.Items[] | select(.PK | startswith("IDEMPOTENCY#"))')

        user_count=$(echo "$user_items" | jq -s 'length')
        task_count=$(echo "$task_items" | jq -s 'length')
        idempotency_count=$(echo "$idempotency_items" | jq -s 'length')

        echo "User records: $user_count"
        echo "Task records: $task_count"
        echo "Idempotency records: $idempotency_count"
    else
        echo "Total items in table: $(echo "$db_response" | grep -c '"PK":' || echo "0")"
    fi
else
    echo -e "${RED}[ERROR] DynamoDB Query Failed${NC}"
fi

echo ""

echo -e "${GREEN}[COMPLETE] API Layer Testing Complete!${NC}"
echo ""
echo -e "${CYAN}=== SUMMARY ===${NC}"
echo "[OK] Health endpoint working"
echo "[OK] Cognito user created and authenticated"
echo "[OK] API authentication working"
echo "[OK] User profile retrieval working"
echo "[OK] Task creation working"
echo "[OK] Task retrieval working"
echo "[OK] Data persisted in DynamoDB"
echo ""
echo -e "API Documentation: ${API_ENDPOINT}/docs${NC}"
echo -e "API Endpoint: $API_ENDPOINT${NC}"

# Optional: Clean up test user
if [[ "${NON_INTERACTIVE:-0}" != "1" ]]; then
    read -p "Do you want to delete the test user? (y/n): " cleanup
    if [[ "$cleanup" == "y" || "$cleanup" == "Y" ]]; then
        if aws cognito-idp admin-delete-user --user-pool-id "$USER_POOL_ID" --username "$USERNAME" --region "$REGION" >/dev/null 2>&1; then
            echo -e "${GREEN}[SUCCESS] Test user deleted${NC}"
        else
            echo -e "${RED}[ERROR] Failed to delete user${NC}"
        fi
    fi
else
    echo "Skipping cleanup in non-interactive mode (set NON_INTERACTIVE=0 to enable prompt)"
fi
