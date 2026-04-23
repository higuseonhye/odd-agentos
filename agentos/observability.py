"""
odd-agentos observability module
---------------------------------
Drop-in instrumentation: Prometheus metrics + structured JSON logging.

Usage:
    from observability import obs, track_llm_call, track_decision

    # wrap any LLM call
    with track_llm_call(model="claude-sonnet-4-6", policy="pmf-analysis"):
        response = my_llm_call(...)

    # record a decision with confidence
    track_decision(
        decision_id="run-123",
        outcome="approved",
        confidence=0.87,
        policy="pmf-analysis",
        latency_ms=340,
    )

    # expose /metrics endpoint (add to your HTTP server or run standalone)
    obs.start_metrics_server(port=9090)
"""

import json
import logging
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Optional Prometheus dependency — degrades gracefully if not installed
# ---------------------------------------------------------------------------
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        start_http_server, REGISTRY, generate_latest, CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------

class StructuredLogger:
    """Emits JSON log lines — plug into any log aggregator (Loki, CloudWatch, etc.)"""

    def __init__(self, name: str = "agentos"):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def _emit(self, level: str, event: str, **kwargs):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **kwargs,
        }
        line = json.dumps(payload, default=str)
        if level == "error":
            self._logger.error(line)
        elif level == "warn":
            self._logger.warning(line)
        else:
            self._logger.info(line)

    def info(self, event: str, **kwargs):  self._emit("info",  event, **kwargs)
    def warn(self, event: str, **kwargs):  self._emit("warn",  event, **kwargs)
    def error(self, event: str, **kwargs): self._emit("error", event, **kwargs)


# ---------------------------------------------------------------------------
# In-memory stats (fallback when Prometheus is not installed)
# ---------------------------------------------------------------------------

@dataclass
class InMemoryStats:
    llm_calls_total: int = 0
    llm_errors_total: int = 0
    decisions_total: int = 0
    low_confidence_total: int = 0          # confidence < 0.6
    latencies_ms: list = field(default_factory=list)
    active_runs: int = 0

    def p50(self) -> float:
        return self._percentile(50)

    def p95(self) -> float:
        return self._percentile(95)

    def p99(self) -> float:
        return self._percentile(99)

    def _percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        idx = int(len(s) * p / 100)
        return s[min(idx, len(s) - 1)]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["p50_ms"] = round(self.p50(), 1)
        d["p95_ms"] = round(self.p95(), 1)
        d["p99_ms"] = round(self.p99(), 1)
        d.pop("latencies_ms")
        return d


# ---------------------------------------------------------------------------
# Core observability class
# ---------------------------------------------------------------------------

class AgentOSObservability:
    """Central observability hub for odd-agentos."""

    def __init__(self, service_name: str = "agentos", confidence_threshold: float = 0.6):
        self.service_name = service_name
        self.confidence_threshold = confidence_threshold
        self.log = StructuredLogger(service_name)
        self.stats = InMemoryStats()

        if PROMETHEUS_AVAILABLE:
            self._init_prometheus()
        else:
            self.log.warn(
                "prometheus_client not installed — using in-memory stats only",
                hint="pip install prometheus_client",
            )

    def _init_prometheus(self):
        prefix = self.service_name.replace("-", "_")

        self.prom_llm_calls = Counter(
            f"{prefix}_llm_calls_total",
            "Total LLM API calls",
            ["model", "policy", "status"],
        )
        self.prom_llm_latency = Histogram(
            f"{prefix}_llm_latency_ms",
            "LLM call latency in milliseconds",
            ["model", "policy"],
            buckets=[50, 100, 250, 500, 1000, 2000, 5000],
        )
        self.prom_decisions = Counter(
            f"{prefix}_decisions_total",
            "Total decisions recorded",
            ["policy", "outcome"],
        )
        self.prom_confidence = Histogram(
            f"{prefix}_decision_confidence",
            "Decision confidence score (0–1)",
            ["policy"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )
        self.prom_active_runs = Gauge(
            f"{prefix}_active_runs",
            "Currently executing agent runs",
        )
        self.prom_low_confidence = Counter(
            f"{prefix}_low_confidence_decisions_total",
            f"Decisions below confidence threshold ({self.confidence_threshold})",
            ["policy"],
        )

    def start_metrics_server(self, port: int = 9090):
        """Expose /metrics for Prometheus scraping."""
        if not PROMETHEUS_AVAILABLE:
            self.log.warn("Cannot start metrics server — prometheus_client not installed")
            return
        start_http_server(port)
        self.log.info("metrics_server_started", port=port, path="/metrics")
        print(f"[agentos] Prometheus metrics available at http://localhost:{port}/metrics")

    def record_llm_call(
        self,
        model: str,
        policy: str,
        latency_ms: float,
        status: str = "success",
        tokens_in: int = 0,
        tokens_out: int = 0,
        error: Optional[str] = None,
    ):
        self.stats.llm_calls_total += 1
        self.stats.latencies_ms.append(latency_ms)
        if status == "error":
            self.stats.llm_errors_total += 1

        if PROMETHEUS_AVAILABLE:
            self.prom_llm_calls.labels(model=model, policy=policy, status=status).inc()
            self.prom_llm_latency.labels(model=model, policy=policy).observe(latency_ms)

        self.log.info(
            "llm_call",
            model=model, policy=policy, status=status,
            latency_ms=round(latency_ms, 1),
            tokens_in=tokens_in, tokens_out=tokens_out,
            **({"error": error} if error else {}),
        )

    def record_decision(
        self,
        decision_id: str,
        outcome: str,
        confidence: float,
        policy: str,
        latency_ms: float,
        metadata: Optional[dict] = None,
    ):
        self.stats.decisions_total += 1
        low_conf = confidence < self.confidence_threshold

        if low_conf:
            self.stats.low_confidence_total += 1

        if PROMETHEUS_AVAILABLE:
            self.prom_decisions.labels(policy=policy, outcome=outcome).inc()
            self.prom_confidence.labels(policy=policy).observe(confidence)
            if low_conf:
                self.prom_low_confidence.labels(policy=policy).inc()

        level = "warn" if low_conf else "info"
        self.log._emit(
            level, "decision",
            decision_id=decision_id, outcome=outcome,
            confidence=round(confidence, 4), policy=policy,
            latency_ms=round(latency_ms, 1),
            low_confidence=low_conf,
            **(metadata or {}),
        )

    def set_active_runs(self, n: int):
        self.stats.active_runs = n
        if PROMETHEUS_AVAILABLE:
            self.prom_active_runs.set(n)

    def summary(self) -> dict:
        return self.stats.to_dict()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

obs = AgentOSObservability()


# ---------------------------------------------------------------------------
# Convenience context managers
# ---------------------------------------------------------------------------

@contextmanager
def track_llm_call(model: str = "unknown", policy: str = "default"):
    """
    Context manager that times an LLM call and records it.

        with track_llm_call(model="claude-sonnet-4-6", policy="pmf"):
            response = client.messages.create(...)
    """
    start = time.perf_counter()
    status = "success"
    error_msg = None
    try:
        obs.set_active_runs(obs.stats.active_runs + 1)
        yield
    except Exception as exc:
        status = "error"
        error_msg = str(exc)
        obs.log.error("llm_call_exception", exc=error_msg, traceback=traceback.format_exc())
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        obs.record_llm_call(model=model, policy=policy, latency_ms=elapsed_ms, status=status, error=error_msg)
        obs.set_active_runs(max(0, obs.stats.active_runs - 1))


def track_decision(
    decision_id: str,
    outcome: str,
    confidence: float,
    policy: str = "default",
    latency_ms: float = 0.0,
    **metadata,
):
    """Record a completed decision with confidence score."""
    obs.record_decision(
        decision_id=decision_id,
        outcome=outcome,
        confidence=confidence,
        policy=policy,
        latency_ms=latency_ms,
        metadata=metadata or None,
    )
