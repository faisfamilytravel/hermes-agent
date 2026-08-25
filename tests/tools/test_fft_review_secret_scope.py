"""Regression: standalone FFT review delivery loads the active profile scope."""
from pathlib import Path
from unittest.mock import patch


def test_fft_review_send_installs_active_profile_scope(tmp_path):
    # Contract test: _handle_send must install the active profile scope before
    # reading gateway configuration. The concrete send stays mocked; no token
    # value or network request is exercised.
    from tools import send_message_tool as sm
    calls = []
    marker = object()
    cfg = type("Cfg", (), {"platforms": {}, "get_home_channel": lambda *_: None})()
    with patch("tools.send_message_tool.build_profile_secret_scope", side_effect=lambda home: calls.append(home) or {"TELEGRAM_BOT_TOKEN": "test"}), \
         patch("tools.send_message_tool.set_secret_scope", return_value=marker), \
         patch("tools.send_message_tool.reset_secret_scope") as reset, \
         patch("tools.send_message_tool.get_hermes_home", return_value=tmp_path), \
         patch("tools.send_message_tool.prepare_send_message_platforms"), \
         patch("gateway.config.load_gateway_config", return_value=cfg):
        # Empty target stops after config load; that is enough to verify scope.
        sm._handle_send({"target": "telegram", "message": "FFT_REVIEW:packet"})
    assert calls == [tmp_path]
    reset.assert_called_once_with(marker)


if __name__ == "__main__":
    test_fft_review_send_installs_active_profile_scope(Path("/tmp/xo"))
    print("PASS")
