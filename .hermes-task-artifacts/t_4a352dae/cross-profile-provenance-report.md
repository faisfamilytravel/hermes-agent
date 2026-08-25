# T1 cross-profile execution provenance — implementation evidence

- Task: `t_4a352dae`
- Timestamp: `2026-08-02T18:05:04Z`
- Authority: Commander-direct Kanban task; implementation only; no service restart or external action.

## Result

Implemented an early Hermes entry-point gate and shared execution-provenance ledger for cross-profile agent launches.

- Same-profile work and admin/read-only CLI operations are unchanged.
- Mission Control Kanban launches remain authorized by existing task/run/claim-lock custody and are recorded as `mission_control_kanban`.
- Direct cross-profile agent launches fail closed with exit code `77` unless `HERMES_EXECUTION_AUTHORITY` contains all bounded Commander fields: authority class/reference, source, target, scope, one-shot flag, expiry, execution ID, evidence, and terminal condition.
- Direct authority is one-shot, expiry checked, source/target bound, and replay rejected by execution ID.
- Gateway `/status` now displays the shared ledger with authority class/reference, source, target, path, Kanban tracking, scope, one-shot, expiry, execution ID, evidence, terminal condition, and live/terminal process state.
- Launch-path coverage includes the installed/module path with `--profile/-p` and profile-scoped `HERMES_HOME`.

## Files

- `hermes_cli/execution_provenance.py` — new bounded-authority validator, append-only shared ledger, live/terminal resolution, status rendering.
- `hermes_cli/main.py` — pre-profile-switch enforcement for explicit profile and profile-scoped `HERMES_HOME` launches.
- `hermes_cli/kanban_db.py` — preserves the dispatch source profile before the worker target is applied.
- `gateway/slash_commands.py` — command-wide shared execution visibility in `/status`.
- `tests/hermes_cli/test_execution_provenance.py` — missing-authority, valid authority, mismatch, expiry, replay, read-only, Kanban custody, and status-state tests.

Current SHA-256:

- `hermes_cli/main.py`: `7e2057db2fa230a5c641b353c09d263058ae29c1d8f7f4bb4973b8440afe37bc`
- `hermes_cli/kanban_db.py`: `ffd3719c39eedb503eb61d1167ad7d8cfac7b06545f4084ca4e91742c75b70e1`
- `gateway/slash_commands.py`: `9c3d461a12f19dfc2197edd94603dce2e17e116c1861f9a03230e668379554d4`
- `hermes_cli/execution_provenance.py`: `aaea3feea68d7c0a2426172a6e09f232a8636b2f12af88741205a551a370d3e8`
- `tests/hermes_cli/test_execution_provenance.py`: `13da28480f027badb8192c1a55dc90e693804c046e12e9c93a4c7ada9b05ce2b`
- Focused diff: `4567df9539f5d060eb1c71386b2e976e9fb6faea6628cbf55e8f3e586340f6cd`

Rollback copies are under `.hermes-task-artifacts/t_4a352dae/backups/`.

## Regression evidence

CPL-2026-07-30-001 authoritative harness:

- Pre-edit: `python3 /Users/rfais370/workspace/mc-regression/harness.py` → rc `0`, `29/29 PASS`.
- Post-edit: same command → rc `0`, `29/29 PASS`.
- Post stdout SHA-256: `afbede942a0690f36f059d0090e6fe4188f35e7fa17cb0e898016035a1c83c90`.
- Post stderr SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Focused tests:

- `scripts/run_tests.sh tests/hermes_cli/test_execution_provenance.py tests/hermes_cli/test_apply_profile_override.py` → `18/18 PASS`.
- `scripts/run_tests.sh tests/hermes_cli/test_kanban_db.py` → `223/223 PASS`.
- `scripts/run_tests.sh tests/gateway/test_status_command.py tests/gateway/test_status.py` → `104/104 PASS`.
- Total final focused tests: `345/345 PASS`.
- `git diff --check` passed.

Negative live launch tests:

- `HERMES_PROFILE=csm python3 -m hermes_cli.main -p s6 chat -q test` without authority → rc `77`.
- `HERMES_PROFILE=csm HERMES_HOME=.../profiles/s6 python3 -m hermes_cli.main chat -q test` without authority → rc `77`.
- Evidence: `.hermes-task-artifacts/t_4a352dae/negative-launch-tests.txt`, SHA-256 `5afea9a5745285d872fee68bda3e4a8518b2a3015e373a48447427d6335ba164`.

## Boundary and residual risk

This is a same-OS-user policy boundary, not a cryptographic sandbox. Another process running as the same macOS user can forge environment variables or edit the shared JSONL ledger. The guard provides fail-closed enforcement at supported Hermes entry points, one-shot/expiry/replay controls, and auditable visibility; it cannot defend against deliberate same-user filesystem/process tampering. Direct execution that bypasses Hermes entry points entirely is outside the gate and must be detected by separate process-accounting controls.

No Commander decision is required for the implemented internal correction. Human code review remains the required gate before accepting or merging these changes. No restart was performed.
