"""Reliability Card — aggregate trust metrics for an agent."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agentos.config import settings


@dataclass
class ReliabilityCard:
    """One-page trust summary for an agent."""

    agent_name: str
    period: str
    trust_score: int
    trust_level: str
    metrics: dict[str, Any]
    failure_patterns: list[dict[str, Any]]
    recommendations: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _trust_level(score: int) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "CONDITIONAL"
    return "LOW-RISK"


def _parse_time(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


class ReliabilityCardGenerator:
    """Scans runs under RUNS_DIR and aggregates metrics for an agent."""

    def __init__(self, agent_name: str, days: int = 30) -> None:
        self.agent_name = agent_name.lower()
        self.days = days

    def generate(self) -> ReliabilityCard:
        since = datetime.now(timezone.utc) - timedelta(days=self.days)
        runs_dir = settings.RUNS_DIR
        total = 0
        completed = 0
        policy_blocked = 0
        approved = 0
        denied = 0
        step_counts: list[int] = []
        failure_types: dict[str, int] = {}

        if runs_dir.is_dir():
            for rd in runs_dir.iterdir():
                if not rd.is_dir():
                    continue
                state_path = rd / "state.json"
                if not state_path.is_file():
                    continue
                state = json.loads(state_path.read_text(encoding="utf-8"))
                started = _parse_time(state.get("started_at") or state.get("updated_at"))
                if started and started < since.replace(tzinfo=timezone.utc):
                    continue
                events = self._events_for_run(rd)
                if not self._mentions_agent(events, state):
                    continue
                total += 1
                st = state.get("status", "")
                if st == "completed":
                    completed += 1
                if st == "policy_blocked":
                    policy_blocked += 1
                step_counts.append(int(state.get("step_count") or len(events)))
                for e in events:
                    if e.get("type") == "approval_granted":
                        approved += 1
                    if e.get("type") == "approval_denied":
                        denied += 1
                ft = self._failure_type_from_events(events)
                if ft:
                    failure_types[ft] = failure_types.get(ft, 0) + 1

        success_rate = completed / total if total else 0.0
        appr_denom = approved + denied
        approval_rate = approved / appr_denom if appr_denom else 0.0
        pol_rate = policy_blocked / total if total else 0.0
        avg_steps = sum(step_counts) / len(step_counts) if step_counts else 0.0

        trust = int(
            round(
                100 * (0.5 * success_rate + 0.25 * (1 - pol_rate) + 0.25 * approval_rate),
            ),
        )
        trust = max(0, min(100, trust))

        top_failures = sorted(failure_types.items(), key=lambda x: -x[1])[:3]
        patterns = [{"type": k, "count": v} for k, v in top_failures]

        recs: list[str] = []
        if pol_rate > 0.1:
            recs.append("Policy blocks are elevated — review rules and agent tags.")
        if success_rate < 0.8:
            recs.append("Success rate is below target — inspect failing steps in System MRI.")

        period_end = datetime.now(timezone.utc).date().isoformat()
        period_start = (datetime.now(timezone.utc) - timedelta(days=self.days)).date().isoformat()
        card = ReliabilityCard(
            agent_name=self.agent_name,
            period=f"{period_start} to {period_end}",
            trust_score=trust,
            trust_level=_trust_level(trust),
            metrics={
                "success_rate": round(success_rate, 4),
                "approval_rate": round(approval_rate, 4),
                "policy_violation_rate": round(pol_rate, 4),
                "avg_steps_per_run": round(avg_steps, 2),
                "runs_in_period": total,
            },
            failure_patterns=patterns,
            recommendations=recs or ["No major issues detected in this window."],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_agent = re.sub(r"[^a-zA-Z0-9._-]+", "_", self.agent_name)
        out = settings.REPORTS_DIR / f"reliability_{safe_agent}_{period_end}.json"
        out.write_text(json.dumps(card.to_dict(), indent=2), encoding="utf-8")
        return card

    def _events_for_run(self, rd: Path) -> list[dict[str, Any]]:
        p = rd / "events.jsonl"
        if not p.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _mentions_agent(self, events: list[dict[str, Any]], state: dict[str, Any]) -> bool:
        for e in events:
            if str(e.get("agent", "")).lower() == self.agent_name:
                return True
        blob = json.dumps(state).lower()
        return self.agent_name in blob

    def _failure_type_from_events(self, events: list[dict[str, Any]]) -> str | None:
        for e in reversed(events):
            if e.get("type") == "run_failed":
                return str(e.get("reason") or "failed")
            if e.get("type") == "step_failed":
                return "step_failed"
        return None
