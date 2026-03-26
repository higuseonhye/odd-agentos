"""YAML workflow execution with snapshots, policy checks, and event logging."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agentos.config import settings
from agentos.runtime.policy_engine import PolicyAction, PolicyEngine, StepContext


SCHEMA_VERSION = "1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StepSnapshot:
    """Immutable record of a completed step for replay."""

    step_id: str
    agent_name: str
    input: Any
    output: Any
    timestamp: str
    resolved_vars: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    llm_prompt: str | None = None
    llm_response: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _run_dir(run_id: str) -> Path:
    return settings.RUNS_DIR / run_id


def _append_event(run_id: str, event: dict[str, Any]) -> None:
    rd = _run_dir(run_id)
    rd.mkdir(parents=True, exist_ok=True)
    path = rd / "events.jsonl"
    event = {**event, "schema_version": SCHEMA_VERSION, "tenant_id": settings.AGENTOS_TENANT_ID}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _write_state(run_id: str, state: dict[str, Any]) -> None:
    rd = _run_dir(run_id)
    rd.mkdir(parents=True, exist_ok=True)
    state = {**state, "updated_at": _utc_now()}
    (rd / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def _read_state(run_id: str) -> dict[str, Any] | None:
    p = _run_dir(run_id) / "state.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _load_workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _execute_agent_step(
    agent_name: str,
    inp: Any,
    resolved_vars: dict[str, Any],
) -> tuple[Any, list[dict[str, Any]], str | None, str | None]:
    """Deterministic stub execution (replace with real LLM/tools)."""
    out = f"[{agent_name}] {inp!s}"
    tool_calls: list[dict[str, Any]] = []
    prompt = None
    response = None
    if settings.AGENTOS_LOG_PAYLOADS:
        prompt = f"system: execute {agent_name}\nuser: {inp!s}"
        response = out
    return out, tool_calls, prompt, response


class WorkflowRunner:
    """Runs workflows, writes events.jsonl and per-step snapshots."""

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self.policy = policy_engine or PolicyEngine(settings.POLICY_PATH)

    def start_run(self, workflow_path: str | Path, run_id: str | None = None) -> str:
        """Begin a new run from the first step."""
        rid = run_id or str(uuid.uuid4())
        wf_path = Path(workflow_path).resolve()
        wf = _load_workflow(wf_path)
        steps = wf.get("steps") or []
        _write_state(
            rid,
            {
                "run_id": rid,
                "workflow_path": str(wf_path),
                "workflow_name": wf.get("name", wf_path.stem),
                "status": "running",
                "current_step_index": 0,
                "pending_step_id": None,
                "step_count": len(steps),
                "started_at": _utc_now(),
            },
        )
        _append_event(
            rid,
            {"type": "run_started", "workflow": wf.get("name"), "path": str(wf_path)},
        )
        self._continue_from(rid, wf_path, wf, from_index=0)
        return rid

    def continue_from(
        self,
        run_id: str,
        workflow_path: str | Path,
        from_index: int,
    ) -> None:
        """Resume execution from a step index (used by replay and advanced flows)."""
        wf_path = Path(workflow_path).resolve()
        wf = _load_workflow(wf_path)
        self._continue_from(run_id, wf_path, wf, from_index=from_index)

    def resume_run(self, run_id: str, approved: bool) -> None:
        """Resume after human approval at pending step."""
        st = _read_state(run_id)
        if not st or st.get("status") != "pending_approval":
            return
        wf_path = Path(st["workflow_path"])
        wf = _load_workflow(wf_path)
        idx = int(st["current_step_index"])
        steps = wf.get("steps") or []
        if idx >= len(steps):
            return
        step = steps[idx]
        sid = step["id"]
        if not approved:
            _append_event(
                run_id,
                {"type": "approval_denied", "step_id": sid, "agent": step.get("agent")},
            )
            _write_state(run_id, {**st, "status": "failed", "failure_reason": "approval_denied"})
            _append_event(run_id, {"type": "run_failed", "reason": "approval_denied"})
            return
        _append_event(run_id, {"type": "approval_granted", "step_id": sid})
        self._execute_step_at(run_id, wf_path, wf, idx, step)
        self._continue_from(run_id, wf_path, wf, from_index=idx + 1)

    def _continue_from(
        self,
        run_id: str,
        wf_path: Path,
        wf: dict[str, Any],
        from_index: int,
    ) -> None:
        steps = wf.get("steps") or []
        for i in range(from_index, len(steps)):
            st = _read_state(run_id)
            if st and st.get("status") != "running":
                return
            step = steps[i]
            ctx = StepContext(
                step_id=step["id"],
                agent_name=str(step.get("agent", "unknown")),
                agent_tags=list(step.get("agent_tags") or []),
                risk_level=str(step.get("risk_level", "low")),
                tool_calls_per_minute=0,
            )
            decision = self.policy.evaluate(ctx)
            if decision.action == PolicyAction.DENY:
                _append_event(
                    run_id,
                    {
                        "type": "policy_violation",
                        "rule_id": decision.rule_id,
                        "action": "deny",
                        "reason": decision.reason,
                        "step_id": step["id"],
                    },
                )
                _write_state(
                    run_id,
                    {
                        **(_read_state(run_id) or {}),
                        "status": "policy_blocked",
                        "last_failed_step_id": step["id"],
                    },
                )
                _append_event(run_id, {"type": "run_failed", "reason": "policy_blocked"})
                return
            if decision.action == PolicyAction.PAUSE_AND_ALERT:
                _append_event(
                    run_id,
                    {
                        "type": "policy_pause",
                        "rule_id": decision.rule_id,
                        "reason": decision.reason,
                        "step_id": step["id"],
                    },
                )
                _write_state(
                    run_id,
                    {
                        **(_read_state(run_id) or {}),
                        "status": "paused",
                        "last_failed_step_id": step["id"],
                    },
                )
                return
            needs_approval = bool(step.get("requires_approval")) or decision.action == PolicyAction.REQUIRE_APPROVAL
            if needs_approval:
                cur = _read_state(run_id) or {}
                _write_state(
                    run_id,
                    {
                        **cur,
                        "status": "pending_approval",
                        "current_step_index": i,
                        "pending_step_id": step["id"],
                    },
                )
                _append_event(
                    run_id,
                    {
                        "type": "step_pending_approval",
                        "step_id": step["id"],
                        "agent": step.get("agent"),
                    },
                )
                return
            self._execute_step_at(run_id, wf_path, wf, i, step)

        st = _read_state(run_id) or {}
        _write_state(run_id, {**st, "status": "completed", "current_step_index": len(steps)})
        _append_event(run_id, {"type": "run_completed"})

    def _execute_step_at(
        self,
        run_id: str,
        wf_path: Path,
        wf: dict[str, Any],
        index: int,
        step: dict[str, Any],
    ) -> None:
        sid = step["id"]
        agent = str(step.get("agent", "agent"))
        inp = step.get("input")
        resolved_vars = {"workflow": wf.get("name"), "step_index": index}
        _append_event(
            run_id,
            {"type": "step_started", "step_id": sid, "agent": agent},
        )
        try:
            out, tool_calls, prompt, response = _execute_agent_step(agent, inp, resolved_vars)
        except Exception as e:  # noqa: BLE001
            _append_event(
                run_id,
                {"type": "step_failed", "step_id": sid, "error": str(e)},
            )
            _write_state(
                run_id,
                {
                    **(_read_state(run_id) or {}),
                    "status": "failed",
                    "failure_reason": str(e),
                    "last_failed_step_id": sid,
                },
            )
            _append_event(run_id, {"type": "run_failed", "reason": str(e)})
            return

        snap = StepSnapshot(
            step_id=sid,
            agent_name=agent,
            input=inp,
            output=out,
            timestamp=_utc_now(),
            resolved_vars=resolved_vars,
            tool_calls=tool_calls,
            llm_prompt=prompt,
            llm_response=response,
        )
        snap_dir = _run_dir(run_id) / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap_path = snap_dir / f"{sid}.json"
        if not snap_path.exists():
            snap_path.write_text(
                json.dumps(snap.to_json_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        _append_event(
            run_id,
            {"type": "step_completed", "step_id": sid, "agent": agent, "output": out},
        )
        cur = _read_state(run_id) or {}
        _write_state(
            run_id,
            {
                **cur,
                "current_step_index": index + 1,
                "pending_step_id": None,
                "status": "running",
            },
        )
