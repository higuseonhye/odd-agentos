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

Open **http://localhost:8080** → your run appears instantly.

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
      │
      ▼
 AgentOS Runtime
  ├── runs each step
  ├── saves a snapshot after every step
  ├── checks policy rules before risky steps
  ├── pauses for human approval when needed
  └── logs everything to events.jsonl
      │
      ▼
 Dashboard (http://localhost:8080)
  ├── See run status live
  ├── Approve / Deny pending steps
  ├── Click "Replay from here" on any failed step
  └── Run System MRI to get a diagnosis report
```

---

## CLI

```bash
agentos init                          # scaffold a new project
agentos run workflows/sample.yaml     # start a run
agentos retry <run_id>                # retry from the failed step
agentos replay <run_id> --from-step summarize   # replay from a specific step
agentos diagnose <run_id>             # get a System MRI report
agentos reliability <agent_name>      # generate a trust score card
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
    requires_approval: true   # pauses for human approval
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
- [ ] `pip install agentos` one-liner (coming soon)
- [ ] Hosted cloud version

---

## License

Proprietary / ODD PLAYGROUND
