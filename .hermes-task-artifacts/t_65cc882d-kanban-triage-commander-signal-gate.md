# t_65cc882d — Kanban TRIAGE Commander-signal gate

## Scope

Suppress staff-only `block_loop_detected` TRIAGE events from subscriber notifications unless the event payload explicitly sets `kind` to `needs_input`. This is a source-only change: no gateway restart, external send, credential/config change, subscription restoration, or live notification test was performed.

## Root cause and behavior

`GatewayKanbanWatchersMixin._kanban_notifier_watcher` formatted every `block_loop_detected` event as “needs a human decision.” The event payload already provides a deterministic discriminator: `kind == "needs_input"` is the human-decision class. The notifier now silently consumes all other loop kinds while retaining the claimed cursor, so they do not replay or wedge later valid events.

The positive path is preserved: an explicit `needs_input` loop still sends the TRIAGE notification. The negative regression covers `transient`, `dependency`, and `capability`; it includes the `t_1f7cda0c` transient/Commander-decision-NO class and asserts both no delivery and cursor advancement.

## Changed paths and SHA-256

- `/Users/rfais370/.hermes/hermes-agent/gateway/kanban_watchers.py`
  - `c2b77084294d0cce2c7dad86487857a14df2c9ce2e140d0e5226492d737094e8`
- `/Users/rfais370/.hermes/hermes-agent/tests/gateway/test_kanban_notifier.py`
  - `091eb8ca1ffd3c8c1d9161c69ef325831b76828d2c8bb453667c1d35d59067bb`

## Control-plane harness

Authoritative harness: `/Users/rfais370/workspace/mc-regression/harness.py`

- Harness SHA-256 before and after: `9c61d46ce1168ea8292adcfd0b3562297cce32fa41993cfc3b41af166ebb3fa0`
- Pre-change: exit 0, 48/48 PASS.
- Post-change: exit 0, 48/48 PASS.
- Both runs emitted the expected loud-retirement evidence for disabled Staff Bus operations `tasking_requires_xo_verification` and `detect_stale`; all harness assertions passed. No harness assertion was changed.

## Regression evidence

- RED (before production gate): `test_notifier_silences_transient_block_loop_without_human_decision` failed because a `transient` event sent `🛑 ... needs a human decision`.
- GREEN focused positive/negative suite: 4 passed in 0.32s.
  - Explicit `needs_input` TRIAGE notification: delivered.
  - `transient`, `dependency`, `capability`: silent and cursor advanced.
- Full notifier module: 12 passed in 1.09s.
- Syntax and whitespace: `python3 -m py_compile gateway/kanban_watchers.py tests/gateway/test_kanban_notifier.py` and `git diff --check` passed.

All test invocations used a clean temporary `HERMES_HOME`; no production Kanban database or messaging adapter was written.

## Rollout/restart gate

XO holds activation. Do not restart the gateway or restore the Commander Telegram subscription on `t_1f7cda0c` as part of this task. The patch remains a verified source change until XO independently reviews and schedules any approved activation.
