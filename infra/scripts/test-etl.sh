#!/bin/bash

# ETL Testing Script - Unix/Linux/Mac Version
# Creates multiple users and spams task creation/updates to generate CDC events for ETL testing

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
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

# ETL-specific configuration
NUM_USERS=$(get_config_value "NUM_USERS" "3" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")
TASKS_PER_USER=$(get_config_value "TASKS_PER_USER" "5" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")
UPDATES_PER_TASK=$(get_config_value "UPDATES_PER_TASK" "3" "$(declare -p map 2>/dev/null | sed 's/^declare -A map=//')")

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

echo -e "${GREEN}[*] Starting ETL Testing...${NC}"
echo -e "API Endpoint: $API_ENDPOINT"
echo -e "User Pool ID: $USER_POOL_ID"
echo -e "Client ID: $CLIENT_ID"
echo -e "Users to create: $NUM_USERS"
echo -e "Tasks per user: $TASKS_PER_USER"
echo -e "Updates per task: $UPDATES_PER_TASK"
echo ""

# Function to create/authenticate a user and return token
get_user_token() {
    local username="$1"
    local email="$2"

    echo -e "${CYAN}Setting up user: $username ($email)${NC}"

    # Create user if doesn't exist
    if create_result=$(aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$username" \
        --user-attributes Name=email,Value="$email" Name=given_name,Value="ETL" Name=family_name,Value="Test" \
        --message-action SUPPRESS \
        --region "$REGION" 2>&1); then

        if echo "$create_result" | grep -q "UsernameExistsException"; then
            echo -e "  ${YELLOW}User already exists${NC}"
        fi
    else
        echo -e "  ${YELLOW}Warning: User creation check failed: $create_result${NC}"
    fi

    # Set permanent password
    if aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$username" \
        --password "$PASSWORD" \
        --permanent \
        --region "$REGION" >/dev/null 2>&1; then
        :
    else
        echo -e "  ${YELLOW}Warning: Password set failed${NC}"
    fi

    # Authenticate and get token
    local attempts=0
    local max_attempts=3
    local token=""

    while [[ $attempts -lt $max_attempts && -z "$token" ]]; do
        attempts=$((attempts + 1))
        echo -e "  ${CYAN}Authentication attempt $attempts...${NC}"

        if id_token=$(aws cognito-idp admin-initiate-auth \
            --user-pool-id "$USER_POOL_ID" \
            --client-id "$CLIENT_ID" \
            --auth-flow ADMIN_NO_SRP_AUTH \
            --auth-parameters USERNAME="$username",PASSWORD="$PASSWORD" \
            --region "$REGION" \
            --query 'AuthenticationResult.IdToken' \
            --output text 2>/dev/null); then

            if [[ -n "$id_token" && "$id_token" != "None" && ${#id_token} -gt 100 ]]; then
                token="$id_token"
                echo -e "  ${GREEN}Token obtained successfully${NC}"
                break
            fi
        fi

        if [[ -z "$token" ]]; then
            sleep 2
        fi
    done

    if [[ -z "$token" ]]; then
        echo -e "  ${RED}Failed to authenticate user after $max_attempts attempts${NC}"
        return 1
    fi

    echo "$token"
}

# Function to create a task
create_task() {
    local token="$1"
    local task_number="$2"
    local user_id="$3"

    local task_data="{
        \"title\": \"ETL Test Task #$task_number\",
        \"description\": \"Generated task for ETL testing - User: $user_id - Created at: $(date '+%Y-%m-%d %H:%M:%S')\",
        \"priority\": \"$([task_number % 3 == 0] && echo "low" || [task_number % 3 == 1] && echo "medium" || echo "high")\",
        \"category\": \"$([task_number % 4 == 0] && echo "work" || [task_number % 4 == 1] && echo "personal" || [task_number % 4 == 2] && echo "shopping" || echo "health")\",
        \"status\": \"pending\"
    }"

    local idempotency_key="bash-etl-task-create-$user_id-$task_number-$(date +%s%3N)"

    if task_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_ENDPOINT/api/v1/tasks" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -H "Idempotency-Key: $idempotency_key" \
        -d "$task_data"); then

        http_status=$(echo "$task_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        body=$(echo "$task_response" | sed -e 's/HTTPSTATUS:.*//g')

        if [[ "$http_status" -eq 200 || "$http_status" -eq 201 ]]; then
            if echo "$body" | jq -r '.id' >/dev/null 2>&1; then
                echo "$body" | jq -r '.id'
                return 0
            fi
        fi
    fi

    echo ""
    return 1
}

# Function to update a task multiple times
update_task() {
    local token="$1"
    local task_id="$2"
    local updates="$3"
    local user_id="$4"

    local statuses=("pending" "in_progress" "completed")
    local priorities=("low" "medium" "high")

    for ((i=1; i<=updates; i++)); do
        local status_index=$((i % 3))
        local priority_index=$((i % 3))

        local update_data="{
            \"title\": \"ETL Test Task - Updated #$i\",
            \"description\": \"Updated task for ETL testing - User: $user_id - Update: $i - Time: $(date '+%Y-%m-%d %H:%M:%S')\",
            \"priority\": \"${priorities[$priority_index]}\",
            \"status\": \"${statuses[$status_index]}\"
        }"

        local idempotency_key="bash-etl-task-update-$task_id-$i-$(date +%s%3N)"

        if update_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X PUT "$API_ENDPOINT/api/v1/tasks/$task_id" \
            -H "Authorization: Bearer $token" \
            -H "Content-Type: application/json" \
            -H "Idempotency-Key: $idempotency_key" \
            -d "$update_data"); then

            http_status=$(echo "$update_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

            if [[ "$http_status" -eq 200 ]]; then
                echo -e "    ${GRAY}Task $task_id updated ($i/$updates)${NC}"
            else
                echo -e "    ${YELLOW}Failed to update task $task_id (attempt $i): HTTP $http_status${NC}"
            fi
        else
            echo -e "    ${YELLOW}Failed to update task $task_id (attempt $i): curl error${NC}"
        fi

        # Small delay between updates
        sleep 0.5
    done
}

# Main ETL testing logic
total_tasks_created=0
total_updates_performed=0
declare -A user_tokens

# Step 1: Create users and get tokens
echo -e "${YELLOW}[STEP 1] Creating Users and Obtaining Tokens...${NC}"

for ((user_num=1; user_num<=NUM_USERS; user_num++)); do
    username="etl-user-$user_num-$(date +%Y%m%d%H%M%S)"
    email="etl.user$user_num.$(date +%Y%m%d%H%M%S%3N)@example.com"

    echo -e "${CYAN}Creating user $user_num/$NUM_USERS...${NC}"

    if token=$(get_user_token "$username" "$email"); then
        user_tokens["$username"]="$token:$user_num:$email"
        echo -e "  ${GREEN}User $user_num ready with token${NC}"
    else
        echo -e "  ${RED}Failed to set up user $user_num${NC}"
    fi

    # Small delay between users
    sleep 1
done

echo ""
echo -e "${YELLOW}[STEP 2] Creating and Updating Tasks for ETL Data Generation...${NC}"

# Step 2: For each user, create tasks and update them
for user_key in "${!user_tokens[@]}"; do
    IFS=':' read -r token user_num email <<< "${user_tokens[$user_key]}"

    echo -e "${CYAN}Processing user $user_num ($user_key)...${NC}"

    task_ids=()

    # Create tasks for this user
    for ((task_num=1; task_num<=TASKS_PER_USER; task_num++)); do
        echo -e "  ${GRAY}Creating task $task_num/$TASKS_PER_USER...${NC}"

        if task_id=$(create_task "$token" "$task_num" "$user_key"); then
            task_ids+=("$task_id")
            total_tasks_created=$((total_tasks_created + 1))
            echo -e "    ${GREEN}Created task: $task_id${NC}"

            # Update the task multiple times
            update_task "$token" "$task_id" "$UPDATES_PER_TASK" "$user_key"
            total_updates_performed=$((total_updates_performed + UPDATES_PER_TASK))
        else
            echo -e "    ${RED}Failed to create task $task_num${NC}"
        fi

        # Small delay between task creation
        sleep 0.2
    done

    echo -e "  ${GREEN}User $user_num completed: ${#task_ids[@]} tasks created${NC}"
    echo ""
done

# Step 3: Verify data in DynamoDB
echo -e "${YELLOW}[STEP 3] Verifying Data Generation in DynamoDB...${NC}"

if db_response=$(aws dynamodb scan --table-name todo-app-data --region "$REGION" 2>/dev/null); then
    echo -e "${GREEN}[SUCCESS] DynamoDB Query Successful!${NC}"

    if echo "$db_response" | jq . >/dev/null 2>&1; then
        item_count=$(echo "$db_response" | jq '.Count')
        echo -e "Current table statistics:"
        echo -e "  Total items in table: $item_count"

        # Filter for different types of data
        user_items=$(echo "$db_response" | jq '.Items[] | select(.PK | startswith("USER#"))')
        task_items=$(echo "$db_response" | jq '.Items[] | select(.PK | startswith("TASK#"))')
        idempotency_items=$(echo "$db_response" | jq '.Items[] | select(.PK | startswith("IDEMPOTENCY#"))')

        user_count=$(echo "$user_items" | jq -s 'length')
        task_count=$(echo "$task_items" | jq -s 'length')
        idempotency_count=$(echo "$idempotency_items" | jq -s 'length')

        echo -e "  User records: $user_count"
        echo -e "  Task records: $task_count"
        echo -e "  Idempotency records: $idempotency_count"
    else
        echo -e "  Total items in table: $(echo "$db_response" | grep -c '"PK":' || echo "0")"
    fi
else
    echo -e "${RED}[ERROR] DynamoDB Query Failed${NC}"
fi

echo ""
echo -e "${GREEN}[COMPLETE] ETL Testing Complete!${NC}"
echo ""
echo -e "${CYAN}=== ETL TEST SUMMARY ===${NC}"
echo "Users created: ${#user_tokens[@]}"
echo "Tasks created: $total_tasks_created"
echo "Task updates performed: $total_updates_performed"
echo "Expected CDC events generated: $(($total_tasks_created * ($UPDATES_PER_TASK + 1) + ${#user_tokens[@]}))"
echo ""
echo "This should trigger the ETL pipeline:"
echo "  - Bronze layer: CDC events from DynamoDB streams"
echo "  - Silver layer: Transformed user/task data"
echo "  - Gold layer: Analytics and business metrics"
echo ""
echo -e "Check CloudWatch logs and S3 buckets for ETL processing results."
echo ""

# Optional: Clean up test users
if [[ "${NON_INTERACTIVE:-0}" != "1" ]]; then
    read -p "Do you want to delete the test users? (y/n): " cleanup
    if [[ "$cleanup" == "y" || "$cleanup" == "Y" ]]; then
        for user_key in "${!user_tokens[@]}"; do
            if aws cognito-idp admin-delete-user --user-pool-id "$USER_POOL_ID" --username "$user_key" --region "$REGION" >/dev/null 2>&1; then
                echo -e "${GREEN}[SUCCESS] Deleted user: $user_key${NC}"
            else
                echo -e "${RED}[ERROR] Failed to delete user $user_key${NC}"
            fi
        done
    fi
else
    echo "Skipping cleanup in non-interactive mode (set NON_INTERACTIVE=0 to enable prompt)"
fi
