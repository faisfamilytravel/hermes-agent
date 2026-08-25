# Correction / supersession evidence — t_b1a3ee4f

Generated: 2026-08-02T19:42:35Z
Parent implementation evidence: `.hermes-task-artifacts/t_2207864a/review-bundle.md`
Authority: Kanban task `t_b1a3ee4f`; CPL-2026-07-30-001 control-plane change discipline.

## Result

PASS — ready for fresh CSM inspection and XO verification. This bundle supersedes the parent review bundle only for the two assigned correction questions: bounded cross-profile execution provenance and generic sensitive command-line argument redaction. It does not self-certify CSM or XO approval.

## Corrections

1. Provenance remains bound to the shared `Path.home() / ".hermes" / "execution-provenance.jsonl"` ledger, independent of target-profile `HERMES_HOME`; existing source/target, structured Commander authority, Mission Control Kanban custody, replay, and expiry checks remain unchanged.
2. `_redacted_execution_path()` now recognizes bounded credential-bearing long-option families case-insensitively, with hyphen/underscore normalization and both `--option value` and `--option=value` forms.
3. Generic redaction covers terminal credential terms (`authorization`, `cookie`, `credential[s]`, `passphrase`, `passwd`, `password`, `secret`, `token`) plus security-qualified `*-key` names (`api`, `access`, `auth`, `client`, `encryption`, `private`, `secret`, `signing`, `webhook`).
4. Boundary tests prove non-sensitive lookalikes remain visible: `--token-count`, `--password-policy`, `--secret-santa`, `--cookie-file-count`, and adversarial `--my-key`.
5. Prompt redaction remains intact for `-q`, `--query`, `-z`, and `--prompt`.

## F1–F6 authorization behavior

No authorization branches were changed. The pre/post 29-assertion control-plane harness is green, and the governing provenance suite covers direct Commander authority, target mismatch, expiry, replay, atomic one-shot consumption, Mission Control Kanban custody, inherited/forged custody rejection, missing DB fail-closed behavior, external noninteractive rejection, shared-ledger location, same-profile/read-only exemptions, and terminal visibility.

## Verification

- Pre-edit harness: 29/29 PASS (`pre-harness.txt`, exit 0).
- Governing failure reproduced tests-first: 8 redaction failures, 16 existing tests passed (`pre-fix-tests.txt`, expected exit 1).
- Focused post-fix: 24 passed, 0 failed (`post-fix-focused.txt`, exit 0).
- Post-edit harness: 29/29 PASS (`post-harness.txt`, exit 0).
- Governing suites + `test_main_invocation`: 36 passed, 5 skipped, 0 failed (`governing-tests.txt`, exit 0).
- `python3 -m hermes_cli.main --help`: PASS (`test-main.txt`, exit 0).
- `python3 -m py_compile ...`: PASS (`py-compile.txt`, exit 0).
- Tracked and untracked whitespace checks: PASS (both normalized exit 0).
- Adversarial probes: 12/12 PASS (`adversarial-probes.txt`, exit 0).
- Complete diff inspected: `task-complete.diff`, 624 lines, covering `hermes_cli/main.py`, full `hermes_cli/execution_provenance.py`, and full `tests/hermes_cli/test_execution_provenance.py`.

## Evidence map

- Exact commands and output pointers: `commands.md`
- Complete pre/post harness output: `pre-harness.txt`, `post-harness.txt`
- Complete test outputs: `pre-fix-tests.txt`, `post-fix-focused.txt`, `governing-tests.txt`
- CLI/static/diff outputs: `test-main.txt`, `py-compile.txt`, `diff-check-tracked.txt`, `diff-check-untracked.txt`
- Executable adversarial probe and output: `adversarial_probe.py`, `adversarial-probes.txt`
- Complete task diff: `task-complete.diff`
- SHA-256 manifest: `SHA256SUMS`

## Fresh-review request

CSM: inspect redaction boundaries, unchanged F1–F6 authority semantics, evidence completeness, and non-overreach.
XO: verify artifact hashes and fan-in only after CSM returns a fresh inspection result.

No protected action was executed: no external contact, publish, spend, credentials, service restart, configuration change, git operation beyond read-only diff/status, deploy, destructive cleanup, or scope expansion.
