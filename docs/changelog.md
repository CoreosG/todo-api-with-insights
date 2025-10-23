   # Changelog

   All notable changes to this project will be documented in this file.

   The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
   and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

   ## [Unreleased]

   ### Added
   - ADR-004: API Framework Selection (FastAPI for serverless integration with Repository pattern implementation).
   - ADR-005: ETL Method (Hybrid Lambda/Glue pipeline for data lake).
   - ADR-006: Monitoring and Observability (CloudWatch for API/ETL metrics and dashboard).
   - ADR-007: IaC Tool Selection (AWS CDK for Python-native infrastructure automation).
   - Custom metrics Lambda function with real-time DynamoDB data calculation.
   - Comprehensive CloudWatch dashboard with API health, Lambda performance, and business metrics widgets.
   - ETL test scripts for generating sample data and testing the complete pipeline.
   - Infrastructure as Code with proper resource cleanup (auto_delete_objects for S3 buckets).

   ### Changed
   - Updated System_architecture.md Mermaid diagram to include CloudWatch Metrics integration for ETL observability (added arrows from Glue Catalog and Athena to CloudWatch for better alignment with ADR-006).
   - Enhanced System_architecture.md with additional metrics links: Firehose, DynamoDB, Streams, Lambda Sync to CloudWatch Metrics for complete API and ETL observability.
   - Simplified architecture by removing SQS queue and consolidating to single Lambda handler across all ADRs (000, 004, 005, 006, 007).
   - Refined ADR prompts in `.cursor/prompts/` for better AI-assisted documentation.
   - Enhanced ADR-004 with comprehensive Repository pattern implementation details, including 5-layer architecture (Entrypoint → Controller → Service → Repository → Database) and Lambda Layers for code sharing across Lambda functions.
   - Updated README.md project structure to reflect actual file organization and added specific file names.
   - Updated all repository references to use correct GitHub URL: https://github.com/CoreosG/todo-api-with-insights.
   - Enhanced custom metrics Lambda to calculate real data from DynamoDB instead of using assumptions.
   - Improved CloudWatch dashboard widgets with correct resource dimensions and metric names.

   ### Fixed
   - Fixed CloudWatch dashboard API Health Overview widget by correcting API Gateway dimensions from `ApiName` to `ApiId`.
   - Fixed CloudWatch dashboard Lambda Performance widget by ensuring correct function name dimensions.
   - Fixed custom metrics Lambda namespace configuration to prevent SchemaValidationError.
   - Fixed Glue job argument passing by adding required `--BRONZE_BUCKET`, `--SILVER_BUCKET`, and `--DATABASE_NAME` parameters.
   - Fixed CDC Lambda metrics namespace configuration for proper CloudWatch integration.
   - Fixed S3 bucket deletion by adding `auto_delete_objects=True` to ensure complete cleanup on stack destruction.
   - Fixed custom metrics Lambda dependencies by creating proper `requirements.txt` with `boto3`, `aws-lambda-powertools`, and `aws-xray-sdk`.

   ### Deprecated
   - None yet.

   ### Removed
   - None yet.

   ### Security
   - None yet.

   ## [1.0.0] - 2025-10-15
   - Initial project setup with ADRs 000-007 completed.
   - Architecture diagram established.
   - Repository pattern implementation details added to ADR-004.

   ---

   For older changes, see git history or release notes.
   ```

### 3. **How to Maintain It**
   - **Updates**: Add to "Unreleased" for ongoing changes. When releasing, move to a versioned section (e.g., ## [1.1.0]).
   - **Ties to Commits**: Link to conventional commit messages (e.g., `docs(adr): add ADR-006 monitoring`).
   - **Expansion**: As you add more (e.g., API code or IaC), categorize accordingly.

   This gives you a solid starting point—feel free to tweak based on your exact changes! If you need more entries or help with future updates, let me know.