# Prompts

First prompt:
Proceed to ADR-006-monitoring-observability as recommended* .

*note: this had context from previous conversations, as seen on [deciding-next-ADR.md](/.cursor/prompts/deciding-next-ADR.md)

Objective: get the setup ADR prompt for ADR-006-monitoring-observability

Provided setup prompt (from A.I) - with manual tweaks:
```
## Prompt for ADR-006: Monitoring and Observability

**Objective:**  
Draft ADR-006: Monitoring and Observability, deciding how to implement CloudWatch-based monitoring for the To-Do API (from ADR-004) and ETL pipeline (from ADR-005), including metrics, logs, alarms, and a dashboard summarizing API health (e.g., latency, error rates) and ETL performance (e.g., job duration, data ingestion). Choose CloudWatch as the primary tool for serverless alignment per ADR-000, integrating with components like API Gateway, Lambda, Firehose. Ensure event-driven metrics for real-time insights, cost optimization, and ties to the architecture diagram (System_architecture.md). Focus on minimal, meaningful observability to support the 10-point criterion, building incrementally on prior ADRs.

**Context Files to Provide:**  
- @docs/adrs/000-architecture-overview.md (for monitoring requirements, CloudWatch emphasis, and observability principles). 
- @docs/adrs/004-api-framework.md (for API-specific metrics like endpoint latency and errors).  
- @docs/adrs/005-etl-method.md (for ETL metrics like Glue job duration, Firehose ingestion, and Athena scan costs).  
- @docs/diagrams/System_architecture.md (for component interactions to monitor).  
- @docs/adrs/template.md (for ADR structure).  

**Key Decisions to Make:**  
- Select CloudWatch features: Metrics for API/ETL performance, Logs for structured JSON, Alarms for thresholds (e.g., >5% errors), and Dashboard for visualization.  
- Integrate with prior ADRs: Metrics from Lambda (ADR-004), DynamoDB/Glue (ADR-005), and overall architecture (ADR-000).  
- Address trade-offs: Custom metrics vs. built-in (cost vs. depth), ensuring pay-per-use serverless monitoring.  

**Constraints:**  
- Align with ADR-000's serverless-first, cost-optimized approach (e.g., minimal metrics to avoid high CloudWatch costs).  
- Keep incremental: Focus on tool selection and setup rationale, not full implementation code.  
- Tie to evaluation (10 points for Observability).  
- Ensure structured logs (JSON with request_id/user_id) and dashboard widgets for API/ETL health.  

**Output Format:**  
- Generate the full ADR-006 content in Markdown, following template.md (Context, Drivers, Options, Outcome, etc.).  
- Include placeholders: [Your Rationale Here] for choices (e.g., why CloudWatch Dashboard over alternatives), [Validation Notes Here] for testing (e.g., simulate alarms).  
- Suggest a simple textual or pseudocode example for dashboard widgets if it enhances clarity.  
- After generation, I'll review and refine manually.  

**Validation Steps:**  
- Verify against ADR-000: Ensure dashboard covers API health and ETL performance as required.  
- Check integrations: Metrics from API Gateway/Lambda (ADR-004) and Glue/Athena (ADR-005).  
- Assess cost/scalability: Focus on essential metrics to stay under CloudWatch free tiers where possible.  

[Your Rationale Here]: 
CloudWatch: native integration for various AWS Resources (subscription filter to firehose), low-cost custom metrics, Dashboard integration.
To be honest: i don't know other options instead of this in a serverless aws achitecture, it just fits all.

[Service Limits to Monitor]:
CloudWatch Metrics: 1000 unique metrics/account free; custom: $0.30/500 metrics first 10k/mo
CloudWatch Logs: 5GB ingestion free/mo; $0.50/GB after; 1000 groups/account
Alarms: 10 free/account; $0.10/alarm/mo after; max 1000/account
Dashboards: 500 widgets/dashboard; 100 dashboards/account
Firehose: 5000 records/sec delivery; buffer 1-128MB, 60-900s interval
Lambda: 1000 concurrent executions; 15min timeout
```


commit link: dead4e91a8909e5b15673dc705e1fc593d1e0cf4