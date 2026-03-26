#!/usr/bin/env python3
"""
Populate runs/ with realistic demo history for dashboard first-open (investors / beta).

Writes state.json + events.jsonl per run under RUNS_DIR (default: ./runs).
Run IDs use prefix ``demo-`` so you can delete them with: Remove-Item runs/demo-* -Recurse (PowerShell).

Usage:
  python scripts/seed_demo_data.py
  python scripts/seed_demo_data.py --force   # overwrite existing demo-* runs
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


def _write_run(
    run_id: str,
    *,
    workflow_file: str,
    workflow_name: str,
    step_count: int,
    started_at: str,
    status: str,
    events: list[dict],
    extra_state: dict | None = None,
) -> None:
    rd = settings.RUNS_DIR / run_id
    rd.mkdir(parents=True, exist_ok=True)
    state: dict = {
        "run_id": run_id,
        "workflow_path": _wf(workflow_file),
        "workflow_name": workflow_name,
        "status": status,
        "current_step_index": step_count,
        "pending_step_id": None,
        "step_count": step_count,
        "started_at": started_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra_state:
        state.update(extra_state)
    (rd / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    lines = [json.dumps(_ev(e), ensure_ascii=False) for e in events]
    (rd / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _support_completed(run_id: str, started_at: str) -> None:
    events = [
        {"type": "run_started", "workflow": "customer_support", "path": _wf("customer_support_agent.yaml")},
        {"type": "step_started", "step_id": "classify", "agent": "support_bot"},
        {"type": "step_completed", "step_id": "classify", "agent": "support_bot", "output": "[support_bot] Classify ticket intent"},
        {"type": "step_started", "step_id": "draft_reply", "agent": "support_bot"},
        {"type": "step_completed", "step_id": "draft_reply", "agent": "support_bot", "output": "[support_bot] Draft a concise customer reply"},
        {"type": "run_completed"},
    ]
    _write_run(
        run_id,
        workflow_file="customer_support_agent.yaml",
        workflow_name="customer_support",
        step_count=2,
        started_at=started_at,
        status="completed",
        events=events,
        extra_state={"current_step_index": 2},
    )


def _support_failed(run_id: str, started_at: str) -> None:
    events = [
        {"type": "run_started", "workflow": "customer_support", "path": _wf("customer_support_agent.yaml")},
        {"type": "step_started", "step_id": "classify", "agent": "support_bot"},
        {"type": "step_completed", "step_id": "classify", "agent": "support_bot", "output": "intent=billing"},
        {"type": "step_started", "step_id": "draft_reply", "agent": "support_bot"},
        {"type": "step_failed", "step_id": "draft_reply", "error": "upstream CRM timeout"},
        {"type": "run_failed", "reason": "upstream CRM timeout"},
    ]
    _write_run(
        run_id,
        workflow_file="customer_support_agent.yaml",
        workflow_name="customer_support",
        step_count=2,
        started_at=started_at,
        status="failed",
        events=events,
        extra_state={
            "current_step_index": 1,
            "failure_reason": "upstream CRM timeout",
            "last_failed_step_id": "draft_reply",
        },
    )


def _financial_completed(run_id: str, started_at: str) -> None:
    p = _wf("financial_report_agent.yaml")
    events = [
        {"type": "run_started", "workflow": "financial_report", "path": p},
        {"type": "step_started", "step_id": "gather_ledger", "agent": "ledger_analyst"},
        {"type": "step_completed", "step_id": "gather_ledger", "agent": "ledger_analyst", "output": "[ledger_analyst] Pull Q4 GL balances"},
        {"type": "step_pending_approval", "step_id": "draft_filing", "agent": "ledger_analyst"},
        {"type": "approval_granted", "step_id": "draft_filing"},
        {"type": "step_started", "step_id": "draft_filing", "agent": "ledger_analyst"},
        {"type": "step_completed", "step_id": "draft_filing", "agent": "ledger_analyst", "output": "[ledger_analyst] Draft narrative"},
        {"type": "step_pending_approval", "step_id": "export_pdf", "agent": "ledger_analyst"},
        {"type": "approval_granted", "step_id": "export_pdf"},
        {"type": "step_started", "step_id": "export_pdf", "agent": "ledger_analyst"},
        {"type": "step_completed", "step_id": "export_pdf", "agent": "ledger_analyst", "output": "[ledger_analyst] PDF generated"},
        {"type": "run_completed"},
    ]
    _write_run(
        run_id,
        workflow_file="financial_report_agent.yaml",
        workflow_name="financial_report",
        step_count=3,
        started_at=started_at,
        status="completed",
        events=events,
        extra_state={"current_step_index": 3},
    )


def _financial_pending(run_id: str, started_at: str) -> None:
    p = _wf("financial_report_agent.yaml")
    events = [
        {"type": "run_started", "workflow": "financial_report", "path": p},
        {"type": "step_started", "step_id": "gather_ledger", "agent": "ledger_analyst"},
        {"type": "step_completed", "step_id": "gather_ledger", "agent": "ledger_analyst", "output": "ledger_ok"},
        {"type": "step_pending_approval", "step_id": "draft_filing", "agent": "ledger_analyst"},
    ]
    _write_run(
        run_id,
        workflow_file="financial_report_agent.yaml",
        workflow_name="financial_report",
        step_count=3,
        started_at=started_at,
        status="pending_approval",
        events=events,
        extra_state={"current_step_index": 1, "pending_step_id": "draft_filing"},
    )


def _financial_policy_blocked(run_id: str, started_at: str) -> None:
    p = _wf("financial_report_agent.yaml")
    events = [
        {"type": "run_started", "workflow": "financial_report", "path": p},
        {"type": "step_started", "step_id": "gather_ledger", "agent": "ledger_analyst"},
        {"type": "step_completed", "step_id": "gather_ledger", "agent": "ledger_analyst", "output": "ledger_ok"},
        {"type": "step_pending_approval", "step_id": "draft_filing", "agent": "ledger_analyst"},
        {"type": "approval_granted", "step_id": "draft_filing"},
        {"type": "step_started", "step_id": "draft_filing", "agent": "ledger_analyst"},
        {"type": "step_completed", "step_id": "draft_filing", "agent": "ledger_analyst", "output": "narrative_ok"},
        {"type": "step_pending_approval", "step_id": "export_pdf", "agent": "ledger_analyst"},
        {"type": "approval_granted", "step_id": "export_pdf"},
        {
            "type": "policy_violation",
            "rule_id": "block-financial-actions",
            "action": "deny",
            "reason": "Financial actions require compliance review",
            "step_id": "export_pdf",
        },
        {"type": "run_failed", "reason": "policy_blocked"},
    ]
    _write_run(
        run_id,
        workflow_file="financial_report_agent.yaml",
        workflow_name="financial_report",
        step_count=3,
        started_at=started_at,
        status="policy_blocked",
        events=events,
        extra_state={"current_step_index": 2, "last_failed_step_id": "export_pdf"},
    )


def _financial_approval_denied(run_id: str, started_at: str) -> None:
    p = _wf("financial_report_agent.yaml")
    events = [
        {"type": "run_started", "workflow": "financial_report", "path": p},
        {"type": "step_started", "step_id": "gather_ledger", "agent": "ledger_analyst"},
        {"type": "step_completed", "step_id": "gather_ledger", "agent": "ledger_analyst", "output": "ledger_ok"},
        {"type": "step_pending_approval", "step_id": "draft_filing", "agent": "ledger_analyst"},
        {"type": "approval_denied", "step_id": "draft_filing", "agent": "ledger_analyst"},
        {"type": "run_failed", "reason": "approval_denied"},
    ]
    _write_run(
        run_id,
        workflow_file="financial_report_agent.yaml",
        workflow_name="financial_report",
        step_count=3,
        started_at=started_at,
        status="failed",
        events=events,
        extra_state={
            "current_step_index": 1,
            "failure_reason": "approval_denied",
            "last_failed_step_id": "draft_filing",
        },
    )


def _pipeline_completed(run_id: str, started_at: str) -> None:
    p = _wf("data_pipeline_agent.yaml")
    events = [
        {"type": "run_started", "workflow": "data_pipeline", "path": p},
        {"type": "step_started", "step_id": "extract", "agent": "data-pipeline"},
        {"type": "step_completed", "step_id": "extract", "agent": "data-pipeline", "output": "42 rows"},
        {"type": "step_started", "step_id": "transform", "agent": "data-pipeline"},
        {"type": "step_completed", "step_id": "transform", "agent": "data-pipeline", "output": "40 rows"},
        {"type": "step_started", "step_id": "load", "agent": "data-pipeline"},
        {"type": "step_completed", "step_id": "load", "agent": "data-pipeline", "output": "staging_ok"},
        {"type": "run_completed"},
    ]
    _write_run(
        run_id,
        workflow_file="data_pipeline_agent.yaml",
        workflow_name="data_pipeline",
        step_count=3,
        started_at=started_at,
        status="completed",
        events=events,
        extra_state={"current_step_index": 3},
    )


def _pipeline_failed_transform(run_id: str, started_at: str) -> None:
    p = _wf("data_pipeline_agent.yaml")
    events = [
        {"type": "run_started", "workflow": "data_pipeline", "path": p},
        {"type": "step_started", "step_id": "extract", "agent": "data-pipeline"},
        {"type": "step_completed", "step_id": "extract", "agent": "data-pipeline", "output": "99 rows"},
        {"type": "step_started", "step_id": "transform", "agent": "data-pipeline"},
        {"type": "step_failed", "step_id": "transform", "error": "schema drift: column revenue_usd missing"},
        {"type": "run_failed", "reason": "schema drift: column revenue_usd missing"},
    ]
    _write_run(
        run_id,
        workflow_file="data_pipeline_agent.yaml",
        workflow_name="data_pipeline",
        step_count=3,
        started_at=started_at,
        status="failed",
        events=events,
        extra_state={
            "current_step_index": 1,
            "failure_reason": "schema drift: column revenue_usd missing",
            "last_failed_step_id": "transform",
        },
    )


def _pipeline_failed_load(run_id: str, started_at: str) -> None:
    p = _wf("data_pipeline_agent.yaml")
    events = [
        {"type": "run_started", "workflow": "data_pipeline", "path": p},
        {"type": "step_started", "step_id": "extract", "agent": "data-pipeline"},
        {"type": "step_completed", "step_id": "extract", "agent": "data-pipeline", "output": "1k rows"},
        {"type": "step_started", "step_id": "transform", "agent": "data-pipeline"},
        {"type": "step_completed", "step_id": "transform", "agent": "data-pipeline", "output": "998 rows"},
        {"type": "step_started", "step_id": "load", "agent": "data-pipeline"},
        {"type": "step_failed", "step_id": "load", "error": "warehouse connection reset"},
        {"type": "run_failed", "reason": "warehouse connection reset"},
    ]
    _write_run(
        run_id,
        workflow_file="data_pipeline_agent.yaml",
        workflow_name="data_pipeline",
        step_count=3,
        started_at=started_at,
        status="failed",
        events=events,
        extra_state={
            "current_step_index": 2,
            "failure_reason": "warehouse connection reset",
            "last_failed_step_id": "load",
        },
    )


def _clear_demo_runs() -> None:
    base = settings.RUNS_DIR
    if not base.is_dir():
        return
    for rd in base.iterdir():
        if rd.is_dir() and rd.name.startswith("demo-"):
            shutil.rmtree(rd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo runs under RUNS_DIR.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove existing runs named demo-* before writing.",
    )
    args = parser.parse_args()

    if args.force:
        _clear_demo_runs()

    now = datetime.now(timezone.utc)
    specs: list[tuple[str, str]] = [
        ("demo-001", "support_done"),
        ("demo-002", "support_done"),
        ("demo-003", "support_fail"),
        ("demo-004", "support_done"),
        ("demo-005", "fin_done"),
        ("demo-006", "fin_pending"),
        ("demo-007", "fin_policy"),
        ("demo-008", "fin_deny"),
        ("demo-009", "pipe_done"),
        ("demo-010", "pipe_tf"),
        ("demo-011", "pipe_done"),
        ("demo-012", "pipe_load"),
        ("demo-013", "fin_done"),
        ("demo-014", "support_done"),
    ]

    for i, (rid, kind) in enumerate(specs):
        started = (now - timedelta(hours=i * 6)).isoformat()
        if (settings.RUNS_DIR / rid).exists() and not args.force:
            print(f"skip {rid} (exists; use --force to overwrite)", file=sys.stderr)
            continue
        if kind == "support_done":
            _support_completed(rid, started)
        elif kind == "support_fail":
            _support_failed(rid, started)
        elif kind == "fin_done":
            _financial_completed(rid, started)
        elif kind == "fin_pending":
            _financial_pending(rid, started)
        elif kind == "fin_policy":
            _financial_policy_blocked(rid, started)
        elif kind == "fin_deny":
            _financial_approval_denied(rid, started)
        elif kind == "pipe_done":
            _pipeline_completed(rid, started)
        elif kind == "pipe_tf":
            _pipeline_failed_transform(rid, started)
        elif kind == "pipe_load":
            _pipeline_failed_load(rid, started)
        else:
            raise RuntimeError(kind)
        print(f"wrote {rid}")

    print(f"Done. Runs directory: {settings.RUNS_DIR.resolve()}")
    print("Reliability: try agents support_bot, ledger_analyst (30-day window).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
