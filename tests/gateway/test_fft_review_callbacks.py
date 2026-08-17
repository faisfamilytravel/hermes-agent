"""Offline tests for the persistent FFT Telegram review callback bridge."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_repo = str(Path(__file__).resolve().parents[2])
if _repo not in sys.path:
    sys.path.insert(0, _repo)


def _ensure_telegram_mock():
    if "telegram" in sys.modules and hasattr(sys.modules["telegram"], "__file__"):
        return
    mod = MagicMock()
    mod.ext.ContextTypes.DEFAULT_TYPE = type(None)
    mod.constants.ParseMode.MARKDOWN = "Markdown"
    mod.constants.ParseMode.MARKDOWN_V2 = "MarkdownV2"
    mod.constants.ParseMode.HTML = "HTML"
    mod.constants.ChatType.PRIVATE = "private"
    mod.constants.ChatType.GROUP = "group"
    mod.constants.ChatType.SUPERGROUP = "supergroup"
    mod.constants.ChatType.CHANNEL = "channel"
    mod.error.NetworkError = type("NetworkError", (OSError,), {})
    mod.error.TimedOut = type("TimedOut", (OSError,), {})
    mod.error.BadRequest = type("BadRequest", (Exception,), {})
    for name in ("telegram", "telegram.ext", "telegram.constants", "telegram.request"):
        sys.modules.setdefault(name, mod)
    sys.modules.setdefault("telegram.error", mod.error)


_ensure_telegram_mock()

from gateway.config import PlatformConfig
from plugins.platforms.telegram.adapter import TelegramAdapter


def _adapter():
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="test-token", extra={}))
    adapter._bot = AsyncMock()
    return adapter


def _callback_update(data="sr:p20260812a:0:approve", user_id="8718328058"):
    query = AsyncMock()
    query.data = data
    query.message = MagicMock()
    query.message.chat_id = 8718328058
    query.message.chat.type = "private"
    query.from_user = MagicMock()
    query.from_user.id = user_id
    query.from_user.first_name = "Commander"
    update = MagicMock()
    update.callback_query = query
    return update, query


@pytest.mark.asyncio
async def test_persistent_review_callback_advances_only_after_terminal_action():
    adapter = _adapter()
    flow = MagicMock()
    flow.select.return_value = {"kind": "next"}
    update, query = _callback_update()
    with patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": "8718328058"}, clear=False):
        with patch.object(adapter, "_fft_review_flow", return_value=flow):
            with patch.object(adapter, "_send_fft_review_current", new_callable=AsyncMock) as send_next:
                await adapter._handle_callback_query(update, MagicMock())
    flow.select.assert_called_once_with("p20260812a", 0, "approve", chat_id=8718328058, user_id="8718328058")
    send_next.assert_awaited_once_with("p20260812a", "8718328058")
    query.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_untrusted_persistent_review_callback_fails_closed():
    adapter = _adapter()
    flow = MagicMock()
    update, query = _callback_update(user_id="intruder")
    with patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": "8718328058"}, clear=False):
        with patch.object(adapter, "_fft_review_flow", return_value=flow):
            await adapter._handle_callback_query(update, MagicMock())
    flow.select.assert_not_called()
    assert "not authorized" in query.answer.call_args.kwargs["text"].lower()


@pytest.mark.asyncio
async def test_review_delivery_directive_uses_native_delivery_once():
    adapter = _adapter()
    flow = MagicMock()
    flow.current_delivered.return_value = False
    with patch.object(adapter, "_fft_review_flow", return_value=flow):
        with patch.object(adapter, "_send_fft_review_current", new_callable=AsyncMock) as send_current:
            result = await adapter.send("8718328058", "[[fft_review:p20260812a]]")
    assert result.success
    send_current.assert_awaited_once_with("p20260812a", "8718328058")
