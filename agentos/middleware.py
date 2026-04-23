"""
middleware.py — Agent run instrumentation wrapper
--------------------------------------------------
기존 agentos 실행 로직을 건드리지 않고 observability를 붙이는 래퍼.

Before (기존 코드):
    result = agent.run(task)

After (계측 추가):
    from middleware import InstrumentedAgent
    agent = InstrumentedAgent(your_agent, policy="pmf-analysis")
    result = agent.run(task)          # 동일한 인터페이스, 자동으로 metrics 기록
"""

import time
import uuid
from typing import Any, Callable, Optional

from observability import obs, track_llm_call, track_decision


class InstrumentedAgent:
    """
    Wraps any agent object to add automatic observability.
    Assumes the agent has a .run(task) method that returns a result dict
    with optional 'confidence' and 'outcome' keys.
    """

    def __init__(self, agent: Any, policy: str = "default", model: str = "unknown"):
        self._agent = agent
        self.policy = policy
        self.model = model

    def run(self, task: Any, decision_id: Optional[str] = None) -> Any:
        run_id = decision_id or str(uuid.uuid4())[:8]
        start = time.perf_counter()

        obs.log.info("agent_run_start", run_id=run_id, policy=self.policy, task=str(task)[:120])
        obs.set_active_runs(obs.stats.active_runs + 1)

        try:
            with track_llm_call(model=self.model, policy=self.policy):
                result = self._agent.run(task)

            elapsed_ms = (time.perf_counter() - start) * 1000

            confidence = _extract_confidence(result)
            outcome = _extract_outcome(result)

            track_decision(
                decision_id=run_id,
                outcome=outcome,
                confidence=confidence,
                policy=self.policy,
                latency_ms=elapsed_ms,
            )

            obs.log.info(
                "agent_run_complete",
                run_id=run_id, policy=self.policy,
                outcome=outcome, confidence=round(confidence, 4),
                latency_ms=round(elapsed_ms, 1),
            )
            return result

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            obs.log.error(
                "agent_run_failed",
                run_id=run_id, policy=self.policy,
                exc=str(exc), latency_ms=round(elapsed_ms, 1),
            )
            raise
        finally:
            obs.set_active_runs(max(0, obs.stats.active_runs - 1))

    def __getattr__(self, name):
        return getattr(self._agent, name)


# ---------------------------------------------------------------------------
# LLM call wrapper — for direct API calls (Anthropic, OpenAI, etc.)
# ---------------------------------------------------------------------------

def instrumented_llm_call(
    fn: Callable,
    model: str = "unknown",
    policy: str = "default",
    extract_tokens: Optional[Callable] = None,
) -> Callable:
    """
    Decorator/wrapper for raw LLM API calls.

    Usage:
        from middleware import instrumented_llm_call

        response = instrumented_llm_call(
            fn=lambda: client.messages.create(model="claude-sonnet-4-6", ...),
            model="claude-sonnet-4-6",
            policy="pmf-analysis",
            extract_tokens=lambda r: (r.usage.input_tokens, r.usage.output_tokens),
        )
    """
    import time
    start = time.perf_counter()
    status = "success"
    tokens_in = tokens_out = 0
    error_msg = None

    try:
        obs.set_active_runs(obs.stats.active_runs + 1)
        result = fn()
        if extract_tokens:
            tokens_in, tokens_out = extract_tokens(result)
        return result
    except Exception as exc:
        status = "error"
        error_msg = str(exc)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        obs.record_llm_call(
            model=model, policy=policy,
            latency_ms=elapsed_ms, status=status,
            tokens_in=tokens_in, tokens_out=tokens_out,
            error=error_msg,
        )
        obs.set_active_runs(max(0, obs.stats.active_runs - 1))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_confidence(result: Any) -> float:
    if isinstance(result, dict):
        for key in ("confidence", "confidence_score", "score", "probability"):
            if key in result:
                return float(result[key])
    if hasattr(result, "confidence"):
        return float(result.confidence)
    return 1.0


def _extract_outcome(result: Any) -> str:
    if isinstance(result, dict):
        for key in ("outcome", "status", "decision", "result"):
            if key in result:
                return str(result[key])
    if hasattr(result, "outcome"):
        return str(result.outcome)
    return "completed"
