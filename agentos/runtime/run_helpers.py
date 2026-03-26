"""Helpers for resolving retry/replay step ids from run state and events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_events_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse events.jsonl into a list of dicts (invalid lines skipped)."""
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def resolve_retry_step(events: list[dict[str, Any]], state: dict[str, Any]) -> str | None:
    """
    Pick the workflow step id to re-execute after a failure.

    Prefers the most recent terminal failure (step_failed, policy block, denial).
    Falls back to ``pending_step_id`` when the run is waiting on approval.
    """
    status = str(state.get("status") or "")

    for e in reversed(events):
        t = e.get("type")
        sid = e.get("step_id")
        if not isinstance(sid, str):
            continue
        if t == "step_failed":
            return sid
        if t == "policy_violation":
            return sid
        if t == "approval_denied":
            return sid
        if t == "policy_pause":
            return sid

    if status == "pending_approval":
        ps = state.get("pending_step_id")
        return str(ps) if ps else None

    lf = state.get("last_failed_step_id")
    if isinstance(lf, str) and lf:
        return lf

    return None
