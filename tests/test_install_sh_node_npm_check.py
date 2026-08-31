"""Regression tests for install.sh Node/npm checks (#77003).

A stray `node` symlink without a sibling `npm` (leftover from a node
version manager) made the installer report "✓ Node.js found" and then fail
opaquely at the desktop stage. Node must only count as found when npm
resolves on the same PATH, and npm install stages must not report success
when the install actually failed.
"""

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"


def test_check_node_requires_npm_alongside_node() -> None:
    """check_node must not report success when only `node` resolves.

    Before the fix, `command -v node` succeeding was enough — a stray node
    symlink (no sibling npm) passed the check, every later `npm install`
    failed silently, and the desktop build died with an opaque
    "Node.js / npm unavailable" (#77003).
    """
    text = INSTALL_SH.read_text()

    # The system-toolchain branch now gates on BOTH node and npm.
    assert (
        "if command -v node &> /dev/null && command -v npm &> /dev/null \\" in text
    )
    # The "node found but npm missing" case has its own explicit branch that
    # falls through to installing the Hermes-managed Node (which bundles npm).
    assert "node found but npm is not on PATH (stray node symlink?)" in text


def test_check_node_managed_requires_npm() -> None:
    """The Hermes-managed fallback requires npm and native-build headers."""
    text = INSTALL_SH.read_text()
    expected = (
        '[ -x "$HERMES_HOME/node/bin/node" ] && '
        '[ -x "$HERMES_HOME/node/bin/npm" ] ' + "\\"
    )
    assert expected in text
    assert '[ -f "$HERMES_HOME/node/include/node/common.gypi" ]' in text
    assert text.index('if [ -x "$HERMES_HOME/node/bin/node" ]') < text.index(
        'if command -v node &> /dev/null && command -v npm &> /dev/null'
    )


def test_managed_node_exports_its_header_directory_for_node_gyp() -> None:
    """A tarball-managed Node must compile native dependencies from its own headers."""
    text = INSTALL_SH.read_text()

    assert 'local node_dir="$HERMES_HOME/node"' in text
    assert '[ -f "$node_dir/include/node/common.gypi" ]' in text
    assert 'export npm_config_nodedir="$node_dir"' in text
    assert text.count("configure_managed_node_gyp_headers") == 3


def test_node_dependency_install_uses_bounded_npm_transport_retries() -> None:
    """Registry/proxy TLS closures must retry serially with useful diagnostics.

    The install/update E2E sandbox can close concurrent TLS streams while npm
    acquires browser-tool dependencies.  Retrying the complete install with
    npm's fetch retries and one socket distinguishes that transport failure
    from an installer defect without turning the installer into an unbounded
    retry loop.
    """
    text = INSTALL_SH.read_text()

    assert "run_npm_install_with_retry" in text
    assert "--fetch-retries=3" in text
    assert "--fetch-timeout=120000" in text
    assert "--maxsockets=1" in text
    assert "npm transport attempt" in text
    assert "npm transport retries exhausted" in text
    assert "Exit handler never called" in text
    assert 'rm -rf -- node_modules' in text


def test_npm_retry_does_not_misclassify_later_non_transport_failure(tmp_path: Path) -> None:
    """Each npm attempt must be classified from its own output, not prior logs."""
    text = INSTALL_SH.read_text()
    retry_source = text[
        text.index("NPM_TRANSPORT_ATTEMPTS=2") : text.index(
            "# Return success only when the host is an apt release"
        )
    ]
    retry_functions = tmp_path / "npm-retry-functions.sh"
    retry_functions.write_text(retry_source)

    npm = tmp_path / "fake-npm"
    npm.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "state=${NPM_RETRY_STATE:?}\n"
        "attempt=$(cat \"$state\" 2>/dev/null || printf 0)\n"
        "attempt=$((attempt + 1))\n"
        "printf '%s' \"$attempt\" > \"$state\"\n"
        "if [ \"$attempt\" -eq 1 ]; then\n"
        "  printf '%s\\n' 'npm ERR! UNEXPECTED_EOF_WHILE_READING' >&2\n"
        "  exit 1\n"
        "fi\n"
        "printf '%s\\n' 'npm ERR! code ERESOLVE' >&2\n"
        "exit 42\n"
    )
    npm.chmod(0o755)

    log_file = tmp_path / "npm.log"
    state_file = tmp_path / "attempt-count"
    runner = (
        "set +e\n"
        f"source {retry_functions!s}\n"
        "NPM_TRANSPORT_ATTEMPTS=3\n"
        "NPM_TRANSPORT_ATTEMPT_TIMEOUT=1\n"
        "run_with_timeout() { shift; \"$@\"; }\n"
        "sleep() { :; }\n"
        f"run_npm_install_with_retry {log_file!s} {npm!s} install\n"
        "exit $?\n"
    )
    result = subprocess.run(
        ["bash", "-c", runner],
        env={"NPM_RETRY_STATE": str(state_file)},
        text=True,
        capture_output=True,
    )

    assert result.returncode == 42
    assert state_file.read_text() == "2"
    log = log_file.read_text()
    assert "npm failure is not a recognized transport/proxy error; not retrying." in log
    assert "npm transport retries exhausted; registry/proxy failure remains." not in log
    assert "--- npm transport attempt 3/3 ---" not in log

