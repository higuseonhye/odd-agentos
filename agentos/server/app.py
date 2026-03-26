"""Flask HTTP API for AgentOS (dashboard + automation)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

from agentos.config import settings
from agentos.runtime.policy_engine import PolicyEngine, StepContext
from agentos.runtime.reliability_card import ReliabilityCardGenerator
from agentos.runtime.replay_runner import ReplayRunner
from agentos.runtime.system_mri import FailureAnalyzer
from agentos.runtime.workflow_runner import WorkflowRunner, _run_dir
from agentos.server.logging_config import configure_logging

log = logging.getLogger(__name__)


def _apply_cors(app: Flask) -> None:
    """CORS: permissive in development; production relies on same-origin proxy unless configured."""
    if settings.CORS_ORIGINS is not None:
        origins: str | list[str] = settings.CORS_ORIGINS
    elif settings.IS_PRODUCTION:
        return
    else:
        origins = "*"
    CORS(app, resources={r"/api/*": {"origins": origins}})


def _build_step_timeline(
    state: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive per-step status for the dashboard from workflow + events."""
    wf_path = state.get("workflow_path")
    if not wf_path:
        return []
    try:
        from agentos.runtime.workflow_runner import _load_workflow

        wf = _load_workflow(Path(wf_path))
    except OSError:
        return []
    raw_steps: list[dict[str, Any]] = wf.get("steps") or []
    status: dict[str, str] = {}
    detail: dict[str, dict[str, Any]] = {}
    for e in events:
        t = e.get("type")
        sid = e.get("step_id")
        if not isinstance(sid, str):
            continue
        if t == "step_started":
            status[sid] = "running"
        elif t == "step_completed":
            status[sid] = "completed"
            detail[sid] = {"output": e.get("output")}
        elif t == "step_failed":
            status[sid] = "failed"
            detail[sid] = {"error": e.get("error")}
        elif t == "step_pending_approval":
            status[sid] = "pending_approval"
        elif t == "policy_violation" and sid:
            status[sid] = "policy_blocked"
            detail[sid] = {"reason": e.get("reason"), "rule_id": e.get("rule_id")}
    out: list[dict[str, Any]] = []
    for s in raw_steps:
        sid = s.get("id")
        if not sid:
            continue
        st = status.get(sid, "pending")
        out.append(
            {
                "id": sid,
                "agent": s.get("agent"),
                "status": st,
                "requires_approval": bool(s.get("requires_approval")),
                "detail": detail.get(sid),
            },
        )
    return out


def _suggest_fix(pattern: str) -> str:
    pl = pattern.lower()
    if "rate" in pl or "limit" in pl:
        return "Add exponential backoff and reduce concurrency."
    if "policy" in pl:
        return "Review YAML policies and agent tags."
    if "approval" in pl:
        return "Review risk levels and approval UX."
    return "Inspect events.jsonl and run System MRI diagnose."


def create_app() -> Flask:
    configure_logging()
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    _apply_cors(app)

    runner = WorkflowRunner()
    replay = ReplayRunner(runner)
    policy_engine = PolicyEngine(settings.POLICY_PATH)

    @app.get("/api/health")
    def health() -> Any:
        return jsonify({"status": "ok", "env": settings.AGENTOS_ENV})

    @app.get("/api/runs")
    def list_runs() -> Any:
        base = settings.RUNS_DIR
        if not base.is_dir():
            return jsonify([])
        rows: list[dict[str, Any]] = []
        for rd in sorted(base.iterdir(), key=lambda p: p.name, reverse=True):
            if not rd.is_dir():
                continue
            sp = rd / "state.json"
            if not sp.is_file():
                continue
            st = json.loads(sp.read_text(encoding="utf-8"))
            rows.append(
                {
                    "run_id": st.get("run_id", rd.name),
                    "status": st.get("status"),
                    "workflow_name": st.get("workflow_name"),
                    "started_at": st.get("started_at"),
                    "step_count": st.get("step_count"),
                    "project": settings.AGENTOS_TENANT_ID,
                },
            )
        return jsonify(rows)

    @app.get("/api/runs/<run_id>")
    def get_run(run_id: str) -> Any:
        p = _run_dir(run_id) / "state.json"
        if not p.is_file():
            return jsonify({"error": "not_found"}), 404
        state = json.loads(p.read_text(encoding="utf-8"))
        events: list[dict[str, Any]] = []
        ep = _run_dir(run_id) / "events.jsonl"
        if ep.is_file():
            for line in ep.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        steps = _build_step_timeline(state, events)
        return jsonify({"state": state, "events": events, "steps": steps})

    @app.post("/api/runs/<run_id>/approve/<step_id>")
    def approve(run_id: str, step_id: str) -> Any:
        st_path = _run_dir(run_id) / "state.json"
        if not st_path.is_file():
            return jsonify({"error": "not_found"}), 404
        st = json.loads(st_path.read_text(encoding="utf-8"))
        if st.get("pending_step_id") != step_id:
            return jsonify({"error": "not_pending", "pending": st.get("pending_step_id")}), 400
        runner.resume_run(run_id, approved=True)
        return jsonify({"ok": True})

    @app.post("/api/runs/<run_id>/deny/<step_id>")
    def deny(run_id: str, step_id: str) -> Any:
        st_path = _run_dir(run_id) / "state.json"
        if not st_path.is_file():
            return jsonify({"error": "not_found"}), 404
        st = json.loads(st_path.read_text(encoding="utf-8"))
        if st.get("pending_step_id") != step_id:
            return jsonify({"error": "not_pending"}), 400
        runner.resume_run(run_id, approved=False)
        return jsonify({"ok": True})

    @app.post("/api/runs/<run_id>/retry")
    def retry(run_id: str) -> Any:
        """
        Retry from failure: new run_id, snapshots preserved, re-execute from failed step.

        Optional JSON body: ``{"from_step": "step_id"}`` to override auto-detection.
        """
        st_path = _run_dir(run_id) / "state.json"
        if not st_path.is_file():
            return jsonify({"error": "not_found"}), 404
        body = request.get_json(silent=True) or {}
        explicit = body.get("from_step")
        try:
            if explicit:
                new_id = replay.replay(run_id, str(explicit))
            else:
                new_id = replay.retry_after_failure(run_id)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except FileNotFoundError:
            return jsonify({"error": "not_found"}), 404
        return jsonify({"run_id": new_id})

    @app.post("/api/runs/<run_id>/replay")
    def replay_run(run_id: str) -> Any:
        body = request.get_json(silent=True) or {}
        from_step = body.get("from_step")
        if not from_step:
            return jsonify({"error": "from_step required"}), 400
        new_id = replay.replay(run_id, str(from_step))
        return jsonify({"run_id": new_id})

    @app.get("/api/policies")
    def get_policies() -> Any:
        p = settings.POLICY_PATH
        if not p.is_file():
            return jsonify({"raw": ""})
        return jsonify({"raw": p.read_text(encoding="utf-8"), "path": str(p)})

    @app.put("/api/policies")
    def put_policies() -> Any:
        body = request.get_json(silent=True) or {}
        raw = body.get("raw")
        if raw is None:
            return jsonify({"error": "raw required"}), 400
        settings.POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
        settings.POLICY_PATH.write_text(str(raw), encoding="utf-8")
        policy_engine.reload()
        return jsonify({"ok": True})

    @app.post("/api/policies/evaluate")
    def evaluate_policy() -> Any:
        """Dry-run policy evaluation for a hypothetical step (dashboard)."""
        body = request.get_json(silent=True) or {}
        s = body.get("step") or {}
        ctx = StepContext(
            step_id=str(s.get("step_id", "dry-run")),
            agent_name=str(s.get("agent_name", "agent")),
            agent_tags=list(s.get("agent_tags") or []),
            risk_level=str(s.get("risk_level", "low")),
            tool_calls_per_minute=int(s.get("tool_calls_per_minute") or 0),
        )
        d = policy_engine.evaluate(ctx)
        return jsonify(
            {
                "action": d.action.value,
                "reason": d.reason,
                "rule_id": d.rule_id,
                "notify": d.notify,
            },
        )

    @app.get("/api/insights/failures")
    def insights_failures() -> Any:
        patterns: dict[str, dict[str, Any]] = {}
        base = settings.RUNS_DIR
        if not base.is_dir():
            return jsonify({"patterns": []})
        for rd in base.iterdir():
            if not rd.is_dir():
                continue
            ev_path = rd / "events.jsonl"
            if not ev_path.is_file():
                continue
            for line in ev_path.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("type") not in ("step_failed", "run_failed"):
                    continue
                key = str(e.get("reason") or e.get("error") or "unknown")
                if key not in patterns:
                    patterns[key] = {"pattern": key, "count": 0, "suggested_fix": _suggest_fix(key)}
                patterns[key]["count"] += 1
        return jsonify({"patterns": list(patterns.values())})

    @app.get("/api/reliability/<path:agent_name>")
    def reliability(agent_name: str) -> Any:
        days = int(request.args.get("days", 30))
        card = ReliabilityCardGenerator(agent_name, days=days).generate()
        return jsonify(card.to_dict())

    @app.get("/api/runs/<run_id>/diagnosis")
    def diagnosis(run_id: str) -> Any:
        rep = FailureAnalyzer(run_id).analyze()
        return jsonify(rep.to_dict())

    @app.post("/api/runs")
    def create_run() -> Any:
        body = request.get_json(silent=True) or {}
        wf = body.get("workflow_path") or body.get("workflow")
        if not wf:
            return jsonify({"error": "workflow_path required"}), 400
        rid = runner.start_run(str(wf))
        return jsonify({"run_id": rid}), 201

    log.info("AgentOS API ready (env=%s)", settings.AGENTOS_ENV)
    return app


# WSGI entry for gunicorn: ``gunicorn 'agentos.server.app:app'``
app = create_app()
