"""System MRI — failure classification and diagnostic reports."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentos.config import settings
from agentos.observability import obs, track_decision

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc, assignment]


@dataclass
class DiagnosticReport:
    """Structured diagnosis for a run."""

    run_id: str
    failure_type: str
    root_cause: str
    affected_steps: list[str]
    suggested_fixes: list[str]
    confidence: float
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_dir(run_id: str) -> Path:
    return settings.RUNS_DIR / run_id


def _read_events(run_id: str) -> list[dict[str, Any]]:
    path = _run_dir(run_id) / "events.jsonl"
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


class FailureAnalyzer:
    """Reads events.jsonl and produces a DiagnosticReport."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    def analyze(self) -> DiagnosticReport:
        events = _read_events(self.run_id)
        ftype, steps, fixes, cause = self._rule_based(events)
        conf = 0.75 if ftype != "unknown" else 0.4
        if settings.OPENAI_API_KEY and OpenAI is not None:
            enhanced = self._llm_enhance(events, ftype, cause, fixes)
            if enhanced:
                cause, fixes, conf = enhanced
        rep = DiagnosticReport(
            run_id=self.run_id,
            failure_type=ftype,
            root_cause=cause,
            affected_steps=steps,
            suggested_fixes=fixes,
            confidence=min(1.0, conf),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        track_decision(
            decision_id=self.run_id,
            outcome=ftype,
            confidence=rep.confidence,
            policy="system_mri",
            latency_ms=0.0,
        )

        diag_path = _run_dir(self.run_id) / "diagnosis.json"
        diag_path.parent.mkdir(parents=True, exist_ok=True)
        diag_path.write_text(json.dumps(rep.to_dict(), indent=2), encoding="utf-8")
        return rep

    def _rule_based(
        self,
        events: list[dict[str, Any]],
    ) -> tuple[str, list[str], list[str], str]:
        text = json.dumps(events).lower()
        steps: list[str] = []
        for e in events:
            if isinstance(e.get("step_id"), str):
                steps.append(e["step_id"])
        steps = list(dict.fromkeys(steps))

        if "rate_limit" in text or "429" in text:
            return (
                "api_error",
                steps,
                ["Add exponential backoff and jitter", "Reduce parallel calls"],
                "Upstream API returned a rate limit or throttling error.",
            )
        if "policy_violation" in text or "policy_blocked" in text:
            return (
                "policy_violation",
                steps,
                ["Review policy rules and agent tags", "Adjust risk_level or approval gates"],
                "A policy rule blocked execution.",
            )
        if "approval_denied" in text:
            return (
                "approval_denied",
                steps,
                ["Review step risk level and approval UX", "Clarify human review criteria"],
                "A human reviewer denied a pending step.",
            )
        if "timeout" in text or "timed out" in text:
            return (
                "timeout",
                steps,
                ["Increase step timeout", "Optimize slow tools or LLM calls"],
                "A step exceeded its allowed execution time.",
            )
        if "hallucination" in text or "hallucination_risk" in text:
            return (
                "hallucination_risk",
                steps,
                ["Add grounding checks", "Use structured output validation"],
                "Output was flagged as potentially unreliable.",
            )
        if "step_failed" in text or "run_failed" in text:
            return (
                "logic_error",
                steps,
                ["Validate output schema", "Add defensive parsing"],
                "A step failed during execution or produced unexpected output.",
            )
        return (
            "unknown",
            steps,
            ["Inspect events.jsonl for details", "Enable AGENTOS_LOG_PAYLOADS for deeper traces"],
            "No specific failure pattern matched; see events for details.",
        )

    def _llm_enhance(
        self,
        events: list[dict[str, Any]],
        ftype: str,
        cause: str,
        fixes: list[str],
    ) -> tuple[str, list[str], float] | None:
        if OpenAI is None or not settings.OPENAI_API_KEY:
            return None
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            _t0 = time.perf_counter()
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You improve diagnostic text for engineers. Reply JSON only: "
                            '{"root_cause": str, "suggested_fixes": [str], "confidence": float}',
                        },
                        {
                            "role": "user",
                            "content": f"type={ftype}\nevents={json.dumps(events)[:8000]}",
                        },
                    ],
                    temperature=0.2,
                )
                obs.record_llm_call(
                    model="gpt-4o-mini",
                    policy="system_mri",
                    latency_ms=(time.perf_counter() - _t0) * 1000,
                    status="success",
                    tokens_in=resp.usage.prompt_tokens,
                    tokens_out=resp.usage.completion_tokens,
                )
            except Exception as exc:
                obs.record_llm_call(
                    model="gpt-4o-mini",
                    policy="system_mri",
                    latency_ms=(time.perf_counter() - _t0) * 1000,
                    status="error",
                    error=str(exc),
                )
                return None

            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
            return (
                str(data.get("root_cause", cause)),
                list(data.get("suggested_fixes", fixes)),
                float(data.get("confidence", 0.7)),
            )
        except Exception:  # noqa: BLE001
            return None