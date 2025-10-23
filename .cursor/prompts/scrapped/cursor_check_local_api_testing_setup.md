# Check local API testing setup
_Exported on 10/20/2025 at 22:19:59 GMT-3 from Cursor (1.7.52)_

---

**User**

study codebase, figure out if i have what  is  needed to test the api locally, also, do  i have the setup for sqs -> lambda -> dynamodb?
lambda triggered by polling sqs for POST as per @003-data-modeling-approach.md @000-architecture-overview.md 

---


---

**User**

so, now that you know this, create a runbook

---


---

**User**

so, checking /docs i see there's no create and delete user, also there's no separate lambda for sync/async am i right? study codebase

---

---

**User**

give me whole code for the 3

---


---

**User**

create tests for @user_repository.py , hull coverage for happy paths, common errors, etc.

---

---

**User**

now we create tests for @user_service.py , @adrs/ @api/  for refference, cover all happy paths, some common errors, etc.

---


---

**User**

well per adr we don't have list all users, so this is testing for a failure right? 
we should remove this test

---

---

**User**

sure, but don't i  need to  update @main.py ?

---

---

**User**

i've tried creating a user on /docs and it gave this error, analyze code and see why. i've only started uvicorn, if this endpoint needs aws resources then guide me to setup them correctly (sam local)

---
---

**User**

no such command 'local', you're  now in agent mode, figure out why it's  not working, final objective:
be able to use the code we made on local aws resources. /api/venv/scripts/activate

---


---

**User**

@api/ @adrs/ now that i have all the code, make @template.yaml optimal

---

---

**User**

continue, you have browser access and aws mcp servers if you  need refference

---

---

**User**

try running it then, if current code implementation allows for user creation etc without authentication then it's a good time to know if it's working.
i want the stack working, if it's not possible say so.

remember /api/venv/scripts/activate
you have browser access and mcp servers

---
