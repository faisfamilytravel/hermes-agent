# t_22464318 implementation blocker

## Verified preconditions

- Pre-change control-plane harness passed: 48/48 assertions, exit 0.
- Artifact: `.hermes-task-artifacts/t_22464318/pre-harness.txt`.
- Isolated updater test invocation works when `HERMES_PROFILE` and `HERMES_HOME` are unset and `HOME` points to a temporary directory; baseline focused updater-autostash suite passed 5/5.

## Root cause traced

`gateway/slash_commands.py` launches the detached gateway update and writes only pending/output/exit IPC. `gateway/run.py` treats `.update_exit_code == 0` as success and cleans those IPC files. `hermes_cli/update_cmd.py` returns false for restore conflict but does not expose that outcome to the gateway notifier.

## Current blocker

The task runtime deadline interrupted the TDD implementation before a complete source/test change could be safely applied. I reverted all changes made to `hermes_cli/update_cmd.py`, `tests/hermes_cli/test_update_autostash.py`, and `tests/gateway/test_update_command.py`; no partial updater behavior remains from this run. No live update, fetch/pull, gateway restart, profile mutation, or shared-venv mutation occurred.

## Required next action

A successor should implement a receipt contract across all three seams: create the receipt atomically at gateway launch (launch timestamp/PID/pre-HEAD), merge updater autostash/restore/drop fields atomically, record child exit/post-HEAD before notification, and make both streaming and legacy notifier paths preserve failed receipts until a delivery result confirms success. Then add the isolated real-git success/conflict tests plus notifier delivery-failure retention test, and run the post-change harness and focused suites using the isolated environment above.
