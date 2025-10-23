# Prompt 

Prompt:

create comprehensive cloudwatch monitoring and alerting solution with dashboard, alarms, and custom metrics. implement sns topic for email notifications. create custom metrics lambda to collect business kpis from dynamodb and publish to cloudwatch.

deploy monitoring stack with cdk deploy TodoMonitoringStack --require-approval never

fix any deployment errors and ensure all metrics are properly configured

create cloudwatch dashboard with multiple sections:
- API health overview (request counts, 4xx/5xx errors, latency)
- Lambda performance (duration, errors, throttles, invocations)  
- ETL pipeline health (firehose delivery, glue jobs)
- Database performance (dynamodb capacity, throttling)
- Business metrics (users, tasks, completion rates)
- Cost monitoring (estimated charges by service)

Follow @System_architecture.md and @adrs/

Objective:

Create comprehensive CloudWatch monitoring and alerting solution with:
- CloudWatch Dashboard with multiple sections for API, ETL, Database, and Business metrics
- CloudWatch Alarms for critical thresholds and cost monitoring
- Custom business metrics collection from DynamoDB

## Commit Link
23b7a1bc3ba9d958caebc3a30f763788b1e6d654 (same as infrastructure_updates, both went to the same commit)
