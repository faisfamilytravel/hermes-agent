# t_9e5ac28a verification command log

UTC checkpoint: 2026-08-02T20:08:42Z
Working tree: /Users/rfais370/.hermes/hermes-agent

1. Tests-first RED evidence
   `scripts/run_tests.sh tests/hermes_cli/test_execution_provenance.py tests/hermes_cli/test_apply_profile_override.py`
   Output: `tests-first-red.txt`
   Exit: `tests-first-red.rc` = 1 (expected RED)
   Result: 10 explicit-sensitive-option cases failed; 38 tests passed. All profile-integration tests passed before the production redaction correction.

2. Prescribed combined regression suite
   `scripts/run_tests.sh tests/hermes_cli/test_execution_provenance.py tests/hermes_cli/test_apply_profile_override.py tests/hermes_cli/test_kanban_db.py tests/gateway/test_status_command.py tests/gateway/test_status.py`
   Output: `prescribed-suite.txt`
   Exit: `prescribed-suite.rc` = 0
   Result: 375 passed, 0 failed.

3. Prescribed standalone `test_main` suite
   `scripts/run_tests.sh tests/hermes_cli/test_main.py`
   Output: `test-main.txt`
   Exit: `test-main.rc` = 1
   Result: runner reported no test files discovered because `tests/hermes_cli/test_main.py` does not exist in this checkout. No substitute suite was run because the task forbids substituting prescribed tests.

4. Post-edit Mission Control control-plane harness
   `python3 /Users/rfais370/workspace/mc-regression/harness.py`
   Output: `post-harness.txt`
   Exit: `post-harness.rc` = 0
   Result: A1-A29 all PASS (29/29).

5. Static compilation
   `python3 -m py_compile hermes_cli/execution_provenance.py tests/hermes_cli/test_execution_provenance.py tests/hermes_cli/test_apply_profile_override.py`
   Output: `py-compile.txt`
   Exit: `py-compile.rc` = 0.

6. Diff whitespace checks
   `git diff --check -- tests/hermes_cli/test_apply_profile_override.py`
   `git diff --no-index --check /dev/null hermes_cli/execution_provenance.py`
   `git diff --no-index --check /dev/null tests/hermes_cli/test_execution_provenance.py`
   Output: `diff-check.txt`
   Normalized exit: `diff-check.rc` = 0. (`git diff --no-index` returns 1 for a clean non-empty diff.)

7. Scope
   Product/test files in this correction: exactly:
   - `hermes_cli/execution_provenance.py`
   - `tests/hermes_cli/test_execution_provenance.py`
   - `tests/hermes_cli/test_apply_profile_override.py`

No restart, activation, promotion, configuration change, commit, push, merge, deploy, or external action was performed.
