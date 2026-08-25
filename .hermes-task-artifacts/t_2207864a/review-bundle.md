# Cross-Profile Execution Provenance Gate Correction — Review Bundle

Task: `t_2207864a`
Authority: Commander task packet via Kanban; CPL-2026-07-30-001
Parent implementation task: `t_4a352dae`
Independent inspection source: CSM task `t_41e7c806`
Disposition: implementation complete; independent CSM/XO review required

## Harness certification

- Pre-edit command: `/Users/rfais370/.hermes/venvs/s6/bin/python /Users/rfais370/workspace/mc-regression/harness.py`
- Pre-edit result: PASS, 29/29 assertions (A1–A29).
- Post-edit command: same.
- Post-edit result: PASS, 29/29 assertions (A1–A29).
- Captured output: `pre-harness.stdout`, `post-harness.txt`; return codes are both 0.

## F1–F6 correction matrix

- F1 external-source bypass: human interactive profile launch remains intentional; external noninteractive agent invocation (`-q`/query/prompt mode) now fails closed without structured authority.
- F2 inherited Kanban environment: Kanban fast path now requires source `mission-ctrl` and read-only canonical SQLite agreement for task ID, assignee/target, running state, current run ID, run profile, claim lock, unexpired claims, and recorded worker PID when available. Missing or malformed DB state fails closed.
- F3 race-prone one-shot replay: Commander execution-ID lookup and append are now performed under one exclusive `flock`, with `fsync`; 16-thread regression proves exactly one acceptance.
- F4 prompt leakage: command provenance redacts prompt/query argv payloads while retaining command shape.
- F5 regression depth: positive Commander, valid Kanban, same-profile and read-only paths remain covered; forged source/target/run/claim, missing DB, external unattended launch, concurrency, redaction, and profile overlay cases are covered.
- F6 ledger path under profile overlay: regression proves the default ledger remains command-wide at `~/.hermes/execution-provenance.jsonl` even when `HERMES_HOME` points to a profile.

## Files changed

- `hermes_cli/execution_provenance.py`
- `tests/hermes_cli/test_execution_provenance.py`

Both files were untracked parent-task deliverables before this correction. The parent bundle at `.hermes-task-artifacts/t_4a352dae/task.diff` is the recoverable pre-correction implementation snapshot. No unrelated tracked file was modified by this task.

## Tests-first evidence

- Pre-fix focused suite: 10 failed, 5 passed. Failures covered F1/F2/F3/F4 plus updated positive contract expectations.
- Post-fix focused suite: 15 passed, 0 failed.
- Canonical wrapper: `scripts/run_tests.sh`.
- Static checks: `python3 -m py_compile` PASS; `git diff --check` PASS.
- Live schema check confirms all queried `tasks` and `task_runs` columns exist.

## Review cautions

- This remains a same-OS-user policy boundary, not a cryptographic security boundary; the source module says so explicitly.
- PID binding is verified when Kanban has populated worker PID. Null PID is tolerated because dispatchers record a child PID after spawn, creating a startup race; all other live custody fields must agree.
- Cross-platform concern: the atomic replay implementation uses `fcntl`, appropriate for the active macOS control plane. Maintainers should decide whether upstream portability requires a Windows locking abstraction before merge.
- The existing worktree contains unrelated dirty files. Review only the two files listed above and the task artifacts.

## Required independent gates

1. CSM inspect F1–F6 semantics, fail-closed behavior, and evidence hashes.
2. XO verify fan-in and authorize acceptance or return for correction.
3. Mission Control must not self-mark `xo_verified` or Commander-level closure.
