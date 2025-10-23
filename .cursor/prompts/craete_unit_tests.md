# Prompts

prompt:
Generate comprehensive unit tests for the Python file provided.
@arquivo

1. Requirements

* **Test Runner:** **pytest**.
* **Mocking:** Use the `pytest-mock` fixture (`mocker`) exclusively for all dependencies (network, file I/O, database, external module calls).
* **Path:** The generated tests must operate as if running from the project root.
* **Naming:** Output a single file named `test_FILENAME.py`.

2. Coverage Goals

1.  **Happy Path:** Test functions with typical and boundary-value inputs.
2.  **Failure Modes:** Verify correct exception raising for invalid inputs (`ValueError`, etc.).
3.  **Isolation:** Mock dependencies to test the target logic in isolation, including simulating dependency failure (e.g., mocked external call raising an exception).


Objective:
i'm using this prompt as template to generate unit tests, i change @arquivo for the file i want.

COMMIT LINKS:
eb8bed52099f726a12d4830c00ea0fe49507e78e - user models
3b2059a3032805864880c61bc14cc15e783fb9a0 - task models
934278e8ea17d5cb2aee32496d389f9e00929605 - idempotency models
934278e8ea17d5cb2aee32496d389f9e00929605 - task repository
0e2f4687a6dc5716baa1bee79a4cddf17d8d0b11 - user repository
025f5faf039e85a74d980d527a47c8ffdae673ad - idempotency repository
67c620f4eac3819ff86a7753ca0d875fc3bfaad2 - task service
6d7b1aa961d6a19d40522061be8075ed3ef16fc5 - user service
0d2e8c76582c4c89b9560d70818bcc627892dbf0 - idempotency service

