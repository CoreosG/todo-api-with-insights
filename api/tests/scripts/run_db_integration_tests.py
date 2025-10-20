#!/usr/bin/env python3
"""
Script to run integration tests with local DynamoDB.

This script helps set up the environment and run the integration tests
that connect to a real local DynamoDB instance.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Main function to run integration tests with local DynamoDB."""
    print("Setting up integration tests with local DynamoDB...")
    print()

    # Set environment variables for local DynamoDB
    os.environ["DYNAMODB_ENDPOINT"] = "http://localhost:8000"
    os.environ["USE_LOCAL_DYNAMODB"] = "true"
    os.environ["AWS_ACCESS_KEY_ID"] = "dummy"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy"

    print("Prerequisites:")
    print("   1. Make sure DynamoDB is running locally:")
    print("      docker run -p 8000:8000 amazon/dynamodb-local")
    print("   2. The tests will connect to localhost:8000")
    print()

    # Change to the api directory
    api_dir = Path(__file__).parent.parent.parent
    os.chdir(api_dir)

    print(f"Working directory: {api_dir}")
    print()

    # Check if DynamoDB is available
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Try to connect to DynamoDB
        dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url="http://localhost:8000",
            region_name="us-east-1",
            aws_access_key_id="dummy",
            aws_secret_access_key="dummy"
        )

        # List tables to test connection
        tables = list(dynamodb.tables.all())
        print(f"Connected to local DynamoDB. Found {len(tables)} existing tables.")

        # Check if our table exists
        table_names = [table.name for table in tables]
        if "todo-app-data" in table_names:
            print("Table 'todo-app-data' already exists.")
        else:
            print("Table 'todo-app-data' will be created by the tests.")

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("Cannot connect to local DynamoDB.")
            print("   Please start DynamoDB with: docker run -p 8000:8000 amazon/dynamodb-local")
            return 1
        else:
            print(f"Error connecting to DynamoDB: {e}")
            return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    print()
    print("Running integration tests with real local DynamoDB...")
    print()

    # Run the tests
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/integration/test_api_gateway_integration_with_db.py",
        "-v"
    ])

    print()
    if result.returncode == 0:
        print("All integration tests with local DynamoDB passed!")
    else:
        print("Some tests failed. Check the output above for details.")
        print()
        print("Troubleshooting tips:")
        print("   - Make sure DynamoDB is running: docker run -p 8000:8000 amazon/dynamodb-local")
        print("   - Check that the endpoint URL is correct")
        print("   - Verify AWS credentials are set (dummy values work for local)")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
