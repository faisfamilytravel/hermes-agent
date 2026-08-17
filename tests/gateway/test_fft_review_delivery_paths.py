"""Regression guard (order 171245R item 3): the [[fft_review:...]] directive
must be expanded on BOTH delivery paths — the live gateway adapter
(scheduled fires) and the standalone HTTP sender (source=direct hand runs).
171204R disclosed the two-path split; this file fails if either stops
expanding, and covers the plain-reply revision binding (item 2)."""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_repo = str(Path(__file__).resolve().parents[2])
if _repo not in sys.path:
    sys.path.insert(0, _repo)

from tests.gateway.test_fft_review_callbacks import _ensure_telegram_mock

_ensure_telegram_mock()

from gateway.config import PlatformConfig
from plugins.platforms.telegram.adapter import TelegramAdapter
from plugins.platforms.telegram import fft_review


WRAPPED = "[Cron delivery: FFT Script Pipeline 0700 ET Morning Commander Review]\n[[fft_review:p20260817x]]\n\nfooter text"


def _adapter():
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="test-token", extra={}))
    adapter._bot = AsyncMock()
    return adapter


def test_marker_matches_wrapped_content():
    # Cron delivery wraps the directive; anchored matching regressed once.
    assert fft_review.match_marker(WRAPPED) == "p20260817x"
    assert fft_review.match_marker("[[fft_review:abc-123]]") == "abc-123"
    assert fft_review.match_marker("no marker here") is None


@pytest.mark.asyncio
async def test_gateway_adapter_path_expands_directive():
    adapter = _adapter()
    flow = MagicMock()
    flow.current_delivered.return_value = False
    with patch.object(adapter, "_fft_review_flow", return_value=flow):
        with patch.object(adapter, "_send_fft_review_current", new_callable=AsyncMock) as send_current:
            result = await adapter.send("8718328058", WRAPPED)
    assert result.success
    send_current.assert_awaited_once_with("p20260817x", "8718328058")
    # The raw marker must never go out through the normal text path.
    adapter._bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_standalone_path_expands_directive():
    from gateway.config import Platform
    import tools.send_message_tool as smt
    pconfig = MagicMock()
    pconfig.token = "test-token"
    with patch.object(fft_review, "standalone_deliver",
                      return_value={"success": True, "message_id": "77"}) as sd:
        result = await smt._send_to_platform(
            Platform.TELEGRAM, pconfig, "8718328058", WRAPPED
        )
    sd.assert_called_once_with("p20260817x", "test-token", "8718328058")
    assert result == {"success": True, "message_id": "77"}


def test_keyboard_is_approve_revise_reject():
    rows = fft_review.keyboard_rows("p1", 0)
    labels = [b["text"] for row in rows for b in row]
    assert labels == ["APPROVE", "REVISE", "REJECT"]  # HOLD retired 171245R


def test_reply_binding_finds_awaiting_item(tmp_path):
    packets = tmp_path / "review-ux" / "packets"
    packets.mkdir(parents=True)
    state = {
        "schema": "fft-script-review-packet-v1",
        "packet_id": "fft-review-test-b2",
        "status": "ACTIVE", "current_index": 0,
        "chat_id": "8718328058", "user_id": "8718328058",
        "items": [{
            "script_id": "FFT-SCRIPT-TEST-01", "sequence": 1,
            "format": "carousel", "version": 1, "sha256": "x", "path": "x",
            "status": "AWAITING_INSTRUCTIONS",
            "revision_token": "tok123",
            "telegram_message_id": "9001",
            "telegram_chunk_ids": ["9000", "9001"],
        }],
        "events": [],
    }
    (packets / "fft-review-test-b2.json").write_text(json.dumps(state))
    hit = fft_review.find_reply_binding("9000", state_root=tmp_path)
    assert hit == ("fft-review-test-b2", 0, "tok123")
    assert fft_review.find_reply_binding("1234", state_root=tmp_path) is None
