# ADR-004: API Framework Selection

**Date:** 2025-10-15
**Status:** Accepted

## Context and Problem Statement

The system requires a Python REST API framework that supports CRUD operations for Users and Tasks with authentication, input validation, and automatic OpenAPI documentation. The framework must integrate seamlessly with the DynamoDB single-table design from ADR-003, align with the serverless-first architecture from ADR-000, and support the complex access patterns defined for user-scoped queries (status, due date, priority, category).

## Decision Drivers

* **Automatic Documentation**: Must generate OpenAPI/Swagger documentation automatically from code
* **Input Validation**: Need robust, type-safe request/response validation at API boundaries
* **Serverless Compatibility**: Must work efficiently with AWS Lambda and API Gateway
* **DynamoDB Integration**: Should support async patterns for efficient database operations
* **Type Safety**: Must provide compile-time type checking and validation
* **Testing Support**: Need built-in testing utilities for API endpoints

## Considered Options

* **Option A: FastAPI** - Modern, async-first web framework with automatic OpenAPI generation
* **Option B: Flask** - Traditional synchronous web framework with manual OpenAPI integration

## Decision Outcome

**Chosen option:** "FastAPI"

### Rationale

FastAPI provides native OpenAPI 3.0 documentation generation, Pydantic-based validation, and async support that aligns perfectly with the serverless architecture and DynamoDB integration requirements. The framework's design supports the user-scoped access patterns from ADR-003 through efficient async database operations.

### Positive Consequences

* ✅ **Automatic OpenAPI Generation**: Generates comprehensive API documentation directly from Python type hints and docstrings
* ✅ **Type-Safe Validation**: Pydantic integration ensures runtime validation and serialization for all API boundaries
* ✅ **Async-First Design**: Native async/await support enables efficient concurrent DynamoDB operations
* ✅ **Built-in Security**: Native support for JWT Bearer tokens and OAuth2 integration with Cognito
* ✅ **Performance**: ASGI-based with Uvicorn provides high throughput suitable for serverless deployment
* ✅ **Testing Integration**: TestClient and pytest-asyncio support for comprehensive API testing

### Negative Consequences

* ❌ **Smaller Ecosystem**: Fewer third-party extensions compared to Flask (mitigated by framework quality and extensibility)
* ❌ **Learning Curve**: Team members unfamiliar with async Python or Pydantic need initial ramp-up time
* ⚠️ **Async Complexity**: Requires careful handling of blocking operations (mitigation: use dependency injection for sync services)

## Detailed Analysis

### Option A: FastAPI (Chosen)

**Pros:**
- **Automatic Documentation**: Generates OpenAPI 3.0 schema and interactive Swagger UI from function signatures and Pydantic models
- **Validation Integration**: Deep Pydantic v2 integration for request/response validation, serialization, and custom validators
- **Security Support**: Built-in OAuth2, JWT Bearer, and API key authentication schemes compatible with Cognito
- **Async Performance**: Native async/await support with ASGI for concurrent request handling and database operations
- **Type Safety**: Full type hint support with mypy compatibility for compile-time error detection
- **DynamoDB Integration**: Async boto3 client compatibility for efficient database operations

**Cons:**
- **Relative Newness**: Released in 2018, though production-proven at scale (Netflix, Uber, Microsoft)
- **Async Paradigm**: Requires understanding async/await patterns and careful dependency management
- **Lambda Adapters**: Requires Mangum ASGI adapter for AWS Lambda deployment

**Evaluation:** **5/5 - Optimal Fit**. Provides all required features with modern async architecture that aligns with serverless patterns and DynamoDB's event-driven capabilities.

### Option B: Flask

**Pros:**
- **Mature Ecosystem**: Large number of extensions and community packages available
- **Familiarity**: Synchronous request-response model familiar to most Python developers
- **Flexibility**: Highly customizable and extensible architecture

**Cons:**
- **Manual Documentation**: Requires additional libraries (Flask-RESTX, APISpec) for OpenAPI generation
- **Validation Overhead**: No built-in validation framework; requires manual implementation or third-party libraries
- **Sync-Only Design**: Synchronous architecture less efficient for concurrent operations and database connections
- **Security Integration**: Requires additional setup for JWT/Cognito integration without native support
- **Type Safety**: Limited type hint support without additional tooling

**Evaluation:** **2/5 - Poor Fit**. While mature and flexible, Flask lacks the automatic documentation and validation features required, and its synchronous design conflicts with the async-first serverless architecture.

## Integration with Data Model (ADR-003)

The chosen FastAPI framework integrates seamlessly with the DynamoDB single-table design:

### API Endpoint Patterns
```python
# User-scoped queries leveraging GSI patterns from ADR-003
@app.get("/users/{user_id}/tasks")
async def get_user_tasks(
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None
) -> List[TaskResponse]:
    # Query GSI1 for status: GSI1PK = USER#{user_id}, GSI1SK begins_with STATUS#
    # Query GSI3 for priority: GSI3PK = USER#{user_id}, GSI3SK begins_with PRIORITY#
    # Query GSI4 for category: GSI4PK = USER#{user_id}, GSI4SK begins_with CATEGORY#
    pass

@app.get("/users/{user_id}/tasks/overdue")
async def get_overdue_tasks(user_id: str) -> List[TaskResponse]:
    # Query GSI2: GSI2PK = USER#{user_id}, GSI2SK < DUEDATE#{today}#
    pass
```

### Pydantic Models for Validation
```python
# Request/Response models aligned with ADR-003 schema
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[Priority] = Priority.medium
    category: Optional[str] = Field(None, max_length=50)
    due_date: Optional[date] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: Priority
    category: Optional[str]
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
```

## Links

* [Related ADR-000: Architecture Overview](000-architecture-overview.md)
* [Related ADR-001: Database Selection](001-database-selection.md)
* [Related ADR-003: Data Modeling Approach](003-data-modeling-approach.md)
* [FastAPI Documentation](https://fastapi.tiangolo.com/)
* [Pydantic Documentation](https://docs.pydantic.dev/)
* [Mangum ASGI Adapter](https://mangum.readthedocs.io/)