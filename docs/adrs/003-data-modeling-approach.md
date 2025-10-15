# ADR-003: Data Modeling Approach

**Date:** 2025-10-14
**Status:** Accepted

## Context and Problem Statement

The system requires an efficient data modeling strategy for DynamoDB to support a To-Do API with complex access patterns while enabling effective Change Data Capture (CDC) for the data lake pipeline. The chosen approach must balance query performance, cost efficiency, and operational simplicity within the serverless-first architecture.

## Decision Drivers

* **Complex Access Patterns**: Need to support user-specific queries, status-based filtering, and date-based queries efficiently
* **CDC Integration**: Single DynamoDB Stream simplifies ETL pipeline architecture
* **Cost Optimization**: Minimize cross-table queries and leverage DynamoDB's efficiency for sparse access patterns
* **Scalability**: Support future access pattern evolution and handle varying load distributions
* **Operational Simplicity**: Minimize the number of tables to manage and monitor

## Considered Options

* **Option A: Single-Table Design** - All entities in one DynamoDB table with strategic partition keys and Global Secondary Indexes
* **Option B: Multi-Table Design** - Separate tables for Users, Tasks, and Idempotency with relationships via foreign keys

## Decision Outcome

**Chosen option:** "Single-Table Design"

### Rationale

The single-table approach optimally supports the complex access patterns while providing superior CDC efficiency and cost characteristics. The design leverages DynamoDB's strengths in handling sparse, hierarchical data through careful partition key design and Global Secondary Indexes.

### Schema Design

**Primary Table Structure:**

```typescript
// Base Table: todo-app-data
// Composite Keys: PK (Partition Key), SK (Sort Key)
// Global Secondary Indexes: GSI1 (Status), GSI2 (Due Date), GSI3 (Priority), GSI4 (Category)

// Users Entity
PK: USER#{user_id}
SK: METADATA
Attributes: email, name, created_at, updated_at

// Tasks Entity
PK: TASK#{user_id}
SK: TASK#{task_id}
Attributes: title, description, status, priority, category, due_date, created_at, updated_at, completed_at

// Idempotency Entity
PK: IDEMPOTENCY#{request_id}
SK: METADATA
Attributes: response_data, target_task_pk, target_task_sk, http_status_code, created_at
TTL: expiration_timestamp (Unix timestamp for automatic cleanup)
```

**Global Secondary Indexes:**

**GSI1 - User Tasks by Status:**
- GSI1PK: USER#{user_id} (for even load distribution across users)
- GSI1SK: STATUS#{status}#{task_id} (categorical attribute in sort key)

**GSI2 - User Tasks by Due Date:**
- GSI2PK: USER#{user_id} (for even load distribution across users)
- GSI2SK: DUEDATE#{due_date}#{task_id} (sortable date attribute in sort key)

**GSI3 - User Tasks by Priority:**
- GSI3PK: USER#{user_id} (for even load distribution across users)
- GSI3SK: PRIORITY#{priority}#{task_id} (categorical attribute in sort key)

**GSI4 - User Tasks by Category:**
- GSI4PK: USER#{user_id} (for even load distribution across users)
- GSI4SK: CATEGORY#{category}#{task_id} (categorical attribute in sort key)

**Note:** User-scoped design: All GSIs use USER#{user_id} as partition key for optimal load distribution and to enable user-specific queries. Categorical attributes (status, priority, category) and sortable attributes (due_date) are placed in sort keys to enable range queries and begins_with operations within each user's data. Global queries across all users require table scans and are not supported by these GSIs.

**Design Trade-offs:**
- ✅ **Optimal Load Distribution**: USER#{user_id} as GSI partition key ensures even distribution across DynamoDB partitions
- ✅ **User-Specific Queries**: All GSI queries are inherently scoped to a specific user, supporting multi-tenant access patterns
- ✅ **Range Query Support**: Sort keys enable efficient range queries for dates and begins_with for categorical attributes
- ❌ **No Global Queries**: Cannot efficiently query across all users for a specific attribute (e.g., "all pending tasks across all users") without table scans
- ❌ **GSI Proliferation**: Requires 4 GSIs to support all attribute-based queries within user scope

### Entity Attribute Definitions

**Users Attributes:**
- `email` (String): User's email address (unique identifier)
- `name` (String): User's display name
- `created_at` (Number): Unix timestamp of user creation
- `updated_at` (Number): Unix timestamp of last user update

**Tasks Attributes:**
- `title` (String): Task title/summary (required)
- `description` (String): Detailed task description (optional)
- `status` (String): Task status - "pending" | "in_progress" | "completed" | "cancelled"
- `priority` (String): Task priority - "low" | "medium" | "high" | "urgent" (optional)
- `category` (String): Task category/tag for organization (optional)
- `due_date` (String): Due date in YYYY-MM-DD format (optional)
- `created_at` (Number): Unix timestamp of task creation
- `updated_at` (Number): Unix timestamp of last task update
- `completed_at` (Number): Unix timestamp when task was completed (null if not completed)

**Idempotency Attributes:**
- `response_data` (String): JSON response body for duplicate request handling
- `target_task_pk` (String): The Task's Partition Key (TASK#{user_id})
- `target_task_sk` (String): The Task's Sort Key (TASK#{task_id})
- `http_status_code` (Number): HTTP status code of the original response
- `created_at` (Number): Unix timestamp of the idempotency record creation

### Access Pattern Implementation

| Access Pattern | Query Strategy | Efficiency | Cost |
|---|---|---|---|
| **Fetch user by user_id** | `PK = USER#{user_id}, SK = METADATA` | Single item lookup | 0.5 RCU |
| **Fetch task by task_id** | `PK = TASK#{user_id}, SK = TASK#{task_id}` | Single item lookup | 0.5 RCU |
| **Fetch all tasks for user** | `PK = TASK#{user_id}, SK begins_with TASK#` | Range query | ~1-5 RCU depending on result size |
| **Fetch tasks by status for user** | `GSI1PK = USER#{user_id}, GSI1SK begins_with STATUS#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch tasks by specific status for user** | `GSI1PK = USER#{user_id}, GSI1SK = STATUS#{status}#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch tasks by due date for user** | `GSI2PK = USER#{user_id}, GSI2SK begins_with DUEDATE#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch tasks by specific due date for user** | `GSI2PK = USER#{user_id}, GSI2SK = DUEDATE#{date}#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch tasks by date range for user** | `GSI2PK = USER#{user_id}, GSI2SK between DUEDATE#{start_date}# AND DUEDATE#{end_date}#` | Range query via GSI | ~1-5 RCU depending on range |
| **Pagination support** | Use `LastEvaluatedKey` and `Limit` parameters | Native DynamoDB feature | No additional cost |
| **Fetch tasks by priority for user** | `GSI3PK = USER#{user_id}, GSI3SK begins_with PRIORITY#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch tasks by specific priority for user** | `GSI3PK = USER#{user_id}, GSI3SK = PRIORITY#{priority}#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch tasks by category for user** | `GSI4PK = USER#{user_id}, GSI4SK begins_with CATEGORY#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch tasks by specific category for user** | `GSI4PK = USER#{user_id}, GSI4SK = CATEGORY#{category}#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Fetch completed tasks by user** | `PK = TASK#{user_id}, SK begins_with TASK#` + filter by `status = completed` | Range query + filter | ~1-5 RCU depending on result size |
| **Fetch overdue tasks for user** | `GSI2PK = USER#{user_id}, GSI2SK < DUEDATE#{today}#` + filter by `status != completed` | Range query + filter | ~1-5 RCU depending on range |
| **Fetch all tasks with due dates for user** | `GSI2PK = USER#{user_id}, GSI2SK begins_with DUEDATE#` | Range query via GSI | ~1-5 RCU depending on result size |
| **Task analytics: Count by status** | Scan with projection + aggregation | Full table scan | ~50-200 RCU for large datasets |
| **Task analytics: Count by priority** | Scan with projection + aggregation | Full table scan | ~50-200 RCU for large datasets |
| **Bulk update task status** | BatchWriteItem for multiple tasks | Batch operation | 1.5 WCU per item |
| **Bulk delete completed tasks** | BatchWriteItem with DeleteRequest | Batch operation | 0.5 WCU per item |
| **Search tasks by title/description** | Scan with filter expression | Full table scan | ~50-500 RCU depending on dataset size |
| **Create/Update task** | `PK = TASK#{user_id}, SK = TASK#{task_id}` | Single item write | 1 WCU |
| **Delete task** | DeleteItem operation | Single item delete | 0.5 WCU |
| **Idempotency check** | `PK = IDEMPOTENCY#{request_id}` | Single item lookup | 0.5 RCU |
| **Idempotency cleanup** | Automatic via TTL | No query needed | 0 RCU |

### Time To Live (TTL) Strategy

**Idempotency Records:**
- TTL attribute set to `created_at + 86400` (24-hour retention window)
- Automatic deletion by DynamoDB eliminates need for manual cleanup
- Supports API idempotency requirements while preventing unbounded growth

**Task Lifecycle Management:**
- No TTL on active tasks (business requirement for data retention)
- Optional: TTL on completed tasks older than N days for cost optimization
- Implementation: Add `ttl` attribute to task items when status changes to "completed"

## Query Implementation Considerations

### Efficient Query Patterns

**Primary Key Queries** (Most Efficient):
- Direct user lookup: `PK = USER#{user_id}`
- Direct task lookup: `PK = TASK#{user_id}, SK = TASK#{task_id}`
- User's tasks: `PK = TASK#{user_id}` (range query)

**GSI Queries** (Efficient for user-specific attributes):
- Status queries: `GSI1PK = USER#{user_id}, GSI1SK begins_with STATUS#`
- Specific status: `GSI1PK = USER#{user_id}, GSI1SK = STATUS#{status}#`
- Date queries: `GSI2PK = USER#{user_id}, GSI2SK begins_with DUEDATE#`
- Specific date: `GSI2PK = USER#{user_id}, GSI2SK = DUEDATE#{date}#`
- Date range: `GSI2PK = USER#{user_id}, GSI2SK between DUEDATE#{start}# AND DUEDATE#{end}#`
- Priority queries: `GSI3PK = USER#{user_id}, GSI3SK begins_with PRIORITY#`
- Category queries: `GSI4PK = USER#{user_id}, GSI4SK begins_with CATEGORY#`

**Scan Operations** (Least Efficient - Use Sparingly):
- Full-text search across titles/descriptions
- Complex analytics requiring aggregation across all items
- Consider Elasticsearch/OpenSearch for complex search requirements

### Performance Optimization

1. **Pagination**: Always implement pagination for queries that may return large result sets
2. **Projection**: Only request required attributes in query results to reduce data transfer
3. **Batch Operations**: Use BatchGetItem for multiple specific item lookups
4. **Conditional Writes**: Use condition expressions to prevent accidental overwrites

### Error Handling

- **Item Not Found**: Expected for get operations on non-existent items
- **Conditional Check Failed**: Handle race conditions in concurrent updates
- **Provisioned Throughput Exceeded**: Implement exponential backoff retry logic
- **Validation Errors**: Ensure data integrity at application layer before DynamoDB writes


### Single-Table vs Multi-Table Analysis

**Single-Table Design:**
- ✅ **CDC Efficiency**: Single DynamoDB Stream simplifies ETL pipeline
- ✅ **Query Performance**: Supports complex access patterns with low latency
- ✅ **Cost Optimization**: Minimizes cross-table joins and leverages sparse table efficiency
- ✅ **Scalability**: Even load distribution across partition keys
- ❌ **Design Complexity**: Requires careful GSI planning and access pattern analysis
- ❌ **Learning Curve**: Team needs to understand single-table design patterns

**Multi-Table Design:**
- ✅ **Simplicity**: Intuitive separation of concerns, easier to understand
- ✅ **Maintenance**: Each table can evolve independently
- ❌ **CDC Complexity**: Multiple streams require complex ETL coordination
- ❌ **Query Cost**: Cross-table queries increase RCU consumption
- ❌ **Access Patterns**: Less efficient for queries spanning multiple entities

## Positive Consequences

* ✅ **Optimal Query Performance**: All access patterns supported with single-digit millisecond latency
* ✅ **Simplified ETL Pipeline**: Single DynamoDB Stream enables straightforward CDC processing
* ✅ **Cost Efficiency**: Compound partition keys prevent hot spots while supporting efficient queries
* ✅ **Future-Proof Design**: GSI strategy supports access pattern evolution
* ✅ **Operational Simplicity**: Single table reduces monitoring and maintenance overhead

## Negative Consequences

* ❌ **Initial Complexity**: Design requires deeper understanding of DynamoDB patterns
* ❌ **Engineering Investment**: Higher upfront cost in schema design and testing
* ⚠️ **Risk Mitigation**: Implement comprehensive testing to validate all access patterns before deployment

## Validation Approach

1. **Load Testing**: Validate performance under expected user/task volumes
2. **Access Pattern Testing**: Ensure all documented patterns work efficiently
3. **CDC Integration Testing**: Verify stream processing handles all entity types correctly
4. **Cost Monitoring**: Track RCU/WCU consumption across different access patterns

## Links

* [Related ADR-000: Architecture Overview](000-architecture-overview.md)
* [Related ADR-001: Database Selection](001-database-selection.md)
* [Related ADR-002: API Framework](002-api-framework.md)

## References

* [DynamoDB Single-Table Design Best Practices](https://aws.amazon.com/blogs/database/amazon-dynamodb-single-table-design-using-dynamodb-partitions/)
* [AWS DynamoDB Documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.html)
* [DynamoDB Streams for CDC](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
