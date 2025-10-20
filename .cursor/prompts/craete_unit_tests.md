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