# CSM Inspection Report — t_16778a5c

Result: PASS

Scope inspected:
- Review bundle: `.hermes-task-artifacts/t_9e5ac28a/t_9e5ac28a-review-bundle.tar.gz`
- Manifest: `.hermes-task-artifacts/t_9e5ac28a/SHA256SUMS`
- Current files:
  - `hermes_cli/execution_provenance.py`
  - `tests/hermes_cli/test_execution_provenance.py`
  - `tests/hermes_cli/test_apply_profile_override.py`

Findings:
1. Artifact integrity: PASS.
   - `sha256sum -c .hermes-task-artifacts/t_9e5ac28a/SHA256SUMS` returned OK for every listed artifact.
   - Bundle SHA-256: `ae34ff69a2ea502e5a2e925cd5fbe114c569dde4c1764d29a1cb6ecc5fd6d919`.
   - The bundle contains the three expected product/test files plus verification artifacts.

2. Bundle-to-working-tree match: PASS.
   - `hermes_cli/execution_provenance.py`: `409063f7da31a1dfe59e505018d3f813363627636004f35f8d3005639597e654`.
   - `tests/hermes_cli/test_execution_provenance.py`: `030818454b8fbdcc148355cddc5e4a5b581c59693389ecd4387cb3a8a0e3a3d8`.
   - `tests/hermes_cli/test_apply_profile_override.py`: `48117f411c3bf19b5939e363e1d535662bb8566166fe020f125ba0a486b8c90e`.
   - The same hashes were obtained from the tarball and current working-tree files.

3. Guard behavior: PASS.
   - Unauthorized external non-interactive profile launches fail closed.
   - Human interactive profile selection remains allowed.
   - Commander-direct one-shot authority records source, target, scope, evidence, terminal condition, and execution status.
   - Mission Control Kanban custody path is live-bound to task/run/claim database state and rejects forged or mismatched custody.
   - Read-only inspection invocations are exempt from authority.

4. Redaction: PASS.
   - Prompt payloads and sensitive options are redacted from execution path, ledger text, and status formatting.
   - Explicit sensitive options checked: `--body`, `--message`, `--content`, `--authority`, `--system-prompt` in both separated and equals forms.
   - Generic sensitive credentials checked: API key, access token, client secret, password, authorization header, cookie, signing key, webhook token.
   - Lookalike non-secret options remained visible and were not over-redacted.

5. Regression evidence: PASS.
   - Re-ran prescribed combined suite: `scripts/run_tests.sh tests/hermes_cli/test_execution_provenance.py tests/hermes_cli/test_apply_profile_override.py tests/hermes_cli/test_kanban_db.py tests/gateway/test_status_command.py tests/gateway/test_status.py`.
   - Result: 375 passed, 0 failed.
   - Re-ran Mission Control harness: `python3 /Users/rfais370/workspace/mc-regression/harness.py`.
   - Result: A1–A29 PASS.
   - Re-ran static compile: `python3 -m py_compile hermes_cli/execution_provenance.py tests/hermes_cli/test_execution_provenance.py tests/hermes_cli/test_apply_profile_override.py`.
   - Result: exit 0.

6. Prescribed missing test file: NOT A DEFECT IN THIS TASK.
   - `tests/hermes_cli/test_main.py` is absent in this checkout.
   - Prior artifact correctly records that the prescribed standalone test could not run for that reason and no substitute was used.

7. Working-tree state note: PASS WITH OPERATIONAL NOTE.
   - `hermes_cli/execution_provenance.py` and `tests/hermes_cli/test_execution_provenance.py` are untracked in git status.
   - This is expected for newly introduced files but must be included in any review/commit path. Do not lose them by reviewing only tracked diffs.

CSM judgment:
The correction is standards-sound for the stated runtime provenance gate. It closes the unsupported cross-profile execution path, preserves interactive/human and read-only lanes, records command-wide status evidence, and avoids leaking prompt or credential material. Evidence is backed by artifact checksums, direct assertions, targeted regression tests, and the Mission Control harness.

Recommended continuation:
Proceed to reviewer/XO integration with the full bundle and ensure the two untracked files are included if this is committed. No Commander decision is required for this inspection result.
