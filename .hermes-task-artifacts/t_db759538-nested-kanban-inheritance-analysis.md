# Nested Hermes Kanban-context inheritance — root-cause analysis and bounded remediation proposal

Date: 2026-08-23
Task: t_db759538
Owner: S-6
Due date: 2026-08-24
Scope: read-only diagnosis and proposal. No code, configuration, service, credential, or board changes were made.

## Exact defect

A dispatcher worker's task-scoped Kanban identity is process-environment state. A nested fresh Hermes process launched from that worker inherits `HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, `HERMES_KANBAN_WORKSPACE`, `HERMES_KANBAN_BOARD`, and related `HERMES_KANBAN_*` values unless its spawning path explicitly scrubs them.

The nested process therefore satisfies the existing worker predicate even though it was not launched or claimed by the dispatcher. It receives the Kanban lifecycle schema and worker guidance, resolves an omitted `task_id` to the parent task, and has the parent run id available for lifecycle compare-and-swap. A `kanban_complete` call can consequently close the parent lifecycle.

This is an authority-boundary defect: environment inheritance is being accepted as proof of dispatcher ownership across a process boundary.

## Verified evidence and exact path

1. `agent/delegation_context.py:37-45` defines the inherited task-scoped key set. Its existing `scrub_kanban_env()` removes all of them, but only delegates call it today.
2. `tools/environments/local.py:1283-1342` constructs foreground terminal child environments from `dict(os.environ | env)`. It calls `_scrub_delegated_child_kanban_env()` at line 1340.
3. `tools/environments/local.py:533-545` performs that scrub only if `is_delegated_child_process_context()` is true. A direct nested `hermes ... chat -q` launched from a worker is neither an in-process `delegate_task` child nor marked `HERMES_DELEGATED_CHILD_CONTEXT`; its parent worker's Kanban keys remain in the child environment.
4. `tools/environments/local.py:470-530` uses the same delegate-only condition for the sanitized/background spawn path. `build_subprocess_env()` routes through it at lines 674-734.
5. `model_tools.py:427-440` force-adds the Kanban toolset whenever `HERMES_KANBAN_TASK` is present and the execution appears dispatcher-owned.
6. `tools/kanban_tools.py:103-119` exposes lifecycle tools under the same environment-based predicate. `tools/kanban_tools.py:142-153` defaults an omitted lifecycle task id to `HERMES_KANBAN_TASK`; `:156-166` extracts the run id from `HERMES_KANBAN_RUN_ID`.
7. `hermes_cli/main.py:2846-2864` preserves an already-inherited `HERMES_KANBAN_BOARD`; it only pins a board if no board value is present.
8. XO `agent.log` for session `20260823_123913_e64c4e` records the unauthorized nested session's `kanban_show` at line 17012, the evidence-file patch at line 17110, and `kanban_complete` at line 17158. The corresponding session transcript shows that its user instruction authorized exactly one read-only GitHub identity canary and prohibited writes. The log proves the tool sequence; the exact shell/terminal command that spawned the nested process is UNVERIFIED IN THIS CONTEXT.

## Existing safeguards and gap

Existing controls already solve two sibling cases, but not a direct new Hermes child process:

- `agent/delegation_context.py:48-161` and `tests/tools/test_delegate_kanban_isolation.py` isolate `delegate_task` children through ContextVars and scrub their subprocess environments.
- `agent/delegation_context.py:73-121` and `tests/cron/test_cron_kanban_env_isolation.py` mark in-process cron runs as non-dispatcher-owned without mutating the worker's global environment.

Those are not applicable to a new OS process started through the terminal/local environment. The ContextVar does not cross `exec`, and no child marker is installed for this launch path.

## Operational consequence

A nested `hermes chat -q` is misclassified as its parent worker. It can read parent-board content and alter the parent lifecycle despite a narrower nested prompt. The parent worker's running task can be marked complete with evidence produced by the nested job, creating false closure and bypassing the parent worker's intended terminal-action custody.

The parent worker itself must keep its lifecycle tools and heartbeat. A remediation must not clear process-global `os.environ`, because that would race the legitimate worker heartbeat and concurrent in-process work; the cron isolation code documents this concern at `agent/delegation_context.py:85-88`.

## Proposed minimal correction (not applied)

Change only the child-environment factory boundary in `tools/environments/local.py`:

1. Generalize `_scrub_delegated_child_kanban_env()` (rename to reflect its broader purpose) so it removes the complete `KANBAN_ENV_KEYS` whenever either:
   - the current execution is a delegated-child lineage, or
   - the current process is a dispatcher-owned worker and is constructing an OS child-process environment.
2. Apply that helper to both existing call sites:
   - `_make_run_env()` for foreground terminal children; and
   - `_sanitize_subprocess_env()` for background/process-registry and `build_subprocess_env()` children.
3. Do not mutate the parent worker's `os.environ`; construct and pass only a scrubbed child dictionary. Do not change dispatcher `_default_spawn()`, which is the legitimate owner that deliberately creates a worker environment with those values.
4. Do not add a user-facing environment flag. The current `KANBAN_ENV_KEYS` list is the single source for the task-scoped values to remove.

Expected result: any nested normal Hermes CLI process starts as an unscoped chat session: no inherited task, run, workspace, database, claim lock, or board pin; no force-added Kanban lifecycle schema; no default parent task id. The original dispatcher worker retains its existing environment and tools.

Bounded limitation: this correction removes accidental inherited lifecycle authority from agent-spawned child environments. It does not make direct human CLI/database access a new security boundary; the human CLI remains an administrative surface. A later hardening effort could introduce dispatcher-issued, non-inheritable lifecycle capability credentials and kernel enforcement, but that is broader than the reported direct-child defect and is not included in this proposal.

## Regression test plan (not applied)

Add focused tests beside `tests/tools/test_delegate_kanban_isolation.py` and/or `tests/tools/test_build_subprocess_env.py`:

1. **Exact red-path unit test — terminal child environment**
   - Seed every key in `agent.delegation_context.KANBAN_ENV_KEYS`, including task and run id, in a simulated dispatcher-worker parent.
   - Call `tools.environments.local._make_run_env({})`.
   - Assert every Kanban key is absent from the returned environment and unchanged in parent `os.environ`.
   - Verify a normal non-Kanban variable and profile home propagation remain present.

2. **Background/shared-factory parity**
   - Repeat the preceding assertion for `_sanitize_subprocess_env()` and `build_subprocess_env()`.
   - This prevents the foreground-only fix that would leave background terminal/process-registry or other shared factory children vulnerable.

3. **Deterministic subprocess E2E — nested CLI analogue**
   - Create and claim a temporary parent task/run using the existing `_make_running_kanban_task` fixture pattern.
   - Start a real `LocalEnvironment.execute()` child with a parent-worker environment and a short Python probe importing the repo under test.
   - In the child assert: `HERMES_KANBAN_TASK` and `HERMES_KANBAN_RUN_ID` are absent; `get_tool_definitions(enabled_toolsets=["terminal"], quiet_mode=True)` contains no `kanban_*`; a direct `kanban_tools._handle_complete({"summary": "attempt"})` returns a missing-task-id error.
   - Re-open the DB in the parent and assert task status and run status are both still `running`; workspace still exists.

4. **Legitimate-worker retention**
   - In the parent (not a child), with the same dispatcher-worker environment, assert Kanban lifecycle tools are present and `_default_task_id(None)` equals the parent task id.
   - This proves the correction has not stripped the actual worker's tools or custody surface.

5. **Existing sibling controls remain green**
   - Run `tests/tools/test_delegate_kanban_isolation.py`, `tests/cron/test_cron_kanban_env_isolation.py`, and the new focused tests. They cover delegate ContextVar isolation, cron in-process isolation, and the newly missing OS-child boundary respectively.

Acceptance criterion: before the proposed patch, test 1 or test 3 reproduces inherited task identity (red). After the patch, all five tests pass, including preservation of parent worker state.

## Validation status

The pre-existing delegate/cron isolation suites were exercised from this dispatcher-worker context. Both the inherited-context run and a rerun with inherited `HERMES_KANBAN_*` values removed produced 21 passed / 3 failed. The three failures occur before their assertions because their temporary `HERMES_HOME` does not isolate the shared-board resolver in this launch context; it resolves `/Users/rfais370/.hermes/kanban.db`, and the repository's hermetic write guard correctly refuses the live-board write. `hermes_cli/kanban_db.py:566-586` identifies the dedicated `HERMES_KANBAN_HOME` shared-root override that the fixture must set for a hermetic board. This is a pre-existing test-fixture/environment isolation finding, not evidence against the delegate/cron isolation logic. The implementation test must set a temporary `HERMES_KANBAN_HOME` before creating its temporary board. No tests for the proposed direct OS-child correction exist yet, so that correction is UNVERIFIED IN THIS CONTEXT.

## Commander decision

Diagnosis/proposal: NO.

Running-behavior change: YES. The correction modifies subprocess-environment behavior that affects tool availability and lifecycle authority. Before implementation, obtain Commander authorization for the bounded change, run the required control-plane harness before and after, record hashes, and stop/rollback if either focused lifecycle test or broader Kanban regression fails.

Recommended exact approval phrase: `Approve the bounded S-6 repair that strips dispatcher Kanban context only from child subprocess environments, preserves the parent worker lifecycle surface, and stops on failed regression evidence.`

## Read-back

This document was written at the stated absolute path and is intended to be read back and SHA-256 verified in this task run before closure.
