"""Tests for retry step resolution and replay."""

import json
from pathlib import Path

import pytest

from agentos.runtime.replay_runner import ReplayRunner
from agentos.runtime.run_helpers import load_events_jsonl, resolve_retry_step
from agentos.runtime.workflow_runner import WorkflowRunner


def test_resolve_retry_step_failed() -> None:
    events = [
        {"type": "run_started"},
        {"type": "step_failed", "step_id": "a1", "error": "boom"},
    ]
    state = {"status": "failed"}
    assert resolve_retry_step(events, state) == "a1"


def test_resolve_retry_policy() -> None:
    events = [
        {"type": "policy_violation", "step_id": "p1", "reason": "x"},
    ]
    state = {"status": "policy_blocked", "last_failed_step_id": "p1"}
    assert resolve_retry_step(events, state) == "p1"


def test_resolve_fallback_last_failed() -> None:
    events: list[dict] = []
    state = {"status": "failed", "last_failed_step_id": "z9"}
    assert resolve_retry_step(events, state) == "z9"


def test_retry_after_failure_creates_new_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentos.config import settings as st

    monkeypatch.setattr(st, "RUNS_DIR", tmp_path)
    wf = tmp_path / "w.yaml"
    wf.write_text(
        """
name: t
steps:
  - id: s1
    agent: a
    input: "x"
    requires_approval: false
""",
        encoding="utf-8",
    )
    rid = WorkflowRunner().start_run(wf)
    rd = tmp_path / rid
    assert (rd / "state.json").is_file()

    # Force a failed run state for retry resolution
    st_json = json.loads((rd / "state.json").read_text(encoding="utf-8"))
    st_json["status"] = "failed"
    st_json["last_failed_step_id"] = "s1"
    (rd / "state.json").write_text(json.dumps(st_json), encoding="utf-8")

    rr = ReplayRunner()
    new_id = rr.retry_after_failure(rid)
    assert new_id != rid
    assert (tmp_path / new_id / "state.json").is_file()


def test_load_events_jsonl_skips_bad_lines(tmp_path: Path) -> None:
    p = tmp_path / "e.jsonl"
    p.write_text('{"type":"a"}\nnot-json\n{"type":"b"}\n', encoding="utf-8")
    ev = load_events_jsonl(p)
    assert len(ev) == 2
