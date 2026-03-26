#!/usr/bin/env python3
"""
Demo seed: writes 12 realistic runs under RUNS_DIR (offline, no OpenAI).

Mix: 4 completed + 1 replay child (completed) + 3 failed (with diagnosis.json)
     + 2 pending_approval + 2 policy_blocked = 12 runs (IDs seed-01 … seed-12).

Usage:
  python scripts/seed_demo.py
  python scripts/seed_demo.py --force
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentos.config import settings  # noqa: E402

SCHEMA_VERSION = "1.0"


def _ev(payload: dict) -> dict:
    return {
        **payload,
        "schema_version": SCHEMA_VERSION,
        "tenant_id": settings.AGENTOS_TENANT_ID,
    }


def _wf(name: str) -> str:
    return str((ROOT / "workflows" / name).resolve())


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _write_state(rd: Path, state: dict) -> None:
    state = {**state, "updated_at": _iso(datetime.now(timezone.utc))}
    (rd / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def _write_events(rd: Path, events: list[dict]) -> None:
    lines = [json.dumps(_ev(e), ensure_ascii=False) for e in events]
    (rd / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_diagnosis(rd: Path, payload: dict) -> None:
    (rd / "diagnosis.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _snapshot(
    step_id: str,
    agent_name: str,
    inp: str,
    out: str,
    ts: str,
    *,
    workflow: str,
    step_index: int,
) -> dict:
    return {
        "step_id": step_id,
        "agent_name": agent_name,
        "input": inp,
        "output": out,
        "timestamp": ts,
        "resolved_vars": {"workflow": workflow, "step_index": step_index},
        "tool_calls": [],
        "llm_prompt": None,
        "llm_response": None,
    }


def _clear_seed_runs() -> None:
    base = settings.RUNS_DIR
    if not base.is_dir():
        return
    for rd in base.iterdir():
        if rd.is_dir() and rd.name.startswith("seed-"):
            shutil.rmtree(rd)


def _run_dir(run_id: str) -> Path:
    return settings.RUNS_DIR / run_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed 12 demo runs (seed-01 … seed-12).")
    parser.add_argument("--force", action="store_true", help="Remove existing seed-* runs first.")
    args = parser.parse_args()

    if args.force:
        _clear_seed_runs()

    now = datetime.now(timezone.utc)
    # Spread started_at across the last 7 days (deterministic offsets)
    offsets_hours = [168, 150, 132, 114, 96, 78, 60, 48, 36, 24, 12, 3]

    wf_fin = _wf("financial_report.yaml")
    wf_cs = _wf("customer_support.yaml")
    wf_comp = _wf("compliance_check.yaml")
    wf_pipe = _wf("data_pipeline_agent.yaml")

    # --- seed-01: financial_report completed ---
    rid = "seed-01"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[0]))
        events = [
            {"type": "run_started", "workflow": "financial_report", "path": wf_fin},
            {"type": "step_started", "step_id": "fetch_data", "agent": "data-fetcher"},
            {
                "type": "step_completed",
                "step_id": "fetch_data",
                "agent": "data-fetcher",
                "output": "Consolidated 1.2M postings; latency p95 840ms",
            },
            {"type": "step_pending_approval", "step_id": "analyze_risk", "agent": "financial-analyst"},
            {"type": "approval_granted", "step_id": "analyze_risk"},
            {"type": "step_started", "step_id": "analyze_risk", "agent": "financial-analyst"},
            {
                "type": "step_completed",
                "step_id": "analyze_risk",
                "agent": "financial-analyst",
                "output": "Top breach: vendor X at 94% of limit; VaR breakeven +12bps",
            },
            {"type": "step_started", "step_id": "send_report", "agent": "report-sender"},
            {
                "type": "step_completed",
                "step_id": "send_report",
                "agent": "report-sender",
                "output": "Uploaded to SharePoint /Finance/Q4-2025; checksum SHA-256 verified",
            },
            {"type": "run_completed"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_fin,
                "workflow_name": "financial_report",
                "status": "completed",
                "current_step_index": 3,
                "pending_step_id": None,
                "step_count": 3,
                "started_at": t0,
            },
        )
        print(f"wrote {rid}")

    # --- seed-02: customer_support completed ---
    rid = "seed-02"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[1]))
        events = [
            {"type": "run_started", "workflow": "customer_support", "path": wf_cs},
            {"type": "step_started", "step_id": "classify_ticket", "agent": "ticket-classifier"},
            {
                "type": "step_completed",
                "step_id": "classify_ticket",
                "agent": "ticket-classifier",
                "output": "intent=billing_dispute priority=P2 locale=en-US",
            },
            {"type": "step_started", "step_id": "resolve_ticket", "agent": "support-resolver"},
            {
                "type": "step_completed",
                "step_id": "resolve_ticket",
                "agent": "support-resolver",
                "output": "Issued partial credit $47.20; SLA reply in 4h 12m",
            },
            {"type": "run_completed"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_cs,
                "workflow_name": "customer_support",
                "status": "completed",
                "current_step_index": 2,
                "pending_step_id": None,
                "step_count": 2,
                "started_at": t0,
            },
        )
        print(f"wrote {rid}")

    # --- seed-03: compliance_check completed ---
    rid = "seed-03"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[2]))
        events = [
            {"type": "run_started", "workflow": "compliance_check", "path": wf_comp},
            {"type": "step_started", "step_id": "scan_docs", "agent": "doc-scanner"},
            {
                "type": "step_completed",
                "step_id": "scan_docs",
                "agent": "doc-scanner",
                "output": "Indexed 38 contracts; 14 contain DPA addenda",
            },
            {"type": "step_pending_approval", "step_id": "flag_violations", "agent": "compliance-checker"},
            {"type": "approval_granted", "step_id": "flag_violations"},
            {"type": "step_started", "step_id": "flag_violations", "agent": "compliance-checker"},
            {
                "type": "step_completed",
                "step_id": "flag_violations",
                "agent": "compliance-checker",
                "output": "3 findings: subprocessors table stale (2 vendors), Art.17 window 8d over SLA",
            },
            {"type": "step_started", "step_id": "generate_report", "agent": "report-generator"},
            {
                "type": "step_completed",
                "step_id": "generate_report",
                "agent": "report-generator",
                "output": "Markdown audit pack v4 with evidence hashes",
            },
            {"type": "step_started", "step_id": "notify_team", "agent": "notifier"},
            {
                "type": "step_completed",
                "step_id": "notify_team",
                "agent": "notifier",
                "output": "Posted to Slack #compliance-alerts; email digest to dpo@company.com",
            },
            {"type": "run_completed"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_comp,
                "workflow_name": "compliance_check",
                "status": "completed",
                "current_step_index": 4,
                "pending_step_id": None,
                "step_count": 4,
                "started_at": t0,
            },
        )
        print(f"wrote {rid}")

    # --- seed-04: data_pipeline completed ---
    rid = "seed-04"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[3]))
        events = [
            {"type": "run_started", "workflow": "data_pipeline", "path": wf_pipe},
            {"type": "step_started", "step_id": "extract", "agent": "data-pipeline"},
            {
                "type": "step_completed",
                "step_id": "extract",
                "agent": "data-pipeline",
                "output": "Snowflake export: 842,019 rows, watermark 2025-03-24T06:00:00Z",
            },
            {"type": "step_started", "step_id": "transform", "agent": "data-pipeline"},
            {
                "type": "step_completed",
                "step_id": "transform",
                "agent": "data-pipeline",
                "output": "Schema v12 applied; 812 dupes merged; null-safe casts on revenue_usd",
            },
            {"type": "step_started", "step_id": "load", "agent": "data-pipeline"},
            {
                "type": "step_completed",
                "step_id": "load",
                "agent": "data-pipeline",
                "output": "Staging DWH.FACT_REVENUE_DAILY: MERGE 812k rows, 0 rejects",
            },
            {"type": "run_completed"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_pipe,
                "workflow_name": "data_pipeline",
                "status": "completed",
                "current_step_index": 3,
                "pending_step_id": None,
                "step_count": 3,
                "started_at": t0,
            },
        )
        print(f"wrote {rid}")

    # --- seed-05: failed parent (retry source) — transform timeout ---
    rid = "seed-05"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[4]))
        ext_out = "Parquet staging 812k rows; ready for transform"
        snap_ts = _iso(now - timedelta(hours=offsets_hours[4]) + timedelta(seconds=5))
        snap = _snapshot(
            "extract",
            "data-pipeline",
            "Extract raw rows from source connector",
            ext_out,
            snap_ts,
            workflow="data_pipeline",
            step_index=0,
        )
        (rd / "snapshots").mkdir(exist_ok=True)
        (rd / "snapshots" / "extract.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")
        events = [
            {"type": "run_started", "workflow": "data_pipeline", "path": wf_pipe},
            {"type": "step_started", "step_id": "extract", "agent": "data-pipeline"},
            {
                "type": "step_completed",
                "step_id": "extract",
                "agent": "data-pipeline",
                "output": ext_out,
            },
            {"type": "step_started", "step_id": "transform", "agent": "data-pipeline"},
            {
                "type": "step_failed",
                "step_id": "transform",
                "error": "Step timed out after 300s waiting for Spark job data-pipeline-tx-4821",
            },
            {
                "type": "run_failed",
                "reason": "Step timed out after 300s waiting for Spark job data-pipeline-tx-4821",
            },
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_pipe,
                "workflow_name": "data_pipeline",
                "status": "failed",
                "current_step_index": 1,
                "pending_step_id": None,
                "step_count": 3,
                "started_at": t0,
                "failure_reason": "Step timed out after 300s waiting for Spark job data-pipeline-tx-4821",
                "last_failed_step_id": "transform",
            },
        )
        _write_diagnosis(
            rd,
            {
                "run_id": rid,
                "failure_type": "timeout",
                "root_cause": "A step exceeded its allowed execution time.",
                "affected_steps": ["extract", "transform"],
                "suggested_fixes": [
                    "Increase step timeout",
                    "Optimize slow tools or LLM calls",
                ],
                "confidence": 0.75,
                "generated_at": _iso(now),
            },
        )
        print(f"wrote {rid}")

    # --- seed-06: failed — API 429 ---
    rid = "seed-06"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[5]))
        events = [
            {"type": "run_started", "workflow": "customer_support", "path": wf_cs},
            {"type": "step_started", "step_id": "classify_ticket", "agent": "ticket-classifier"},
            {
                "type": "step_failed",
                "step_id": "classify_ticket",
                "error": "CRM API 429 Too Many Requests: retry-after=28s trace=crm-9f3a",
            },
            {"type": "run_failed", "reason": "CRM API 429 Too Many Requests: retry-after=28s trace=crm-9f3a"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_cs,
                "workflow_name": "customer_support",
                "status": "failed",
                "current_step_index": 0,
                "failure_reason": "CRM API 429 Too Many Requests: retry-after=28s trace=crm-9f3a",
                "last_failed_step_id": "classify_ticket",
                "step_count": 2,
                "started_at": t0,
            },
        )
        _write_diagnosis(
            rd,
            {
                "run_id": rid,
                "failure_type": "api_error",
                "root_cause": "Upstream API returned a rate limit or throttling error.",
                "affected_steps": ["classify_ticket"],
                "suggested_fixes": [
                    "Add exponential backoff and jitter",
                    "Reduce parallel calls",
                ],
                "confidence": 0.75,
                "generated_at": _iso(now),
            },
        )
        print(f"wrote {rid}")

    # --- seed-07: failed — logic / validation ---
    rid = "seed-07"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[6]))
        events = [
            {"type": "run_started", "workflow": "financial_report", "path": wf_fin},
            {"type": "step_started", "step_id": "fetch_data", "agent": "data-fetcher"},
            {
                "type": "step_completed",
                "step_id": "fetch_data",
                "agent": "data-fetcher",
                "output": "Ledger slice 440k rows",
            },
            {"type": "step_pending_approval", "step_id": "analyze_risk", "agent": "financial-analyst"},
            {"type": "approval_granted", "step_id": "analyze_risk"},
            {"type": "step_started", "step_id": "analyze_risk", "agent": "financial-analyst"},
            {
                "type": "step_failed",
                "step_id": "analyze_risk",
                "error": "ValidationError: scenario matrix shape (12,9) incompatible with exposure tensor (12,8)",
            },
            {
                "type": "run_failed",
                "reason": "ValidationError: scenario matrix shape (12,9) incompatible with exposure tensor (12,8)",
            },
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_fin,
                "workflow_name": "financial_report",
                "status": "failed",
                "current_step_index": 1,
                "failure_reason": "ValidationError: scenario matrix shape (12,9) incompatible with exposure tensor (12,8)",
                "last_failed_step_id": "analyze_risk",
                "step_count": 3,
                "started_at": t0,
            },
        )
        _write_diagnosis(
            rd,
            {
                "run_id": rid,
                "failure_type": "logic_error",
                "root_cause": "A step failed during execution or produced unexpected output.",
                "affected_steps": ["fetch_data", "analyze_risk"],
                "suggested_fixes": [
                    "Validate output schema",
                    "Add defensive parsing",
                ],
                "confidence": 0.75,
                "generated_at": _iso(now),
            },
        )
        print(f"wrote {rid}")

    # --- seed-08: pending_approval financial analyze_risk ---
    rid = "seed-08"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[7]))
        events = [
            {"type": "run_started", "workflow": "financial_report", "path": wf_fin},
            {"type": "step_started", "step_id": "fetch_data", "agent": "data-fetcher"},
            {
                "type": "step_completed",
                "step_id": "fetch_data",
                "agent": "data-fetcher",
                "output": "Pulled FX forwards and IR swaps for desk EM-APAC",
            },
            {"type": "step_pending_approval", "step_id": "analyze_risk", "agent": "financial-analyst"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_fin,
                "workflow_name": "financial_report",
                "status": "pending_approval",
                "current_step_index": 1,
                "pending_step_id": "analyze_risk",
                "step_count": 3,
                "started_at": t0,
            },
        )
        print(f"wrote {rid}")

    # --- seed-09: pending_approval compliance flag_violations ---
    rid = "seed-09"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[8]))
        events = [
            {"type": "run_started", "workflow": "compliance_check", "path": wf_comp},
            {"type": "step_started", "step_id": "scan_docs", "agent": "doc-scanner"},
            {
                "type": "step_completed",
                "step_id": "scan_docs",
                "agent": "doc-scanner",
                "output": "OCR 112 pages; 6 DPAs flagged for subprocessors drift",
            },
            {"type": "step_pending_approval", "step_id": "flag_violations", "agent": "compliance-checker"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_comp,
                "workflow_name": "compliance_check",
                "status": "pending_approval",
                "current_step_index": 1,
                "pending_step_id": "flag_violations",
                "step_count": 4,
                "started_at": t0,
            },
        )
        print(f"wrote {rid}")

    # --- seed-10: policy_blocked (compliance — deny before flag step) ---
    rid = "seed-10"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[9]))
        events = [
            {"type": "run_started", "workflow": "compliance_check", "path": wf_comp},
            {"type": "step_started", "step_id": "scan_docs", "agent": "doc-scanner"},
            {
                "type": "step_completed",
                "step_id": "scan_docs",
                "agent": "doc-scanner",
                "output": "Indexed vault snapshot /legal/vendors/2025-Q1",
            },
            {
                "type": "policy_violation",
                "rule_id": "block-financial-actions",
                "action": "deny",
                "reason": "Financial actions require compliance review",
                "step_id": "flag_violations",
            },
            {"type": "run_failed", "reason": "policy_blocked"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_comp,
                "workflow_name": "compliance_check",
                "status": "policy_blocked",
                "current_step_index": 1,
                "pending_step_id": None,
                "step_count": 4,
                "started_at": t0,
                "last_failed_step_id": "flag_violations",
            },
        )
        print(f"wrote {rid}")

    # --- seed-11: policy_blocked (financial — deny on send_report) ---
    rid = "seed-11"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[10]))
        events = [
            {"type": "run_started", "workflow": "financial_report", "path": wf_fin},
            {"type": "step_started", "step_id": "fetch_data", "agent": "data-fetcher"},
            {
                "type": "step_completed",
                "step_id": "fetch_data",
                "agent": "data-fetcher",
                "output": "Balances reconciled vs. subledger B; no material breaks",
            },
            {"type": "step_pending_approval", "step_id": "analyze_risk", "agent": "financial-analyst"},
            {"type": "approval_granted", "step_id": "analyze_risk"},
            {"type": "step_started", "step_id": "analyze_risk", "agent": "financial-analyst"},
            {
                "type": "step_completed",
                "step_id": "analyze_risk",
                "agent": "financial-analyst",
                "output": "Risk band B+; concentration within policy after hedge overlay",
            },
            {
                "type": "policy_violation",
                "rule_id": "block-financial-actions",
                "action": "deny",
                "reason": "Financial actions require compliance review",
                "step_id": "send_report",
            },
            {"type": "run_failed", "reason": "policy_blocked"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_fin,
                "workflow_name": "financial_report",
                "status": "policy_blocked",
                "current_step_index": 2,
                "pending_step_id": None,
                "step_count": 3,
                "started_at": t0,
                "last_failed_step_id": "send_report",
            },
        )
        print(f"wrote {rid}")

    # --- seed-12: replay child — completed after replay from transform ---
    rid = "seed-12"
    parent_id = "seed-05"
    if not args.force and _run_dir(rid).is_dir():
        print(f"skip {rid} (exists; use --force)", file=sys.stderr)
    else:
        rd = _run_dir(rid)
        rd.mkdir(parents=True, exist_ok=True)
        t0 = _iso(now - timedelta(hours=offsets_hours[11]))
        (rd / "snapshots").mkdir(parents=True, exist_ok=True)
        parent_snap = _run_dir(parent_id) / "snapshots" / "extract.json"
        if parent_snap.is_file():
            shutil.copy2(parent_snap, rd / "snapshots" / "extract.json")
        else:
            snap_ts = _iso(now - timedelta(hours=offsets_hours[4]))
            snap = _snapshot(
                "extract",
                "data-pipeline",
                "Extract raw rows from source connector",
                "Parquet staging 812k rows; ready for transform",
                snap_ts,
                workflow="data_pipeline",
                step_index=0,
            )
            (rd / "snapshots" / "extract.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")

        events = [
            {
                "type": "replay_started",
                "origin_run_id": parent_id,
                "from_step": "transform",
            },
            {"type": "step_started", "step_id": "transform", "agent": "data-pipeline"},
            {
                "type": "step_completed",
                "step_id": "transform",
                "agent": "data-pipeline",
                "output": "Re-run with broadcast join; job data-pipeline-tx-5012 finished in 142s",
            },
            {"type": "step_started", "step_id": "load", "agent": "data-pipeline"},
            {
                "type": "step_completed",
                "step_id": "load",
                "agent": "data-pipeline",
                "output": "MERGE into DWH.FACT_REVENUE_DAILY complete; rowcount 812,019",
            },
            {"type": "run_completed"},
        ]
        _write_events(rd, events)
        _write_state(
            rd,
            {
                "run_id": rid,
                "workflow_path": wf_pipe,
                "workflow_name": "data_pipeline",
                "status": "completed",
                "current_step_index": 3,
                "pending_step_id": None,
                "step_count": 3,
                "started_at": t0,
                "replay_of": parent_id,
                "replay_from_step": "transform",
            },
        )
        print(f"wrote {rid}")

    print(f"Done. Runs directory: {settings.RUNS_DIR.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
