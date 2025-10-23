# Starting steps for development project
_Exported on 10/20/2025 at 21:33:22 GMT-3 from Cursor (1.7.52)_

---

**User**

@adrs/ from where should i start developing? 
create a venv? create directories recommended on challenge overview ?


---

---

**User**

ok @004-api-framework-and-architecture.md states we'll do a multi layer Architecture, guide me on how to approach this.
for local development i want to  use sam local, should i first provision the database with sample data for Testing the api?

---


---

**User**

if we're gonna create a template for sam let's already provide all resources for api.
i'll have: api gateway -> lambda async/sync -> (async) SQS -> lambda (trigger with sqs) poller -> dynamodb, (sync) -> dynamodb

---

---

**User**

look at current @api/ dir, now what should  i do?

---

---

**User**

i believe before we start coding we should setup lint? as per @000-architecture-overview.md challenge overview requirements

---

---

**User**

ok now let's code, to setup pydantic models, study @adrs/ to be sure @pydantic_models.py is complete. we'll do one thing at a time and you'll suggest next steps

---


---

**User**

ok let's go to repository layer creation

---


---

**User**

for this file should we start making a .env.example?

---


---

**User**

in this case shouldn't it be .env.dev.example? because won't we need a real .env.example for prod later?

---


---

**User**

now update @task_repository.py to use .env.dev

---


---

**User**

should we make tests for the 2 files we made so far? @task_repository.py @pydantic_models.py 

---

---

**User**

@task_repository.py @pydantic_models.py @adrs/ @rules.mdc 
Create task_service.py , use ADRs for implementation refference, follow set rules. get full coverage.

---


---

**User**

how does it handle idmepotency?

---

---

**User**

@003-data-modeling-approach.md @task_repository.py @task_service.py check if they cover all access patterns. (idempontecy and exponential backoff if it applies), give whole code for files that change. (also be sure they can refference files in other folder  in parent dir, and the fix method won't cause problems  in lambda)

---


---

**User**

give unit tests for these

---


---

**User**

tests for idempotency?

---

---

**User**

@test_task_repository.py @task_repository.py 

---


---

**User**

@test_task_service.py @task_service.py 
fix variable assigned but  never  used. give whole code

question (only answer):
isn't task service file too small? i believe it should cover the use of all @task_repository.py 

---

---

**User**

question, be concise:
is this idempotency checking using repository? check @adrs/, @task_repository.py 
when it goes to prod, and someone POSTS a task, it'll create the idempotency record on dynamodb right?

---


---

**User**

ok, @task_service.py @test_task_service.py @api/ 
create more tests for @task_service.py , full coverage for happy paths, common errors, etc.

---



---

**User**

ok, check everything and plan  next steps  of  implementation

---
