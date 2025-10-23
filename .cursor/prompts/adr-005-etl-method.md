## Prompts

First prompt: 
added @004-api-framework.md successfully.
now to ADR-005 ETL Method, review @System_architecture.md 
we'll have s3 bronze, silver, gold.
steps are in @000-architecture-overview.mdsystem architecture section.

generate a elaborate prompt to setup ADR-005.

*note: this prompt has context from previous prompts, on [other prompt file](/.cursor/prompts/deciding-next-ADR.md)

objective: 
get a elaborate prompt, run and review results. this time i'm expecting to have a lot  of gaps to fill in.


Provided setup prompt (from A.I) - with manual tweaks:
```
## Prompt for ADR-005: ETL Method

**Objective:**  
Draft ADR-005: ETL Method, deciding how to implement the data lake pipeline as clarified: CloudWatch logs (from API Gateway, Lambda Sync, Lambda Async) and DynamoDB Streams (processed by Lambda CDC) both feed into Firehose for ingestion to S3 Bronze (raw, partitioned Parquet data). From there, Glue Catalog/Crawler enables S3 Silver (transformed via Glue Jobs for aggregations), and Athena queries produce S3 Gold (optimized for analytics). Choose the method (e.g., Lambda for CDC/Firehose ingestion vs. Glue for batch processing) to ensure event-driven, cost-effective processing that integrates with the single-table data model from ADR-003 and API from ADR-004. Focus on simplicity, idempotency, and serverless alignment per ADR-000.

**Context Files to Provide:**  
- @docs/adrs/000-architecture-overview.md (for ETL requirements, S3 partitioning, and overall pipeline).  
- @docs/adrs/001-database-selection.md (for DynamoDB Streams and CDC).  
- @docs/adrs/003-data-modeling-approach.md (for data entities and events to process).  
- @docs/adrs/004-api-framework.md (for API-generated logs/data feeding the pipeline).  
- @docs/diagrams/System_architecture.md (for the diagram visualizing the Bronze/Silver/Gold flow).  
- @docs/adrs/template.md (for ADR structure).  

**Key Decisions to Make:**  
- Select tools for each stage: Firehose/Lambda for ingestion to S3 Bronze, Glue for Silver transformations, Athena for Gold queries.  
- Justify based on the pipeline: Event-driven triggers for real-time freshness, partitioning for query efficiency, and aggregations (e.g., tasks_per_user_daily).  
- Address trade-offs: Lambda for low-latency CDC vs. Glue for complex batch jobs.  

**Constraints:**  
- Align with serverless principles (pay-per-use, event-driven).  
- Ensure idempotency (safe retries) and error handling (e.g., DLQ for failed events).  
- Keep incremental: Focus on method rationale, referencing the clarified pipeline without full code.  
- Tie to evaluation (15 points for ETL/Athena).  

**Output Format:**  
- Generate the full ADR-005 content in Markdown, following template.md (Context, Drivers, Options, Outcome, etc.).  
- Include placeholders: [Your Rationale Here] for choices (e.g., Lambda for CDC), [Validation Notes Here] for testing (e.g., simulate Firehose delivery), [Commit Links Here].  
- Suggest a textual representation of the pipeline flow for clarity.  
- After generation, I'll review and refine manually.  

**Validation Steps:**  
- Verify against the pipeline: Ensure Firehose handles both log and CDC sources to S3 Bronze.  
- Check for cost/scalability (e.g., event-driven Lambda for variable loads).  

**[Your Rationale Here]:**  
Firehose: Buffers logs/CDC (60s intervals); converts JSON→Parquet; partitions by event_date/user_id; handles 5MiB/s throughput. Cost: $0.029/GB ingested. Idempotent via record IDs.  
S3 Bronze: Immutable raw storage; Parquet compression (70% savings); lifecycle to Glacier after 90d. Cost: $0.023/GB/month. Partitioned YYYY/MM/DD/user_id.  
Glue Catalog/Crawler: Auto-infers schemas daily; partitions discovery. Cost: $0.44/DPU-hour (0.25 DPU, 10min = $0.03/run). Enables queryability.  
Glue Jobs: Spark ETL for aggregations (tasks_per_user_daily); incremental via WHERE date >= last_run. Cost: $0.44/DPU-hour (2 DPU, 15min = $0.22/run). Idempotent via S3 prefixes.  
Athena: Serverless queries on Silver; CTAS to Gold for BI extracts. Cost: $5/TB scanned (partitioning cuts 90%). Overwrites Gold idempotently.  
Lambda CDC: Triggers on Streams; batches 100 records to Firehose. Cost: $0.20/1M requests. DLQ for failures.  

**[Limitations to Look For]:**  
Firehose: Record size 1000 KiB max; 500 records/4MiB per PutRecordBatch; 24h retention if S3 fails; 5000 streams/account limit (100 in some regions); 60-900s buffer only.  
S3 Bronze: 5000 PUTs/second bucket limit; 5TB object max; no real-time queries (Athena lag 5-10min).  
Glue Catalog/Crawler: 1h min crawl interval; schema drift requires manual fix; 1000 tables/account limit.  
Glue Jobs: 10min cold start; 48h max runtime; 1000 concurrent jobs/account; Spark 3.1 only (no Delta Lake).  
Athena: $5/TB scanned (unpartitioned kills budget); 30min query timeout; 1000 tables/database limit; no streaming ingest.  
Lambda CDC: 15min timeout; 10GB memory max; 1000 concurrent executions/account; DynamoDB Streams 24h retention.

```



commit link: 1ce9cf7edf8342a2856c008c4a21e07b433c26e4
(esse ja foi melhorzinho pois peguei algumas dicas de limitações dos serviços, eu só procurei por elas pois descobri que tem bastante coisa assim enquanto estudava pro SAA-C03)