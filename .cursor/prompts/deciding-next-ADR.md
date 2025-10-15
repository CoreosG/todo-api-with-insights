# Prompts:

### ADR-004 - Api Framework
prompt:
    @docs/ - architecture overview done, database and data modeling done, use them as refference.
    Now i need to decide whether to make a ADR for api-framework or the stack as a whole. Since many things were decided on challenge context, such as linting, testing, authentication. Should i work on just the api-framework with the other frameworks as more refined detailed mentions, or do a detailed ADR for each step?

Objective:
    Understand more what is  the best practice given my current context, since i feel it's  overkill to do a separate ADR for each item in the stack decision.

## Subsequential prompts:
prompt: Given we're doing just one api-framework ADR mentioning technology stack as a comprehensive section within the document, generate a prompt for the agent to work on setting up the initial ADR given all my previous context.

objective:
get a elaborate prompt, run and review results

prompt:
```
 Prompt for ADR-004: API Framework

**Objective:**  
Draft ADR-004: API Framework, focusing on selecting and justifying a Python framework for the REST API that integrates with the DynamoDB data model from ADR-003. Use the existing partial draft in ADR-002 as a starting point. Ensure the ADR is incremental, concise (<150 lines), and builds bottom-up from the database layer. Reference pre-decided elements (e.g., Cognito for authentication, ruff+black+mypy for linting, pytest for testing) without creating separate ADRs for them. Decide on the framework (e.g., reaffirm FastAPI) and explain integration with DynamoDB access patterns.

**Context Files to Provide:**  
- @docs/adrs/000-architecture-overview.md (for overall architecture, serverless principles, and pre-decided rules like auth and linting).  
- @docs/adrs/001-database-selection.md (for database choice and CDC integration).  
- @docs/adrs/003-data-modeling-approach.md (for data model, entities, and access patterns to inform API design).  
- @docs/adrs/002-api-framework.md (the partial draft to build upon or complete).  
- @docs/adrs/template.md (for ADR structure).  
- @.cursor/rules/rules.mdc (for pre-decided linting/testing tools).  

**Key Decisions to Make:**  
- Choose the API framework (e.g., FastAPI vs. Flask) based on OpenAPI generation, validation, async support, and serverless compatibility.  
- Explain how it leverages ADR-003's schema (e.g., querying GSIs for user tasks).  
- Tie in pre-decided elements: Cognito for auth (via API Gateway), Pydantic for validation, pytest for testing, and linting tools for code quality.  

**Constraints:**  
- Align with ADR-000's serverless-first approach and evaluation criteria (e.g., API Design & Correctness).  
- Keep incremental: Focus on framework rationale, not full implementation details.  
- Prioritize readability and evidence-based trade-offs.  
- If needed, suggest small code snippets for illustration, but avoid boilerplate.  

**Output Format:**  
- Generate the full ADR-004 content in Markdown, following the template.md structure.  
- Include placeholders for manual review: [Your Rationale Here] for key decisions, [Validation Notes Here] for testing/alignment checks, and [Commit Links Here] for traceability.  
- After generation, I'll review and refine manually based on project rules.

**Validation Steps:**  
- Cross-check against provided ADRs for consistency (e.g., no conflicts with DynamoDB Streams).  
- Ensure it supports the challenge's OpenAPI and input validation requirements.  
- Confirm brevity and focus on architectural choice over operations.

[Your Rationale Here]: ✅ Minimal documentation overhead
✅ Type safety
✅ Async support
✅ Starlette + uvicorn provides high throughput
✅ Tests: TestClient and pytest-asyncio  
[Validation Notes Here]: verify fastApi compatibility with lambda.  
```


commit link: