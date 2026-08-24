"""Regression coverage for the install E2E sandbox HTTPS proxy."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROXY_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sandbox" / "proxy.py"


def load_proxy_module():
    spec = importlib.util.spec_from_file_location("sandbox_proxy_for_test", PROXY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    saved_argv = sys.argv
    try:
        sys.argv = [str(PROXY_PATH), "/tmp/root", "/tmp/certs", "/tmp/real-ca.pem"]
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    return module


def test_open_upstream_tls_retries_a_failed_handshake(monkeypatch) -> None:
    """A transient upstream TLS EOF must not abort the whole proxy request."""
    proxy = load_proxy_module()
    attempts = 0

    class RawSocket:
        def close(self) -> None:
            pass

    class Context:
        def wrap_socket(self, raw, *, server_hostname):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise proxy.ssl.SSLEOFError(8, "unexpected eof")
            return "connected"

    monkeypatch.setattr(proxy.socket, "create_connection", lambda *args, **kwargs: RawSocket())

    assert proxy.open_upstream_tls("registry.npmjs.org", 443, Context()) == "connected"
    assert attempts == 2
