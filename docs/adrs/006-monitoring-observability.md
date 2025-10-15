# ADR-006: Monitoring and Observability Strategy

**Date:** 2025-10-15
**Status:** Accepted

## Context and Problem Statement

The system requires comprehensive monitoring and observability for both the To-Do API (built with FastAPI per ADR-004) and the ETL pipeline (hybrid Lambda/Glue approach per ADR-005) to ensure production reliability and meet ADR-000's requirement for CloudWatch-based monitoring with at least one dashboard. The solution must provide real-time insights into API health (latency, error rates) and ETL performance (job duration, data ingestion) while maintaining cost optimization through minimal, meaningful metrics that align with the serverless-first architecture.

## Decision Drivers

* **Serverless Integration**: Must leverage CloudWatch's native integration with AWS services (API Gateway, Lambda, Firehose, Glue)
* **Real-Time Visibility**: Need immediate insights into API performance and ETL pipeline health for proactive issue detection
* **Cost Optimization**: Focus on essential metrics to stay within CloudWatch free tiers while providing actionable observability
* **Production Reliability**: Implement alarms and structured logging to enable rapid troubleshooting and maintain service health
* **API/ETL Correlation**: Must track request flows across components (API Gateway → Lambda → DynamoDB → ETL pipeline)
* **Evaluation Alignment**: Support the 10-point observability criterion with meaningful metrics and visualization

## Considered Options

* **Option A: CloudWatch Native** - Use built-in CloudWatch features with custom metrics and dashboards
* **Option B: Third-Party SaaS** - External monitoring services (DataDog, New Relic) for enhanced visualization
* **Option C: Minimal Monitoring** - Basic CloudWatch integration with reduced custom metrics

## Decision Outcome

**Chosen option:** "CloudWatch Native"

### Rationale

CloudWatch provides seamless integration with all AWS services in the architecture, enabling comprehensive observability without vendor lock-in beyond AWS. The native approach supports real-time monitoring, structured logging, and cost-effective alerting while maintaining alignment with the serverless-first principles from ADR-000.

### Positive Consequences

* ✅ **Native AWS Integration**: Seamless connectivity with API Gateway, Lambda, DynamoDB, Glue, and Firehose metrics
* ✅ **Real-Time Monitoring**: Sub-minute granularity for API latency and ETL performance tracking
* ✅ **Cost Efficiency**: Leverages CloudWatch free tiers (1000+ metrics, 5GB logs) for essential observability
* ✅ **Structured Logging**: JSON-formatted logs with request_id and user_id correlation across components
* ✅ **Proactive Alerting**: Configurable alarms for immediate notification of performance degradation
* ✅ **Dashboard Visualization**: Unified view of API health and ETL pipeline performance in single pane

### Negative Consequences

* ❌ **Limited Advanced Analytics**: Fewer ML-based insights compared to specialized SaaS monitoring tools
* ❌ **AWS Dependency**: Vendor lock-in to AWS monitoring ecosystem (acceptable for serverless architecture)
* ⚠️ **Learning Curve**: Team requires familiarity with CloudWatch features and query language

## Detailed Analysis

### Option A: CloudWatch Native (Chosen)

**Pros:**
- P1. **Zero Integration Overhead**: Built-in metrics collection from all AWS services without additional agents
- P2. **Real-Time Correlation**: Native request tracing across API Gateway, Lambda, and downstream services
- P3. **Cost-Effective Scaling**: Pay-per-use model with generous free tiers for startup workloads
- P4. **Unified Dashboard**: Single platform for metrics, logs, and alarms across entire architecture

**Cons:**
- C1. **Query Language Complexity**: CloudWatch Insights requires learning for complex log analysis
- C2. **Limited Third-Party Integrations**: Fewer pre-built integrations compared to SaaS alternatives

**Evaluation:** **5/5 - Optimal Fit**. Provides comprehensive observability for serverless architecture while maintaining cost efficiency and operational simplicity.

### Option B: Third-Party SaaS

**Pros:**
- P1. **Advanced Visualization**: Rich dashboards with ML-powered anomaly detection and alerting
- P2. **Multi-Cloud Support**: Unified monitoring across AWS and potential future cloud providers
- P3. **Extensive Integrations**: Pre-built connectors for various services and external tools

**Cons:**
- C1. **Additional Cost**: Monthly subscription fees regardless of actual usage volume
- C2. **Integration Complexity**: Requires agents, exporters, or API integrations for AWS services
- C3. **Data Export Requirements**: Must configure data pipelines to external monitoring platforms

**Evaluation:** **2/5 - Poor Fit**. Introduces unnecessary complexity and cost for a serverless AWS-native architecture where CloudWatch provides sufficient capabilities.

### Option C: Minimal Monitoring

**Pros:**
- P1. **Maximum Cost Savings**: Minimal CloudWatch usage stays well within free tiers
- P2. **Reduced Complexity**: Fewer metrics and alerts to configure and maintain

**Cons:**
- C1. **Insufficient Visibility**: Lacks depth for troubleshooting complex distributed system issues
- C2. **Reactive-Only Approach**: No proactive alerting for performance degradation detection
- C3. **Evaluation Gap**: Fails to meet the 10-point observability criterion requirements

**Evaluation:** **1/5 - Insufficient**. While cost-effective, provides inadequate visibility for production system reliability and troubleshooting needs.

## Monitoring Architecture Implementation

### Metrics Collection Strategy

**API Layer Metrics (from ADR-004):**
- **API Gateway Metrics**: Request count, latency (P50, P95, P99), error rate, 4XX/5XX responses
- **Lambda Function Metrics**: Invocation count, duration, error count, cold start rate, concurrent executions
- **Custom Business Metrics**: Tasks created/updated/deleted per user, authentication success/failure rates

**ETL Pipeline Metrics (from ADR-005):**
- **Firehose Metrics**: Incoming records/bytes, delivery success/failure rates, age of oldest record
- **Glue Job Metrics**: Job run duration, DPU consumption, success/failure rates, input/output record counts
- **Athena Query Metrics**: Query execution time, data scanned, query result size, concurrent query limits

**Database Metrics (from ADR-001/ADR-003):**
- **DynamoDB Metrics**: Read/write capacity usage, throttling events, item count, table size
- **CDC Processing Metrics**: Stream record age, Lambda processing lag, batch size distribution

### Structured Logging Implementation

**Log Format Standardization:**
```json
{
  "timestamp": "2025-10-15T10:30:45.123Z",
  "level": "INFO",
  "request_id": "abc-123-def-456",
  "user_id": "user-789",
  "component": "api-gateway|lambda-sync|lambda-async|lambda-cdc",
  "operation": "create-task|update-task|query-tasks|process-cdc",
  "duration_ms": 150,
  "status": "success|error",
  "message": "Task created successfully",
  "metadata": {
    "task_id": "task-123",
    "table_name": "todo-app-data",
    "partition_key": "TASK#user-789",
    "sort_key": "TASK#task-123"
  }
}
```

**Log Destinations:**
- **CloudWatch Logs Groups**: Separate groups per component (api-gateway, lambda-functions, glue-jobs)
- **Log Retention**: 30 days for active logs.
- **Subscription Filters**: Forward structured logs to Firehose for S3 archival and Athena analysis

### Alarm Configuration Strategy - Responses won't be implemented

**Critical Alarms (Immediate Response Required):**
- **API Error Rate**: >5% 4XX/5XX responses over 5-minute period
- **Lambda Timeout**: Any function timeout events
- **DynamoDB Throttling**: >1% throttled requests over 5-minute period
- **ETL Pipeline Failure**: Glue job failures or Lambda CDC processing errors

**Warning Alarms (Performance Monitoring):**
- **API Latency**: P99 latency >1000ms for 10-minute period
- **Firehose Delivery Lag**: Record age >300 seconds
- **Glue Job Duration**: Job runtime >2x average duration
- **Athena Query Cost**: Daily scan volume >1GB threshold

**Alarm Actions:**
- **SNS Notifications**: Email/SMS alerts to on-call rotation
- **Slack Integration**: Real-time notifications for immediate team awareness
- **PagerDuty Integration**: Escalation for critical system issues

### Dashboard Design

**Primary Dashboard: "To-Do API & ETL Health Overview"**

**API Health Widgets:**
- **Request Volume**: Line chart showing requests per minute over last 24 hours
- **Error Rate Trend**: Area chart displaying 4XX/5XX error rates with 5% threshold line
- **Latency Distribution**: Heatmap showing P50/P95/P99 latency percentiles
- **Top Error Types**: Bar chart of most common HTTP error codes

**ETL Pipeline Widgets:**
- **Data Ingestion Rate**: Line chart of records processed per hour by component
- **Pipeline Latency**: Number widgets showing end-to-end processing time
- **Job Success Rate**: Pie chart of Glue job success/failure distribution
- **Storage Growth**: Area chart tracking S3 Bronze/Silver/Gold data volumes

**System Health Widgets:**
- **Active Alarms**: Status indicator showing current alarm states
- **Resource Utilization**: CPU/memory metrics for Lambda functions
- **Cost Tracking**: Daily CloudWatch and Athena usage costs

**Dashboard Configuration:**
- **Refresh Rate**: Auto-refresh every 60 seconds for real-time visibility
- **Time Range**: Default 24-hour view with customizable ranges
- **Export Capability**: PDF reports for stakeholder reviews

### Cost Optimization Strategies

**CloudWatch Cost Management:**
- **Metric Selection**: Focus on 20-30 essential custom metrics vs. hundreds of granular ones
- **Log Sampling**: Implement intelligent sampling for high-volume logs during normal operation
- **Retention Policies**: 30-day retention for operational logs
- **Free Tier Utilization**: Prioritize built-in metrics over custom ones where possible

**Monitoring Cost Tracking:**
- **Budget Alarms**: CloudWatch billing alarms for monthly spend thresholds
- **Usage Dashboards**: Visibility into metric/log ingestion volumes and associated costs


## Integration with Architecture Components

### API Gateway Integration (ADR-004)
- Enable detailed request/response logging with sampling
- Configure custom access logging to CloudWatch for enhanced analytics
- Set up method-level metrics for endpoint performance tracking

### Lambda Functions Integration (ADR-004/ADR-005)
- Implement structured logging with correlation IDs across sync/async/CDC functions
- Track cold start metrics and memory utilization for performance optimization
- Monitor concurrent execution limits and timeout events

### ETL Pipeline Integration (ADR-005)
- Monitor Firehose delivery streams for throughput and error rates
- Track Glue job execution metrics and DPU consumption patterns
- Monitor Athena query performance and scan volume costs

### Database Integration (ADR-001/ADR-003)
- Monitor DynamoDB read/write capacity utilization and throttling events
- Track table-level metrics for the single-table design performance
- Monitor DynamoDB Streams processing lag for CDC pipeline health

## Validation Approach

1. **Load Testing**: Validate alarm thresholds under expected production traffic patterns
2. **End-to-End Tracing**: Verify request correlation across all architecture components
3. **Cost Impact Assessment**: Monitor CloudWatch usage and costs during initial deployment
4. **Alert Validation**: Test alarm notification workflows and escalation procedures
5. **Dashboard Usability**: Gather feedback on dashboard effectiveness for operational tasks
6. **Performance Benchmarking**: Establish baseline metrics for ongoing optimization

## Links

* [Related ADR-000: Architecture Overview](000-architecture-overview.md)
* [Related ADR-001: Database Selection](001-database-selection.md)
* [Related ADR-002: Database Capacity Mode Selection](002-database-capacity-mode-selection.md)
* [Related ADR-003: Data Modeling Approach](003-data-modeling-approach.md)
* [Related ADR-005: ETL Method](005-etl-method.md)
* [AWS CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
* [CloudWatch Dashboard Best Practices](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)
* [Structured Logging Patterns](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchlogs.html)

## References

* [AWS Well-Architected Observability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/observability-best-practices/)
* [Serverless Monitoring Patterns](https://aws.amazon.com/blogs/architecture/monitoring-serverless-applications/)
* [CloudWatch Cost Optimization](https://aws.amazon.com/blogs/mt/cloudwatch-cost-optimization/)
