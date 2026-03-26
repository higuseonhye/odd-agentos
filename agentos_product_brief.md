# AgentOS — Product Brief & Cursor Development Guide
> ODD PLAYGROUND | Founder: Seonhye Gu
> Last updated: 2026-03-26

---

## 1. One-Line Definition

> **AgentOS is a self-evolving operating infrastructure for AI agents — enabling full execution replay, failure recovery from any step, and policy-based human approval gates.**

If LangSmith is a "log viewer," AgentOS is the "OS for agents."

---

## 2. Why We're Building This (Problem)

| Problem | Consequence |
|---------|-------------|
| Same input → different output (non-determinism) | Service quality is unpredictable |
| No replay or recovery on failure | Must restart from scratch every time |
| No accountability for AI decisions | Regulated industries (finance, public sector) can't adopt AI |
| EU AI Act + domestic AI laws taking effect | Audit obligations → new compliance burden for enterprises |

---

## 3. What We're Building (Product)

### Three Core Engines

```
┌─────────────────────────────────────────────────┐
│            AgentOS Dashboard (React)             │
├──────────────┬──────────────┬───────────────────┤
│  Replayable  │    Policy    │    System MRI      │
│   Runtime    │    Engine    │  (Self-Improve)    │
│  (Python)    │  (YAML-based)│                    │
└──────────────┴──────────────┴───────────────────┘
                    ↑ SDK / API
              External AI Agents
```

### Feature List

**Phase 1 (Current MVP — based on `agentos` repo)**
- [x] YAML workflow runner
- [x] Human-in-the-loop approval gates (CLI + web UI)
- [x] Append-only event log (`events.jsonl`)
- [x] Retry from failed step
- [x] Multi-tenant base (`tenant_id`)
- [x] Docker deployment support

**Phase 2 (Roadmap)**
- [ ] Replayable Runtime optimization (step-level snapshots)
- [ ] Policy Engine expansion (YAML-based rule sets)
- [ ] System MRI diagnostic engine (automated failure pattern analysis)
- [ ] Self-Improvement Engine (diagnosis → automated fix suggestions)
- [ ] Reliability Card (auto-generated agent trust score reports)
- [ ] SDK / API documentation

---

## 4. Existing Repository Overview

| Repo | Status | Core Content |
|------|--------|--------------|
| `agentos` | ⭐ Main | HITL workflows, approval gates, retry, Docker |
| `agentos_mvp` | Early skeleton | Flask + plain HTML UI |
| `agentos_master` / `agentos_reference` | Reference | Version history |
| `agent-accountability-eval` | Eval framework | Audit log schemas, GO/NO-GO gates |
| `agent-eval-toolkit` | Eval tools | Behavior-based metrics |
| `agent-lens` | Analysis tool | Agent behavior observation |
| `mission-engine` | Experiment | Mission-driven agent execution |
| `judgement-engine` | Experiment | Judgment engine |
| `worldsim-eval` | Experiment | Environment simulation eval |
| `zeroenv` | Experiment | Zero-config environment setup |
| `deal-lens` | Separate product | Deal/transaction analysis tool |
| `aicivic-mvp` | Separate product | Civic AI service MVP |
| `pmf-finder` | Utility | PMF discovery tool |
| `storyos` / `stage` | Experiments | Story/Stage OS |
| `structure-it` / `deciscope` | Experiments | Structuring / decision scoping |
| `spk_balance` | Utility | Speaker balance tool |
| `ai-bedrock-chatbot` | Reference | AWS Bedrock chatbot |

**→ Primary development target: build on top of the `agentos` repo**

---

## 5. Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python (Flask/FastAPI), Celery, Redis |
| Frontend | React, JavaScript |
| Data | JSONL (event logs), JSON (state snapshots), YAML (policies/workflows) |
| Infrastructure | Docker, docker-compose |
| AI Integration | OpenAI API (current), multi-LLM support planned |

---

## 6. Business Model

| Plan | Price | Target |
|------|-------|--------|
| Free | Free | Individual developers, open source |
| Team | $200/month per team | Startups, small dev teams |
| Enterprise | Annual contract (negotiated) | Enterprises, finance/public sector |

**SOM Target**: $4.7M–$35M within the first 3 years

---

## 7. Competitive Positioning

```
                    AI Governance (High)
                          │
            [AgentOS] ────┼──── (Blue Ocean)
                          │
  ──────────────────────────────────────────
  Execution Replay (Low)  │         Execution Replay (High)
                          │
  [LangSmith, W&B]  ──────┼──── [Temporal]
  Log/Experiment Mgmt     │    Workflow Orchestration
                          │
                    AI Governance (Low)
```

---

## 8. 5-Year Financial Targets (USD, millions)

| Year | Revenue | Operating Income |
|------|---------|-----------------|
| 2026 | $0.04M | -$0.04M |
| 2027 | $0.4M | $0.12M |
| 2028 | $1.6M | $0.8M |
| 2029 | $4M | $2.8M |
| 2030 | $8M | $5.2M |

---

---

# Cursor Development Prompts

Paste these prompts into Cursor as needed. Always start with CURSOR-01 when opening a new chat.

---

## [CURSOR-01] Project Context Initialization (Always paste this first in every new chat)

```
You are building AgentOS — an AI Agent Operating System for ODD PLAYGROUND.

## What AgentOS is
AgentOS is a self-evolving infrastructure for running, monitoring, replaying, and governing AI agents. It solves the core problems of:
1. Non-determinism: agents give different outputs for the same input
2. No replay/recovery: when agents fail, you restart from scratch
3. No accountability: no audit trail for AI decisions in regulated industries

## Current codebase
The main repo is `agentos/` with this structure:
- `agents/` — YAML agent configs
- `config/` — settings.py with env var config
- `policies/` — YAML policy files (deny_agents, approval_required_agents)
- `runtime/` — workflow_runner.py (core execution engine)
- `server/` — Flask API server
- `tests/` — test files
- `viewer/` — HTML/JS frontend dashboard
- `workflows/` — YAML workflow definitions
- `main.py` — CLI entrypoint

## What already works (v1)
- YAML workflow runner
- Human-in-the-loop approval gates (CLI + web UI)
- Append-only event log: runs/<run_id>/events.jsonl (schema_version: 1.0)
- Retry from failed step (CLI + dashboard button)
- Multi-tenant base (AGENTOS_TENANT_ID)
- Docker deployment

## Tech stack
- Backend: Python (Flask), Celery, Redis
- Frontend: React (or plain HTML/JS for viewer)
- Data: JSONL event logs, JSON state snapshots, YAML policies
- Infra: Docker, docker-compose
- AI: OpenAI API (OPENAI_API_KEY env var)

## Key concepts
- Run: one execution of a workflow. Has a run_id, events.jsonl, state.json
- Step: one unit within a run. Has an agent, input, requires_approval flag
- Approval Gate: human must click Approve/Deny before step executes
- Policy Engine: YAML-based rules that auto-deny or require approval for certain agents
- Replayable Runtime: every step's state is saved so runs can be replayed exactly
- Reliability Card: auto-generated report of agent trust score + risk analysis

Always keep code modular, well-commented, and follow the existing file structure conventions.
```

---

## [CURSOR-02] Replayable Runtime Upgrade

```
## Task: Upgrade Replayable Runtime in AgentOS

Goal: Make every step's execution state fully snapshotable and replayable.

### Current state
- events.jsonl logs events per run but does not capture full step state
- Retry from failure re-runs from the failed step, but state is not precisely reconstructed

### What to build
1. In `runtime/workflow_runner.py`, add a `StepSnapshot` dataclass that captures:
   - step_id, agent_name, input, output, timestamp
   - all resolved template variables at time of execution
   - tool calls made (if any)
   - LLM prompt + response (only if AGENTOS_LOG_PAYLOADS=true)

2. After each step completes, write snapshot to:
   `runs/<run_id>/snapshots/<step_id>.json`

3. Add a `ReplayRunner` class that:
   - Takes a run_id and optional start_step_id
   - Loads snapshots for all steps before start_step_id (to restore state)
   - Re-executes from start_step_id with the restored context
   - Emits events to a new run_id (so original run is preserved)

4. Expose via CLI:
   `python main.py replay <run_id> --from-step <step_id>`

5. Expose via API:
   POST /api/runs/{run_id}/replay  body: { "from_step": "step_id" }

### Constraints
- Never mutate the original run's data
- All snapshots must be append-only / immutable once written
- Keep backward compatibility with existing events.jsonl schema

Write clean, well-typed Python. Add docstrings to all new classes and functions.
```

---

## [CURSOR-03] Policy Engine Expansion (YAML-based)

```
## Task: Expand the Policy Engine in AgentOS

### Current state
`policies/default.yaml` supports:
- deny_agents: list
- approval_required_agents: list

### What to build
Extend the Policy Engine to support richer rules:

1. New YAML schema in `policies/`:
```yaml
version: "2.0"
rules:
  - id: block-financial-actions
    description: "Block any agent that touches financial data"
    condition:
      agent_tags_include: ["financial", "payment"]
    action: deny
    reason: "Financial actions require compliance review"

  - id: require-approval-high-risk
    condition:
      risk_level_gte: high
    action: require_approval
    notify: ["admin@company.com"]

  - id: rate-limit-external-calls
    condition:
      tool_calls_per_minute_gt: 10
    action: pause_and_alert
```

2. Build `runtime/policy_engine.py`:
   - `PolicyEngine` class that loads and parses the YAML
   - `evaluate(step: StepContext) -> PolicyDecision` method
   - `PolicyDecision` has: action (allow/deny/require_approval/pause), reason, rule_id
   - Support hot-reloading of policy file without restart

3. Integrate into `workflow_runner.py`:
   - Before each step, call `policy_engine.evaluate(step)`
   - If deny: log to audit, skip step, mark run as policy-blocked
   - If require_approval: route to approval gate
   - If pause_and_alert: pause run and emit alert event

4. Add policy violation events to events.jsonl:
   ```json
   {"type": "policy_violation", "rule_id": "...", "action": "deny", "reason": "..."}
   ```

5. Display policy decisions in the dashboard viewer.

Write comprehensive tests in `tests/test_policy_engine.py`.
```

---

## [CURSOR-04] React Dashboard Rebuild (Frontend)

```
## Task: Upgrade AgentOS Dashboard to a production-quality React app

### Current state
`viewer/` contains basic HTML/JS files for run list and detail view.

### What to build
Rebuild as a proper React SPA (scaffold with Vite: `npm create vite@latest dashboard -- --template react`).

#### Pages / Routes
1. `/` — Run List
   - Table: run_id, status (badge), workflow name, start time, step count, project
   - Filter by: status, project, date range
   - "New Run" button → modal to enter workflow path + project

2. `/runs/:run_id` — Run Detail
   - Header: run status, elapsed time, retry button
   - Step Timeline: visual timeline of steps with status icons
     - 🟡 pending_approval → shows Approve / Deny buttons
     - 🔴 failed → shows failure reason + "Retry from here" button
     - ✅ completed
   - Right panel: step detail (input, output, policy decisions)
   - Tab: Audit Log (scrollable events.jsonl viewer)

3. `/insights` — Failure Insights
   - Recent failures grouped by error pattern
   - Suggested fixes per pattern (e.g., "API rate limit → add retry backoff")

4. `/policies` — Policy Manager
   - YAML editor for policies/default.yaml
   - "Test policy against run" dry-run feature

5. `/reliability` — Reliability Cards
   - Per-agent trust score (% of runs completed without policy violations)
   - Risk level distribution chart
   - Downloadable PDF report button

#### Design requirements
- Dark theme, professional developer tool aesthetic
- Use Tailwind CSS
- Monospace font for logs/code (JetBrains Mono or similar)
- Real-time updates via polling (every 3s) or WebSocket if available
- Responsive for 1280px+ (desktop-first)

#### API integration
Base URL: http://localhost:8080
Endpoints needed from backend:
- GET /api/runs
- GET /api/runs/:run_id
- POST /api/runs/:run_id/approve/:step_id
- POST /api/runs/:run_id/deny/:step_id
- POST /api/runs/:run_id/retry
- POST /api/runs/:run_id/replay (new)
- GET /api/policies
- PUT /api/policies
- GET /api/insights/failures
- GET /api/reliability/:agent_name

Build with clean component structure, proper error handling, and loading states.
```

---

## [CURSOR-05] System MRI — Failure Diagnosis Engine

```
## Task: Build System MRI — Failure Diagnosis Engine for AgentOS

### What it does
System MRI analyzes completed or failed runs and produces structured diagnostic reports.
It answers: "Why did this agent fail, and what should change?"

### Build `runtime/system_mri.py`

1. `FailureAnalyzer` class:
   - Input: run_id (reads from runs/<run_id>/events.jsonl)
   - Extracts all failure events
   - Classifies failure type:
     - `api_error` (rate limit, auth, network)
     - `policy_violation` (blocked by policy engine)
     - `approval_denied` (human denied a step)
     - `timeout` (step exceeded time limit)
     - `hallucination_risk` (agent output flagged)
     - `logic_error` (unexpected output format)

2. `DiagnosticReport` dataclass:
   ```python
   @dataclass
   class DiagnosticReport:
       run_id: str
       failure_type: str
       root_cause: str          # human-readable explanation
       affected_steps: list[str]
       suggested_fixes: list[str]  # actionable suggestions
       confidence: float        # 0.0-1.0
       generated_at: str
   ```

3. Pattern matching rules (start rule-based, not LLM):
   - If event contains "rate_limit" → type=api_error, suggest: "Add exponential backoff"
   - If event contains "approval_denied" → type=approval_denied, suggest: "Review step risk level"
   - etc.

4. Optional LLM enhancement (when OPENAI_API_KEY is set):
   - Send failure events to GPT to generate natural language root_cause and suggestions
   - Fall back to rule-based if LLM call fails

5. CLI command:
   `python main.py diagnose <run_id>`
   → prints DiagnosticReport as formatted text

6. API endpoint:
   GET /api/runs/:run_id/diagnosis
   → returns DiagnosticReport as JSON

7. Store report to: `runs/<run_id>/diagnosis.json`

Write tests covering all failure type classifications.
```

---

## [CURSOR-06] Reliability Card Auto-Generation

```
## Task: Build Reliability Card generator for AgentOS

### What it is
A Reliability Card is a one-page trust report for an agent or workflow.
Think of it as a "nutrition label" for AI agents — shows risk profile, compliance status, and historical performance.

### Build `runtime/reliability_card.py`

1. `ReliabilityCardGenerator` class:
   - Input: agent_name (or workflow_path), date_range
   - Reads all runs involving this agent
   - Computes metrics:
     - `success_rate`: completed / total runs
     - `approval_rate`: approved / (approved + denied)
     - `policy_violation_rate`: policy_blocked / total runs
     - `avg_steps_per_run`: average step count
     - `failure_patterns`: top 3 failure types from MRI reports
     - `trust_score`: weighted composite (0–100)

2. `ReliabilityCard` dataclass:
   ```python
   @dataclass
   class ReliabilityCard:
       agent_name: str
       period: str              # e.g. "2026-03-01 to 2026-03-26"
       trust_score: int         # 0-100
       trust_level: str         # "HIGH" / "CONDITIONAL" / "LOW-RISK"
       metrics: dict
       failure_patterns: list[dict]
       recommendations: list[str]
       generated_at: str
   ```

3. Trust level thresholds:
   - 80–100: "HIGH" (safe to deploy without restrictions)
   - 60–79: "CONDITIONAL" (deploy with monitoring)
   - 0–59: "LOW-RISK" (do not deploy / needs review)

4. CLI: `python main.py reliability <agent_name> --days 30`
5. API: GET /api/reliability/:agent_name?days=30
6. Save to: `reports/reliability_<agent_name>_<date>.json`

Nice to have: generate PDF output using reportlab or weasyprint.
```

---

## [CURSOR-07] SDK Packaging (for developer distribution)

```
## Task: Package AgentOS Core as an installable Python SDK

### Goal
Allow any developer to add AgentOS observability to their existing AI agent with 3 lines of code:
```python
from agentos import AgentOS

os = AgentOS(project="my-project", api_key="...")
os.run("workflows/my_workflow.yaml")
```

### Structure to create
```
agentos-sdk/
├── agentos/
│   ├── __init__.py          # exports AgentOS, Step, Policy
│   ├── client.py            # AgentOS client class
│   ├── decorators.py        # @agentos.trace() decorator for existing functions
│   ├── models.py            # Pydantic models for Run, Step, Event
│   └── exceptions.py        # AgentOSError, PolicyViolationError
├── tests/
├── pyproject.toml
└── README.md
```

### Key features of the SDK

1. `@agentos.trace()` decorator:
   ```python
   @agentos.trace(requires_approval=True, risk_level="high")
   def my_agent_function(input: str) -> str:
       # existing code unchanged
       ...
   ```
   → Automatically logs execution, waits for approval if configured, handles retries

2. `AgentOS.run(workflow_path)` — runs a YAML workflow
3. `AgentOS.replay(run_id, from_step)` — replays a run
4. `AgentOS.diagnose(run_id)` — returns DiagnosticReport

### pyproject.toml
```toml
[project]
name = "agentos-sdk"
version = "0.1.0"
description = "AI Agent Operating System — run, replay, govern your AI agents"
requires-python = ">=3.10"
dependencies = ["requests", "pyyaml", "pydantic"]
```

Write comprehensive docstrings. This is the public developer API — clarity matters most.
```

---

## [CURSOR-08] Production Docker Setup

```
## Task: Production-ready Docker setup for AgentOS

### Current state
`docker-compose.yml` exists but is basic.

### What to build
1. `docker-compose.prod.yml` with:
   - `api` service: Flask/FastAPI on port 8080
   - `worker` service: Celery worker (handles async run execution)
   - `redis` service: message broker for Celery
   - `dashboard` service: React build served via nginx on port 3000
   - Named volumes: `agentos_runs`, `agentos_reports`
   - Health checks on all services

2. `Dockerfile.api` (multi-stage):
   - Stage 1: install dependencies
   - Stage 2: production image (no dev deps)
   - Non-root user
   - Proper WORKDIR

3. `Dockerfile.dashboard`:
   - Stage 1: npm build
   - Stage 2: nginx serving static files

4. `nginx.conf`:
   - Serve React SPA (handle client-side routing)
   - Reverse proxy /api/* to api:8080

5. `.env.example`:
   ```
   OPENAI_API_KEY=
   AGENTOS_ADMIN_PASSWORD=
   AGENTOS_SECRET_KEY=
   AGENTOS_LOG_PAYLOADS=false
   AGENTOS_POLICY_PATH=policies/default.yaml
   REDIS_URL=redis://redis:6379/0
   ```

6. `Makefile` with shortcuts:
   ```
   make dev      # docker compose up (dev)
   make prod     # docker compose -f docker-compose.prod.yml up -d
   make logs     # docker compose logs -f
   make shell    # docker compose exec api bash
   ```

Ensure all secrets come from env vars. No hardcoded values anywhere.
```

---

## Recommended Sprint Order

```
Sprint 1 (Start here):
  CURSOR-04 → React dashboard rebuild (demo-ready UI)

Sprint 2:
  CURSOR-02 → Replayable Runtime upgrade (core differentiator)
  CURSOR-03 → Policy Engine expansion

Sprint 3:
  CURSOR-05 → System MRI diagnosis engine
  CURSOR-06 → Reliability Card generation

Sprint 4:
  CURSOR-07 → SDK packaging (open source release)
  CURSOR-08 → Production Docker

Every new Cursor chat:
  → Paste CURSOR-01 first to initialize context
```
