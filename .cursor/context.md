# Todo API with Insights - Project Context

## Overview
This is a **production-minded To-Do REST API** with a **data lake pipeline** built using Python and AWS serverless services. The project demonstrates architectural decision-making, best practices, and comprehensive documentation through Architecture Decision Records (ADRs).

## Architecture (ADR-000)
- **Serverless-first architecture** using AWS managed services
- **API Gateway + Cognito** for authentication and REST endpoints
- **Lambda functions** for API handlers (sync/async/CDC processing)
- **DynamoDB** for persistence with single-table design
- **S3 + Glue + Athena** for data lake and analytics
- **CloudWatch** for monitoring, logging, and alerting
- **AWS CDK** for Infrastructure as Code

## Technology Stack

### API Layer (ADR-004)
- **FastAPI** with automatic OpenAPI 3.0 documentation
- **5-layer architecture**: Entrypoint → Controller → Service → Repository → Database
- **Repository pattern** for database abstraction and testability
- **Pydantic** for input validation and serialization
- **Mangum** ASGI adapter for Lambda deployment
- **Lambda Layers** for shared code across functions

### Database Layer (ADR-001, ADR-002, ADR-003)
- **DynamoDB** with On-Demand capacity mode
- **Single-table design** with user-scoped partition keys (`USER#{user_id}`)
- **Global Secondary Indexes** for efficient queries by status, due_date, priority, category
- **DynamoDB Streams** for real-time Change Data Capture (CDC)
- **Idempotency records** with TTL for duplicate request handling

### Data Lake & ETL (ADR-005)
- **Hybrid pipeline**: Lambda for real-time CDC, Glue for batch transformations
- **Firehose** for log buffering and Parquet conversion (60s intervals)
- **S3 Bronze layer**: Raw Parquet data partitioned by `year/month/day/user_id`
- **Glue Catalog/Crawler** for schema inference and table federation
- **S3 Silver layer**: Transformed data for aggregations
- **Athena** for serverless SQL analytics on Gold layer

### Observability (ADR-006)
- **Structured JSON logging** with request_id, user_id, component, operation
- **CloudWatch integration** for metrics, logs, and alarms
- **Comprehensive monitoring** of API (latency, errors) and ETL (job duration, throughput)
- **CloudWatch Dashboard** for unified health visualization

### Infrastructure (ADR-007)
- **AWS CDK (Python)** for single-command deployments (`cdk deploy --all`)
- **Multiple stacks**: ApiStack, DataStack, EtlStack, MonitoringStack
- **Resource tagging**: Project, Owner, Environment, CostCenter
- **Least-privilege IAM** policies with granular permissions
- **CDK bootstrap** and drift detection for environment management

## Project Structure
```
.
├── api/                 # FastAPI application code
│   ├── src/            # Source code (handlers, models, services)
│   └── tests/          # API tests
├── etl/                # ETL pipeline code
│   ├── src/           # Glue jobs and Lambda CDC handlers
│   └── tests/         # ETL tests
├── infra/             # AWS CDK infrastructure code
├── docs/              # Documentation
│   ├── adrs/          # Architecture Decision Records (000-007)
│   ├── diagrams/      # System architecture diagrams
│   └── changelog.md   # Project changelog
└── .cursor/           # AI collaboration files
    ├── prompts/       # Prompt history and templates
    ├── rules/         # Development rules and guidelines
    └── context.md     # This file - project context
```

## Key Constraints & Requirements
- **Serverless-first** for cost efficiency and scalability
- **Production-ready** with proper error handling and observability
- **Single-command deployment** via CDK
- **Comprehensive documentation** through ADRs
- **Type-safe** with Pydantic validation
- **Event-driven** ETL with real-time CDC
- **Schema evolution-friendly** data formats (Parquet)
- **Least-privilege security** with IAM policies

## Development Workflow
1. **Architecture decisions** documented in ADRs before implementation
2. **Incremental changes** (< 200 LOC) with conventional commits
3. **Code quality** enforced with ruff+black+mypy (`make lint`)
4. **Testing** for new endpoints and bug fixes (pytest)
5. **Documentation** updated for every change (changelog, ADRs)
6. **AI collaboration** with prompt tracking in `.cursor/prompts/`

## Current Status
- ✅ **ADRs 000-007** completed and documented
- ✅ **Architecture diagram** created with Mermaid
- ✅ **Navigation consistency** across all ADRs
- 🔄 **API implementation** pending (FastAPI with Repository pattern)
- 🔄 **ETL implementation** pending (Lambda CDC + Glue jobs)
- 🔄 **Infrastructure deployment** pending (CDK stacks)
- 🔄 **Monitoring setup** pending (CloudWatch dashboard)

## Success Criteria
- ✅ Working CRUD API for Users and Tasks with authentication
- ✅ Real-time ETL pipeline landing data in S3
- ✅ Athena queries enabled on processed data
- ✅ CloudWatch dashboard showing API and ETL health
- ✅ Single-command CDK deployment
- ✅ Complete documentation with ADRs and diagrams

## Evaluation Focus (100 pts)
- Architecture rationale (ADRs, diagrams): 25 pts
- API design & correctness: 20 pts
- Data modeling & persistence: 15 pts
- ETL / Athena integration: 15 pts
- Observability (metrics, dashboards): 10 pts
- IaC completeness: 10 pts
- Documentation & readability: 5 pts

This context provides AI assistants with comprehensive understanding of the project's architecture, constraints, and current state for effective collaboration.
