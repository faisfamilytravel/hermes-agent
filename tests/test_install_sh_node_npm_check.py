"""Regression tests for install.sh Node/npm checks (#77003).

A stray `node` symlink without a sibling `npm` (leftover from a node
version manager) made the installer report "✓ Node.js found" and then fail
opaquely at the desktop stage. Node must only count as found when npm
resolves on the same PATH, and npm install stages must not report success
when the install actually failed.
"""

from pathlib import Path

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
    """The Hermes-managed Node fallback also requires its npm to exist."""
    text = INSTALL_SH.read_text()
    expected = (
        '[ -x "$HERMES_HOME/node/bin/node" ] && '
        '[ -x "$HERMES_HOME/node/bin/npm" ] ' + "\\"
    )
    assert expected in text


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

