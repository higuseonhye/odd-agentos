# AgentOS
**Replay, debug, and govern AI agents in production.**
When your agent fails mid-run, AgentOS tells you exactly which step broke — and lets you re-run from that point without starting over.

---

## Start in 30 seconds
```bash
pip install agentos
agentos init
agentos run workflows/sample.yaml
```
Open **http://localhost:8080** — your run appears instantly.

> No Redis. No Docker. No second terminal. Just Python.

---

## What it solves
| Problem | What AgentOS does |
|---------|------------------|
| Agent fails — no idea why | Step-by-step audit log + System MRI diagnosis |
| Have to restart from scratch | Replay from any failed step |
| No human oversight on risky actions | Approve / Deny gates in the dashboard |
| Can't prove what the agent did | Immutable event log (`events.jsonl`) |

---

## How it works
```
your workflow.yaml
      ↓
 AgentOS Runtime
  ├── runs each step
  ├── saves a snapshot after every step
  ├── checks policy rules before risky steps
  ├── pauses for human approval when needed
  └── logs everything to events.jsonl
      ↓
 Dashboard (http://localhost:8080)
  ├── See run status live
  ├── Approve / Deny pending steps
  ├── Click "Replay from here" on any failed step
  └── Run System MRI to get a diagnosis report
```

---

## CLI
```bash
agentos init                         # scaffold a new project
agentos run workflows/sample.yaml    # start a run
agentos retry <run_id>               # retry from the failed step
agentos replay <run_id> --from-step summarize  # replay from a specific step
agentos diagnose <run_id>            # get a System MRI report
agentos reliability <agent_name>     # generate a trust score card
```

---

## Example workflow
```yaml
# workflows/sample.yaml
name: sample
steps:
  - id: greet
    agent: greeter
    risk_level: low
    input: "world"
    requires_approval: false
  - id: summarize
    agent: summarizer
    risk_level: medium
    input: "Summarize: hello"
    requires_approval: true  # pauses for human approval
```

Run it:
```bash
agentos run workflows/sample.yaml
# → greet completes automatically
# → summarize pauses — open dashboard to Approve or Deny
```

---

## Policy rules (YAML)
Control what agents can do without touching code:
```yaml
# policies/default.yaml
rules:
  - id: block-payments
    condition:
      agent_tags_include: ["payment"]
    action: deny
    reason: "Payment actions require compliance review"
  - id: approve-high-risk
    condition:
      risk_level_gte: high
    action: require_approval
```

---

## Production hardening

AgentOS ships with built-in observability. Every LLM call and agent decision is automatically instrumented — no extra configuration needed.

### What gets recorded

Every run emits structured JSON logs to stderr, ready for any log aggregator (Loki, CloudWatch, Datadog):

```json
{"ts": "2026-04-23T01:49:42Z", "level": "info", "event": "llm_call",
 "model": "gpt-4o-mini", "policy": "greeter", "status": "success",
 "latency_ms": 312.4, "tokens_in": 84, "tokens_out": 210}

{"ts": "2026-04-23T01:49:42Z", "level": "info", "event": "decision",
 "decision_id": "a98cb823/greet", "outcome": "completed",
 "confidence": 0.87, "policy": "greeter", "latency_ms": 318.1,
 "low_confidence": false}

{"ts": "2026-04-23T01:49:42Z", "level": "warn", "event": "decision",
 "decision_id": "b12f9910/summarize", "outcome": "needs_review",
 "confidence": 0.43, "policy": "summarizer", "latency_ms": 289.6,
 "low_confidence": true}
```

`level: warn` is automatically emitted when confidence drops below 0.6 — the signal that a decision needs human review before the organization acts on it.

### Prometheus metrics

Install the client and metrics are available at `/metrics` automatically:

```bash
pip install prometheus_client
```

```python
from agentos.observability import obs
obs.start_metrics_server(port=9090)  # add to main.py or docker-compose
```

| Metric | Type | What it tells you |
|--------|------|-------------------|
| `agentos_llm_calls_total` | Counter | call volume by model, policy, status |
| `agentos_llm_latency_ms` | Histogram | p50/p95/p99 latency per policy |
| `agentos_decisions_total` | Counter | decision volume by outcome |
| `agentos_decision_confidence` | Histogram | confidence distribution per policy |
| `agentos_low_confidence_decisions_total` | Counter | decisions that need human review |
| `agentos_active_runs` | Gauge | concurrency at any moment |

### Terminal dashboard

```bash
python dashboard/dashboard.py        # live view, refreshes every 3s
python dashboard/dashboard.py test   # smoke test with simulated calls
```

```
┌─ odd-agentos observability ──────────────────── 01:49:42 ─┐

  LLM Calls
  total          42    active now    2
  errors          1    error rate   2.4%

  Latency (ms)
  p50        312.0   ████████░░░░░░░░░░░░
  p95        890.0   ██████████████░░░░░░
  p99       1240.0   ████████████████████

  Decisions
  total          38
  low conf        4    rate        10.5%

  [ok] All systems nominal
└──────────────────────────────────────────────────────────┘
```

### System MRI

When a run fails, `agentos diagnose <run_id>` reads `events.jsonl`, classifies the failure, and writes a structured report:

```json
{
  "run_id": "a98cb823-e071-4fd8-bfb4-7d579644cfe7",
  "failure_type": "policy_violation",
  "root_cause": "A policy rule blocked execution.",
  "affected_steps": ["summarize"],
  "suggested_fixes": [
    "Review policy rules and agent tags",
    "Adjust risk_level or approval gates"
  ],
  "confidence": 0.75,
  "generated_at": "2026-04-23T01:49:44Z"
}
```

Failure types: `api_error`, `policy_violation`, `approval_denied`, `timeout`, `hallucination_risk`, `logic_error`, `unknown`.

### Key design principle

> AI makes the decision. The confidence score makes it credible. The human approves when it isn't.

Low-confidence decisions (`confidence < 0.6`) surface automatically as warnings in logs and metrics. High-risk steps pause for human approval before execution. Every decision is replayable from `events.jsonl`. This is what "AI decisions credible enough for organizations to execute" looks like in practice.

---

## SDK
```bash
pip install agentos-sdk
```
```python
from agentos_sdk import AgentOS
client = AgentOS(project="my-project")
run_id = client.run("workflows/sample.yaml")
report = client.diagnose(run_id)
```

Decorator for existing functions:
```python
from agentos_sdk.decorators import trace

@trace(requires_approval=True, risk_level="high")
def my_agent(input: str) -> str:
    ...
```

---

## Docker (production)
```bash
make prod
# or: docker compose -f docker-compose.prod.yml up -d --build
```

---

## Roadmap
- [x] YAML workflow runner
- [x] Human-in-the-loop approval gates
- [x] Replay from any step
- [x] System MRI failure diagnosis
- [x] Reliability Card (agent trust score)
- [x] Policy engine (YAML rules)
- [x] Built-in observability (Prometheus + structured logging)
- [ ] `pip install agentos` one-liner (coming soon)
- [ ] Hosted cloud version

---

## License
Proprietary / ODD Park