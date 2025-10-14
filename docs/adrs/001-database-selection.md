# ADR-001: Database Selection

**Date:** 2025-10-14 
**Status:** Accepted  


## Context and Problem Statement

The system requires a persistent data store for user and task data to support a Python REST API with basic CRUD operations. The solution must be highly scalable, cost-effective for a minimal application, and integrate well with the chosen Serverless-First AWS architecture and the event-driven Data Lake pipeline requirement.

## Decision Drivers

* Serverless-first architecture, event-driven
* Scalability, managed operations.
* Ease of implementation for event-driven ETL
* Costs of operation

## Considered Options

* Option A - DynamoDB (Managed NoSQL Key-Value Store)
* Option B - RDS PostgreSQL

## Decision Outcome

**Chosen option:** "DynamoDB"

### Rationale

* Native Event-Driven ETL: DynamoDB Streams provide a real-time Change Data Capture (CDC) mechanism, directly enabling the required event-driven ETL pipeline to the Data Lake with minimal custom code or tooling (Glue/Lambda trigger integration).

* Serverless and Scalable: As a fully managed NoSQL service, DynamoDB offers automatic, elastic scaling of throughput and storage. It aligns with the pay-per-request (On-Demand) serverless model, ensuring high performance without manual capacity management, satisfying the core architectural principle.

* Cost Efficiency for Sparse Data: DynamoDB's low-cost structure and highly optimized performance for key-value lookups are more cost-effective for the simple user/task data model compared to the provisioned costs of a relational database.


### Positive Consequences

* ✅ Real-Time Data Lake Feed: DynamoDB Streams enable near-instantaneous updates to the data lake, supporting a fresh view of task data for analysis.
* ✅ Zero Operational Overhead: AWS manages patching, scaling, and replication, minimizing the operational burden and maximizing developer focus on application code.
* ✅ High, Predictable Performance: Consistent single-digit millisecond latency is maintained at any scale, ensuring a fast, reliable API experience.

### Negative Consequences

* ❌ Complex Querying: Poor support for complex relational queries (joins, aggregations) or ad-hoc querying. Data access must be pre-planned and executed via primary/secondary keys.
* ❌ Data Modeling Complexity: Requires specialized Single-Table Design knowledge and schema planning to handle all access patterns efficiently.
* ⚠️  Risk 1 (Vendor Lock-in): Adopting DynamoDB Streams and key-value modeling creates high vendor lock-in. Mitigation: The application logic in the Python API will be kept lean, interacting with a repository pattern interface to minimize direct coupling to the DynamoDB SDK.

## Detailed Analysis

### Option A: DynamoDB
**Pros:**
- P1. Serverless Scaling/Cost: Automatic scaling (On-Demand) and pay-per-request model. Zero capacity management.

- P2. CDC/ETL Integration: DynamoDB Streams provide native, low-latency Change Data Capture for event-driven ETL.

- P3. High Availability: Built-in multi-AZ redundancy and automatic partitioning.

**Cons:**
- C1. Query Limitations: Limited to primary key and Global Secondary Index lookups; complex reporting requires offloading to the Data Lake (Athena).

- C2. Transactional Limits: Transactional consistency requires specific APIs (TransactWriteItems, TransactReadItems) which consume double capacity units.


**Evaluation:** 5/5 - Strong Fit. Highly aligns with Serverless, Cost, Scalability, and ETL requirements, despite the trade-off in query flexibility.

### Option B: RDS PostgreSQL
**Pros:**
- P1. ACID Compliance/Query Power: Full transactional integrity and powerful SQL capabilities suitable for complex ad-hoc queries and joins.
- P2. Familiarity

**Cons:**
- C1. Operational Cost/Overhead: Requires provisioned instance capacity (higher base cost). RDS Serverless V2 is still more expensive than DynamoDB on-demand for this workload type.
- C2. ETL Complexity: Event-driven CDC requires setting up external tooling which increases complexity and operational load, violating the simplicity principle.
- C3. Scaling Limit: Elasticity is slower and more limited than DynamoDB's native scaling model.


**Evaluation:** 2/5 - Poor Fit. While robust for querying, the operational cost, complexity of ETL integration, and slower scaling contradict the Serverless-First and Cost/Simplicity drivers.


## Links

* [Related ADR-002: Data Modeling Approach]
* [Related ADR-000: Architecture Overview]
