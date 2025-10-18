# ADR-005: ETL Method Selection

**Date:** 2025-10-15
**Status:** Accepted

## Context and Problem Statement

The system requires a lightweight ETL pipeline that extracts task-level data and writes insights to Amazon S3 for Athena queries, as specified in ADR-000. The pipeline must handle two data sources: CloudWatch logs (from API Gateway, Lambda) and DynamoDB Streams (processed by Lambda CDC). Both sources feed into Firehose for ingestion to S3 Bronze (raw, partitioned Parquet data), followed by Glue Catalog/Crawler for S3 Silver (transformed via Glue Jobs for aggregations), and Athena queries producing S3 Gold (optimized for analytics). The chosen method must ensure event-driven, cost-effective processing that integrates with the single-table data model from ADR-003 and API from ADR-004, while maintaining simplicity, idempotency, and serverless alignment per ADR-000.

## Decision Drivers

* **Event-Driven Architecture**: Must support real-time data freshness through triggers from DynamoDB Streams and CloudWatch subscriptions
* **Serverless Cost Optimization**: Pipeline components must scale to zero when idle and pay only for actual processing
* **Data Lake Integration**: Must handle both log aggregation and CDC events to create partitioned, queryable datasets
* **Operational Simplicity**: Minimize custom code and leverage managed AWS services for transformations and cataloging
* **Idempotency & Reliability**: Ensure safe retries and failure handling (DLQ patterns) for production reliability
* **Schema Evolution Support**: Handle the single-table DynamoDB design with flexible Parquet partitioning

## Considered Options

* **Option A: Lambda-Centric Pipeline** - Use Lambda for all processing (CDC, Firehose ingestion, basic transformations)
* **Option B: Glue-Centric Pipeline** - Use Glue Jobs for transformations with Lambda for lightweight CDC processing
* **Option C: Hybrid Pipeline** - Lambda for real-time CDC/Firehose ingestion, Glue for batch aggregations

## Decision Outcome

**Chosen option:** "Hybrid Pipeline"

### Rationale

The hybrid approach optimally balances real-time processing requirements with cost-effective batch transformations. Lambda handles low-latency CDC events and Firehose delivery, while Glue provides powerful Spark-based aggregations for the Silver layer, ensuring both responsiveness and analytical depth.

### Positive Consequences

* ✅ **Real-Time Freshness**: Lambda CDC enables immediate processing of DynamoDB changes for up-to-date insights
* ✅ **Near-Real-Time Processing**: Sub-second CDC via Lambda aligns with ADR-000's freshness requirements, ensuring task insights are available within minutes
* ✅ **Cost Optimization**: Event-driven Lambda scales to zero; Glue Jobs run only when needed for aggregations
* ✅ **Processing Power**: Glue Spark jobs efficiently handle complex transformations at scale
* ✅ **Operational Simplicity**: Managed services reduce custom code while maintaining reliability
* ✅ **Analytical Capability**: Athena queries on optimized Gold data support complex task analytics

### Negative Consequences

* ❌ **Architectural Complexity**: Requires coordination between Lambda and Glue components
* ❌ **Cold Start Latency**: Glue Jobs have 10-minute cold starts (mitigated by EventBridge scheduling)
* ⚠️ **Vendor Lock-in**: Deep integration with AWS managed services (acceptable for test scenario per ADR-000)

## Detailed Analysis

### Option A: Lambda-Centric Pipeline

**Pros:**
- P1. **Ultra-Low Latency**: Sub-second processing for CDC events and immediate Firehose delivery
- P2. **True Serverless**: Pay-per-invocation model with automatic scaling to zero
- P3. **Unified Runtime**: Single Python runtime across all pipeline stages simplifies development

**Cons:**
- C1. **Memory/Timeout Limits**: 15-minute timeout and 10GB memory limit restrict complex aggregations
- C2. **Cost Inefficiency**: Repeated Lambda invocations for large datasets become expensive
- C3. **Limited Transformation Power**: Lacks distributed processing capabilities for complex analytics

**Evaluation:** **3/5 - Good for simple pipelines**. Excels at real-time ingestion but falls short for complex analytical transformations required for task insights.

### Option B: Glue-Centric Pipeline

**Pros:**
- P1. **Powerful Transformations**: Spark-based processing handles complex aggregations efficiently
- P2. **Scalable Batch Processing**: Auto-scales workers for large datasets with 48-hour runtime limit
- P3. **Built-in Optimization**: Native partitioning and compression optimizations for Athena queries

**Cons:**
- C1. **Latency Trade-offs**: 10-minute cold starts and batch-oriented processing delay real-time insights
- C2. **Higher Operational Cost**: DPU-hour billing even for small jobs (minimum 0.25 DPU)
- C3. **Scheduling Complexity**: Requires EventBridge for orchestration vs. event-driven triggers

**Evaluation:** **3/5 - Good for batch analytics**. Excellent for complex transformations but introduces latency that conflicts with real-time requirements.

### Option C: Hybrid Pipeline (Chosen)

**Pros:**
- P1. **Best of Both Worlds**: Real-time Lambda processing combined with powerful Glue transformations
- P2. **Event-Driven Efficiency**: DynamoDB Streams trigger immediate CDC processing
- P3. **Optimized Cost Structure**: Lambda for variable loads, Glue for compute-intensive batch jobs
- P4. **Production Reliability**: DLQ patterns and idempotent processing across both components

**Cons:**
- C1. **Integration Complexity**: Requires coordination between Lambda and Glue workflows
- C2. **Skill Set Requirements**: Team needs expertise in both Lambda and Glue development patterns

**Evaluation:** **5/5 - Optimal Fit**. Provides the real-time responsiveness needed for task insights while maintaining cost-effective batch processing for complex analytics.

## Pipeline Architecture Details

### Data Flow Stages

**Bronze Layer (Raw Data Ingestion):**
- **Firehose Integration**: Buffers logs/CDC events (60s intervals), converts JSON→Parquet, partitions by event_date (mapped from task created_at from ADR-003) and user_id to enable efficient, user-scoped Athena queries
- **Cost**: $0.029/GB ingested with idempotent delivery via record IDs
- **Partitioning**: S3 paths use YYYY/MM/DD/user_id structure for efficient Athena pruning

**Silver Layer (Transformed Data):**
- **Glue Catalog/Crawler**: Auto-infers schemas daily ($0.03/run), enables table federation
- **Glue Jobs**: Spark ETL for aggregations (tasks_per_user_daily), incremental processing via date filters
- **Cost**: $0.44/DPU-hour (2 DPU, 15min = $0.22/run) with idempotent S3 prefix handling

**Gold Layer (Analytics Optimized):**
- **Athena Integration**: Serverless SQL queries on Silver data with CTAS to Gold for BI extracts
- **Cost**: $5/TB scanned (partitioning reduces 90%), idempotent overwrites for fresh extracts

### Event-Driven Triggers

**DynamoDB Streams → Lambda CDC:**
- Triggers on INSERT/UPDATE/DELETE operations from single-table design (ADR-003)
- Batches 100 records per invocation for Firehose efficiency
- DLQ for failed processing with exponential backoff retry logic

**CloudWatch Logs → Firehose:**
- Subscription filters capture API Gateway and Lambda execution logs
- Structured JSON format with request_id and user_id for correlation
- Automatic S3 delivery with SSE-KMS encryption

### Limitations and Mitigations

**Firehose Constraints:**
- 1000 KiB record limit, 500 records/4MiB per batch, 24h retention on failure
- Mitigation: Batch records in Lambda CDC, implement circuit breaker for S3 failures

**S3 Bronze Limits:**
- 5000 PUTs/second bucket limit, no real-time queries (Athena lag 5-10min)
- Mitigation: Partitioning strategy reduces query scope, lifecycle policies manage storage costs

**Glue Processing Limits:**
- 1h minimum crawl interval, 1000 concurrent jobs/account limit
- Mitigation: Scheduled crawlers for schema updates, EventBridge for job orchestration

**Athena Query Limits:**
- 30min timeout, $5/TB scanned without partitioning
- Mitigation: Comprehensive partitioning strategy, query optimization with partition pruning

## Validation Approach

1. **Load Testing**: Validate pipeline performance under expected task creation/update volumes
2. **End-to-End Testing**: Verify data flows from DynamoDB Streams through all layers to Athena queries
3. **Cost Monitoring**: Track Firehose ingestion, Glue DPU-hours, and Athena scan volumes
4. **Error Scenario Testing**: Simulate S3 failures, Lambda timeouts, and Glue job failures with recovery validation
5. **Schema Evolution Testing**: Verify handling of new task attributes in single-table design

## Links

* [Related ADR-000: Architecture Overview](000-architecture-overview.md)
* [Related ADR-001: Database Selection](001-database-selection.md)
* [Related ADR-003: Data Modeling Approach](003-data-modeling-approach.md)
* [Related ADR-002: Database Capacity Mode Selection](002-database-capacity-mode-selection.md)
* [AWS Firehose Documentation](https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html)
* [AWS Glue Documentation](https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html)
* [AWS Athena Documentation](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)

## References

* [AWS Data Lake Best Practices](https://docs.aws.amazon.com/whitepapers/latest/building-data-lakes/building-data-lakes.html)
* [DynamoDB Streams CDC Patterns](https://aws.amazon.com/blogs/database/amazon-dynamodb-streams-use-cases-and-design-patterns/)
* [Event-Driven Architecture Patterns](https://docs.aws.amazon.com/whitepapers/latest/event-driven-architecture/welcome.html)
