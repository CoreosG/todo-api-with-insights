## Prompt: 
@000-architecture-overview.md @001-database-selection.md 
Working now on ADR-003: Data Modeling Approach, help me decide between a Single-Table Approach or  multi table, for that we should decide:

Entities and relationships:
primary  entities: Users, Tasks, idempotency
Users (1) - Tasks (N)
Tasks (1) - idem (N)

Access patterns:
- Fetch user by user_id
- fetch all tasks  for user
- fetch tasks by status
- fetch tasks by due date
- continue...

PK/SK...

TTL

Objective:
get relevant information on NoSQL table structure, decide best practices, help with ADR writing.
Create schemas, check response and  improve on that.

## Subsequential prompts

prompt:
Idempotency entity missing Attributes, like response data and task_id, user_id.
identify more access patterns.

Objective:
Complete previous response, check  answer and complement manually what i know  is missing, previous prompt answer was rather vague.

prompt:
Validate ADR information using AWS MCP Server tool, point out wrong information, design faults and give implementation details.


Objective:
Since i don't know DynamoDB, i'll validate everything that was written, fix whatever is identified, get the implementation details and input it on  another LLM providing the ADR as context to confirm.
If everything is alright, i'll proceed.


## Validation Notes
- Cross-referenced AWS DynamoDB docs and single-table best practices to ensure query efficiency and GSI limits (max 20 GSIs per table).
- Manually reviewed for alignment with ADR-000's serverless principles and ETL needs; adjusted for user-scoped queries to avoid global scans.
- No major faults identified—design supports required access patterns without overcomplicating the schema.



Commit Link: