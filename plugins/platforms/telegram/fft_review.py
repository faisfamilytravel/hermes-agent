"""FFT persistent Commander script-review bridge.

Built under order 171140R AUG26 (walls 1+3); amended under order 171245R
AUG26 (Build 2): HOLD retired by Commander ruling, REJECT added with a
replacement-authoring chain, plain-reply revision binding, and
out-of-order item delivery.

This module owns NO Telegram credentials and NEVER renders, publishes,
schedules, uploads, or spends. Approval authorizes stockpile custody only;
rejection commissions AUTHORING ONLY, per the FFT Script Review README.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

STATE_ROOT = Path("/Users/rfais370/.hermes/shared/fft-content-production/script-stockpile")
LOCATIONS_HELPER = Path("/Users/rfais370/.hermes/shared/fft_locations.py")
REVIEW_BOARD = "fft-script-pipeline-recurring"

MARKER_RE = re.compile(r"\[\[fft_review:([A-Za-z0-9._-]+)\]\]")
SR_RE = re.compile(r"^\s*SR\s+([A-Za-z0-9._-]+)\s+([A-Za-z0-9]+)\s*:\s*(.+)$", re.S)

CHUNK = 3500  # Telegram hard limit is 4096 chars; leave headroom.

_flow_mod = None
_desktop_root: Optional[str] = None


def _module():
    global _flow_mod
    if _flow_mod is None:
        spec = importlib.util.spec_from_file_location(
            "fft_review_flow_runtime", STATE_ROOT / "review_flow.py"
        )
        mod = importlib.util.module_from_spec(spec)
        if str(STATE_ROOT) not in sys.path:
            sys.path.insert(0, str(STATE_ROOT))
        spec.loader.exec_module(mod)
        _flow_mod = mod
    return _flow_mod


def review_error():
    return _module().ReviewFlowError


def _resolve_desktop_root() -> str:
    global _desktop_root
    if _desktop_root is None:
        out = subprocess.run(
            [sys.executable, str(LOCATIONS_HELPER), "script_review"],
            capture_output=True, text=True, timeout=20,
        )
        path = (out.stdout or "").strip()
        if not path:
            raise RuntimeError(
                f"fft_locations.py script_review returned nothing: {out.stderr[:200]}"
            )
        _desktop_root = path
    return _desktop_root


def get_flow(state_root: Optional[Path] = None, desktop_root: Optional[str] = None):
    mod = _module()
    return mod.ReviewFlow(
        desktop_root or _resolve_desktop_root(),
        state_root or STATE_ROOT,
    )


def match_marker(text: str) -> Optional[str]:
    # Search, not match: cron delivery prefixes "[Cron delivery: <job>]\n".
    m = MARKER_RE.search(text or "")
    return m.group(1) if m else None


def match_sr(text: str):
    m = SR_RE.match(text or "")
    return (m.group(1), m.group(2), m.group(3).strip()) if m else None


def record_event(packet_id: str, event: dict[str, Any], flow=None) -> None:
    flow = flow or get_flow()
    state = flow._load(packet_id)
    event = dict(event)
    event.setdefault("at", datetime.now(timezone.utc).isoformat())
    state.setdefault("events", []).append(event)
    flow._write(state)


def chunk_text(text: str) -> list[str]:
    if len(text) <= CHUNK:
        return [text]
    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= CHUNK:
            parts.append(remaining)
            break
        cut = remaining.rfind("\n", 0, CHUNK)
        if cut < CHUNK // 2:
            cut = CHUNK
        parts.append(remaining[:cut])
        remaining = remaining[cut:]
    return parts


def keyboard_rows(packet_id: str, index: int) -> list[list[dict]]:
    """APPROVE / REVISE / REJECT (HOLD retired, order 171245R)."""
    return [[
        {"text": "APPROVE", "callback_data": f"sr:{packet_id}:{index}:approve"},
        {"text": "REVISE", "callback_data": f"sr:{packet_id}:{index}:revise"},
        {"text": "REJECT", "callback_data": f"sr:{packet_id}:{index}:reject"},
    ]]


def first_pending_index(state: dict) -> Optional[int]:
    for i, item in enumerate(state.get("items", [])):
        if item.get("status") == "PENDING":
            return i
    return None


def blocking_index(state: dict) -> Optional[int]:
    """STRICT ONE AT A TIME (Commander ruling, order 171431R Stage A).

    Returns the index of the script currently IN FRONT of the Commander:
    a PENDING item already delivered, or an item AWAITING_INSTRUCTIONS
    (REVISE holds the slot). While this returns a value, NO other script
    may be delivered. Enforced in code at both delivery paths.
    """
    for i, item in enumerate(state.get("items", [])):
        if item.get("status") == "AWAITING_INSTRUCTIONS":
            return i
        if item.get("status") == "PENDING" and item.get("delivered_at"):
            return i
    return None


def formats_approved(state: dict) -> dict:
    out = {}
    for item in state.get("items", []):
        if item.get("disposition") == "approve":
            out[item.get("format")] = item.get("script_id")
    return out


def packet_close_text(state: dict) -> Optional[str]:
    """ONE closing message once one carousel and one reel are approved."""
    ap = formats_approved(state)
    if "carousel" in ap and "reel" in ap:
        return (f"FFT review packet complete.\n"
                f"Approved carousel: {ap['carousel']}\n"
                f"Approved reel: {ap['reel']}\n"
                "Both slots hold Commander-approved scripts. Packet closed.")
    return None


def render_item(flow, packet_id: str, index: int) -> str:
    """Phone-readable review message (Commander ruling, order 171431R B).

    Copy leads. Header line, slide/beat blocks, one custody line. The
    full script record with hashes, evidence, and governance stays in
    the stockpile file untouched; it just stops being in the message.
    """
    mod = _module()
    state = flow._load(packet_id)
    item = state["items"][index]
    path = Path(item["path"])
    if not path.exists() or mod.sha256(path) != item["sha256"]:
        raise mod.ReviewFlowError("script hash changed; packet must be rebuilt before delivery")
    if str(STATE_ROOT) not in sys.path:
        sys.path.insert(0, str(STATE_ROOT))
    from script_to_package import parse_script
    text = path.read_text(encoding="utf-8")
    parsed = parse_script(text)
    fm = parsed["frontmatter"]
    date_h = fm.get("created_date", state.get("created_date", ""))
    fmt = item["format"].title()
    lines = [f"{date_h} | Slot {item['sequence']:02d} | {fmt} | v{item['version']}", ""]
    if item["format"] == "reel":
        spoken = re.findall(r"^- Spoken:\s*(.*)$", text, re.M)
        copy_blocks = re.findall(r"^- Copy:\s*(.*?)(?=^- |^### |\Z)", text, re.M | re.S)
        beats = re.findall(r"^### (\d+)\.\s*([^\n]*)$", text, re.M)
        visuals = re.findall(r"^- Visual:\s*(.*)$", text, re.M)
        for i, (num, head) in enumerate(beats):
            lines.append(f"{num}. {head.strip()}")
            if i < len(spoken):
                lines.append(f"Spoken: {spoken[i]}")
            if i < len(copy_blocks):
                oneline = " / ".join(
                    l.strip() for l in copy_blocks[i].strip().splitlines() if l.strip())
                lines.append(f"On screen: {oneline}")
            if i < len(visuals):
                lines.append(f"(visual: {visuals[i]})")
            lines.append("")
    else:
        for s_ in parsed["slides"]:
            lines.append(f"{s_['slide']}. {s_['kicker']}")
            lines.append(s_["title"])
            if s_["support"]:
                lines.append(s_["support"])
            if s_["takeaway"]:
                lines.append(f"Takeaway: {s_['takeaway']}")
            if s_.get("visual"):
                lines.append(f"(visual: {s_['visual']})")
            lines.append("")
    if parsed.get("cta"):
        lines.append(f"CTA: {parsed['cta']}")
        lines.append("")
    lines.append("Approval is stockpile custody only. Nothing renders or publishes.")
    return "\n".join(lines)


def mark_item_delivered(flow, packet_id: str, index: int,
                        message_id: Optional[str],
                        chunk_ids: Optional[list] = None) -> None:
    """Delivery markers for an arbitrary index (packet-record write)."""
    state = flow._load(packet_id)
    item = state["items"][index]
    item["delivered_at"] = _module().now_utc()
    item["telegram_message_id"] = str(message_id) if message_id is not None else None
    if chunk_ids:
        item["telegram_chunk_ids"] = [str(c) for c in chunk_ids]
    flow._write(state)


def standalone_deliver(packet_id: str, token: str, chat_id: str,
                       index: Optional[int] = None) -> dict:
    """Deliver one PENDING script via raw Bot API HTTPS (out-of-gateway path).

    delivered_at/tg_msg_id are set only on a confirmed send; failures are
    recorded as packet events and never marked delivered.
    """
    flow = get_flow()
    try:
        extend_packet_with_replacements(flow, packet_id)
    except Exception:
        pass
    state = flow._load(packet_id)
    # STRICT ONE AT A TIME (171431R): while a script is in front of the
    # Commander, nothing else is delivered, on any path, any index.
    blk = blocking_index(state)
    if index is None:
        index = first_pending_index(state)
    if blk is not None and index != blk:
        return {"success": True, "message_id": None,
                "held": f"one-at-a-time: item {blk} is in front of the Commander"}
    if index is None:
        out = _post_message(token, chat_id, completion_summary(flow, packet_id))
        return {"success": bool(out.get("ok")),
                "message_id": str(out.get("result", {}).get("message_id"))}
    item = state["items"][index]
    if item.get("status") != "PENDING" or item.get("delivered_at"):
        return {"success": True, "message_id": None}

    text = render_item(flow, packet_id, index)
    chunks = chunk_text(text)
    ids: list = []
    try:
        for i, part in enumerate(chunks):
            payload: dict[str, Any] = {"chat_id": int(chat_id), "text": part}
            if i == len(chunks) - 1:
                payload["reply_markup"] = {"inline_keyboard": keyboard_rows(packet_id, index)}
            out = _post_message_raw(token, payload)
            if not out.get("ok"):
                raise RuntimeError(f"Telegram sendMessage not ok: {str(out)[:200]}")
            ids.append(out.get("result", {}).get("message_id"))
    except Exception as exc:
        try:
            record_event(packet_id, {
                "action": "send_failed",
                "script_id": item.get("script_id"),
                "error": str(exc)[:300],
            }, flow=flow)
        except Exception:
            pass
        return {"error": f"fft_review standalone delivery failed: {exc}"}
    kb_echo = bool((out.get("result") or {}).get("reply_markup"))
    record_event(packet_id, {"action": "delivered", "script_id": item.get("script_id"),
                             "message_id": str(ids[-1]) if ids else None,
                             "keyboard_rendered_api_echo": kb_echo}, flow=flow)
    mark_item_delivered(flow, packet_id, index, ids[-1] if ids else None, ids)
    return {"success": True, "message_id": str(ids[-1]) if ids else None,
            "keyboard_rendered_api_echo": kb_echo}


def _post_message_raw(token: str, payload: dict) -> dict:
    import urllib.request
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_message(token: str, chat_id: str, text: str) -> dict:
    return _post_message_raw(token, {"chat_id": int(chat_id), "text": text})


def find_reply_binding(replied_msg_id, state_root: Optional[Path] = None):
    """Bind a plain Telegram reply to an AWAITING_INSTRUCTIONS item.

    Matches the replied-to message id against each item's recorded
    telegram_message_id / telegram_chunk_ids. Returns
    (packet_id, index, revision_token) or None.
    """
    if replied_msg_id is None:
        return None
    rid = str(replied_msg_id)
    root = Path(state_root or STATE_ROOT) / "review-ux" / "packets"
    for path in sorted(glob.glob(str(root / "*.json"))):
        try:
            state = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        for i, item in enumerate(state.get("items", [])):
            ids = set(item.get("telegram_chunk_ids") or [])
            if item.get("telegram_message_id"):
                ids.add(str(item["telegram_message_id"]))
            if rid in ids and item.get("status") == "AWAITING_INSTRUCTIONS" \
                    and item.get("revision_token"):
                return (state["packet_id"], i, item["revision_token"])
            if rid in ids and item.get("awaiting_rejection_reason"):
                return (state["packet_id"], i, "__REASON__")
    return None


def create_replacement_card(item: dict, created_date: str, packet_time: str, reason: str = "") -> str:
    """Commission an S-9 replacement script for a rejected slot.

    Routing: a Kanban card on the recurring pipeline board, claimed and
    spawned by the Mission Control in-gateway dispatcher — the same path
    every pipeline tasking rides (BOARD-FIRST doctrine). AUTHORING ONLY.
    """
    import os
    from hermes_cli import kanban_db as kb
    os.environ.setdefault("HERMES_KANBAN_BOARD", REVIEW_BOARD)
    seq = int(item["sequence"])
    title = (f"FFT {packet_time} {created_date} S-9 REPLACEMENT for rejected "
             f"slot {seq:02d} ({item['script_id']})")
    if not (reason or "").strip():
        raise RuntimeError(
            "rejection reason is REQUIRED authoring input; replacement not commissioned")
    body = (
        f"COMMANDER REJECTION REASON, verbatim, REQUIRED INPUT:\n{reason.strip()}\n\n"
        f"COMMANDER REJECTED {item['script_id']} v{item['version']} in review. "
        f"Author a REPLACEMENT script for created_date {created_date}, "
        f"sequence {seq:02d}, packet {packet_time}, format {item['format']}.\n"
        "Load and follow recurring-content-pipeline-operations. Use "
        "stockpile.py create with the same gates as the original (novelty "
        "audit against the manifest, evidence citations, COMMANDER_REVIEW "
        "state). The rejected record remains RETIRED history; do not touch it.\n"
        "AUTHORING ONLY: no rendering, scheduling, upload, publication, or "
        "spend. The replacement is delivered for Commander review by the "
        "review bridge once it reaches COMMANDER_REVIEW.\n"
        "Authority: Commander REJECT ruling via Telegram review, order "
        "171245R AUG26 chain."
    )
    with kb.connect_closing() as conn:
        task = kb.create_task(
            conn, title=title, body=body, assignee="s9",
            created_by="fft-review-bridge",
            tenant="fft-content-production",
            workspace_kind="dir",
            workspace_path=str(STATE_ROOT),
            skills=["recurring-content-pipeline-operations"],
        )
    tid = task["id"] if isinstance(task, dict) else str(task)
    return tid


def extend_packet_with_replacements(flow, packet_id: str) -> list[int]:
    """Append COMMANDER_REVIEW replacement records for REJECTED slots.

    A replacement (same created_date + sequence, new record) authored after
    a rejection queues as a fresh PENDING item, so the normal delivery flow
    sends it with APPROVE/REVISE/REJECT. Returns new item indexes.
    """
    mod = _module()
    state = flow._load(packet_id)
    rejected_seqs = {int(i["sequence"]) for i in state.get("items", [])
                     if i.get("disposition") == "REJECTED"}
    if not rejected_seqs:
        return []
    # A replacement may be a NEW record or a VERSION BUMP of the rejected
    # script_id (stockpile create for the same slot bumps version) — proven
    # live 17 AUG: rejected v1 was replaced by v2 under the same id.
    known_ids = {(i["script_id"], int(i.get("version", 0)))
                 for i in state.get("items", [])}
    stockpile = mod.Stockpile(flow.desktop_root, flow.state_root)
    manifest = stockpile._load_manifest()
    added: list[int] = []
    for record in manifest.get("records", []):
        if (record.get("created_date") == state.get("created_date")
                and record.get("packet_time_et") == (
                    state.get("packet_time_et") or state.get("packet_time"))
                and int(record.get("sequence", -1)) in rejected_seqs
                and record.get("state") == "COMMANDER_REVIEW"
                and (record.get("script_id"), int(record.get("version", 0))) not in known_ids):
            state["items"].append({
                "script_id": record["script_id"],
                "sequence": int(record["sequence"]),
                "format": record["format"], "version": int(record["version"]),
                "sha256": record["sha256"], "path": record["path"],
                "status": "PENDING",
                "replacement_for": next(
                    (i["script_id"] for i in state["items"]
                     if i.get("disposition") == "REJECTED"
                     and int(i["sequence"]) == int(record["sequence"])), None),
            })
            added.append(len(state["items"]) - 1)
    if added:
        state.setdefault("events", []).append({
            "at": mod.now_utc(), "action": "replacement_queued",
            "count": len(added),
        })
        unresolved = [i for i, it in enumerate(state["items"])
                      if it.get("status") != "RESOLVED"]
        state["current_index"] = unresolved[0] if unresolved else len(state["items"])
        if state.get("status") == "COMPLETE":
            state["status"] = "ACTIVE"
        flow._write(state)
    return added


def live_bindable_ids(state_root: Optional[Path] = None):
    """(message_id, format) pairs for items awaiting instructions."""
    out = []
    root = Path(state_root or STATE_ROOT) / "review-ux" / "packets"
    for path in sorted(glob.glob(str(root / "*.json"))):
        try:
            st = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in st.get("items", []):
            live = (item.get("status") == "AWAITING_INSTRUCTIONS"
                    or (item.get("status") == "PENDING" and item.get("delivered_at")))
            if live:
                ids = item.get("telegram_chunk_ids") or []
                mid = ids[-1] if ids else item.get("telegram_message_id")
                if mid:
                    out.append((str(mid), item.get("format", "script")))
    return out


def completion_summary(flow, packet_id: str) -> str:
    state = flow._load(packet_id)
    close = packet_close_text(state)
    if close:
        return close
    lines = [f"FFT Commander Review complete: {packet_id}"]
    for item in state.get("items", []):
        lines.append(
            f"  {item.get('script_id')} v{item.get('version')}: "
            f"{item.get('disposition') or item.get('status')}"
        )
    lines.append("Stockpile custody only. Nothing was rendered or published.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# RETIRED 171245R AUG26 by Commander ruling: HOLD created a backlog that
# never resolves. The handler below is retired in place per FFT convention
# (labeled, not deleted). Existing recorded HOLD events remain history.
# def record_hold(packet_id, index, by):
#     record_event(packet_id, {"action": "hold", "index": index, "by": by})
# ---------------------------------------------------------------------------


def bind_rejection_reason(packet_id: str, index: int, reason: str) -> str:
    """Order 171745R Stage C: reason is durable, bound, and gates authoring."""
    if not reason.strip():
        raise RuntimeError("empty rejection reason")
    flow = get_flow()
    state = flow._load(packet_id)
    item = state["items"][index]
    item["rejection_reason"] = reason.strip()
    item.pop("awaiting_rejection_reason", None)
    state.setdefault("events", []).append({
        "at": _module().now_utc(), "action": "rejection_reason_bound",
        "script_id": item["script_id"], "version": item["version"],
        "reason_verbatim": reason.strip(),
    })
    flow._write(state)
    return create_replacement_card(
        item, state.get("created_date"),
        state.get("packet_time_et") or state.get("packet_time"),
        reason=reason.strip(),
    )
