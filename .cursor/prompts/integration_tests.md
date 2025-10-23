# Prompts

prompt:
create integration tests.
should be able to: create user, create task, update task, delete task, create task again, create task using same idempotency key, create different task using same idempotency key, create 3 tasks with different idempotency keys.
create more users, delete some users.

@api/ really study these first, then make the tests and try to pass them.
@API_TESTING_GUIDE.md if you need

objective:
quick test creation for integration on the layers.

# Subsequent prompts

prompt:
Test Todo API HTTP Endpoints with Real Authentication Simulation
Goal: Test the complete HTTP API with realistic API Gateway authentication simulation, including:
Authentication Testing: Test endpoints with fake JWT claims (simulating real Cognito tokens)
Complete CRUD Workflow: Test full user → task → update → delete cycle via HTTP
Idempotency Testing: Test duplicate request handling with Idempotency-Key headers
Error Scenarios: Test validation errors, missing authentication, invalid data
Performance Testing: Test bulk operations and concurrent requests

 [] API Gateway payload extraction works correctly
[ ] User auto-creation from JWT claims functions
[ ] Task CRUD operations work with real database
[ ] Idempotency prevents duplicate operations
[ ] Proper error responses for invalid requests
[ ] User-scoped access control works
[ ] Data persists correctly in DynamoDB


@test_api_endpoints.py @test_full_api_integration.py check implementation code, they should be extracting user data from api gateway payload, which we're simulating here.
rest of the data should be on body. user creation shouldn't actually have body parameters since it'll create user using api gateway payload.

think first on file and codebase and act later

objective:
my first prompt was lacking, made it better to iterate on result


commit link: 5f5d4cc7c33c714a8b269e98ca09a398384c8eb6