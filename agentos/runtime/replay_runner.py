"""Replay runs from a step without mutating the original run."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentos.runtime.run_helpers import load_events_jsonl, resolve_retry_step
from agentos.runtime.workflow_runner import WorkflowRunner, _append_event, _load_workflow, _run_dir, _write_state


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReplayRunner:
    """
    Creates a new run that preserves the original run's data and re-executes
    from a chosen step. Snapshots from steps before the start step are copied
    into the new run directory so context is preserved for auditing.
    """

    def __init__(self, workflow_runner: WorkflowRunner | None = None) -> None:
        self._runner = workflow_runner or WorkflowRunner()

    def replay(self, origin_run_id: str, from_step_id: str, new_run_id: str | None = None) -> str:
        """
        Build a new run_id that copies prior snapshots and continues execution
        from ``from_step_id``. The original run directory is never modified.
        """
        origin = _run_dir(origin_run_id)
        if not origin.is_dir():
            raise FileNotFoundError(f"Run not found: {origin_run_id}")
        state_path = origin / "state.json"
        if not state_path.is_file():
            raise FileNotFoundError(f"Missing state.json for run {origin_run_id}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        wf_path = Path(state["workflow_path"])
        wf = _load_workflow(wf_path)
        steps: list[dict[str, Any]] = wf.get("steps") or []
        start_idx = next((i for i, s in enumerate(steps) if s.get("id") == from_step_id), -1)
        if start_idx < 0:
            raise ValueError(f"Step id not in workflow: {from_step_id}")

        new_id = new_run_id or str(uuid.uuid4())
        new_root = _run_dir(new_id)
        if new_root.exists():
            raise FileExistsError(f"Run already exists: {new_id}")
        new_root.mkdir(parents=True)
        (new_root / "snapshots").mkdir(exist_ok=True)

        for i in range(start_idx):
            sid = steps[i]["id"]
            src = origin / "snapshots" / f"{sid}.json"
            if src.is_file():
                shutil.copy2(src, new_root / "snapshots" / f"{sid}.json")

        _write_state(
            new_id,
            {
                "run_id": new_id,
                "workflow_path": str(wf_path),
                "workflow_name": wf.get("name", wf_path.stem),
                "status": "running",
                "current_step_index": start_idx,
                "pending_step_id": None,
                "step_count": len(steps),
                "started_at": _utc_now(),
                "replay_of": origin_run_id,
                "replay_from_step": from_step_id,
            },
        )
        _append_event(
            new_id,
            {
                "type": "replay_started",
                "origin_run_id": origin_run_id,
                "from_step": from_step_id,
            },
        )

        self._runner.continue_from(new_id, wf_path, from_index=start_idx)
        return new_id

    def retry_after_failure(
        self,
        origin_run_id: str,
        from_step_id: str | None = None,
        new_run_id: str | None = None,
    ) -> str:
        """
        Create a new run that replays from the failed step (or explicit step).

        If ``from_step_id`` is omitted, the step is inferred from events and state.
        """
        origin = _run_dir(origin_run_id)
        if not origin.is_dir():
            raise FileNotFoundError(f"Run not found: {origin_run_id}")
        state_path = origin / "state.json"
        if not state_path.is_file():
            raise FileNotFoundError(f"Missing state.json for run {origin_run_id}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if from_step_id:
            return self.replay(origin_run_id, from_step_id, new_run_id=new_run_id)
        events = load_events_jsonl(origin / "events.jsonl")
        resolved = resolve_retry_step(events, state)
        if not resolved:
            raise ValueError(
                "Could not resolve a step to retry; pass from_step explicitly.",
            )
        return self.replay(origin_run_id, resolved, new_run_id=new_run_id)
