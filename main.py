"""AgentOS CLI — run workflows, replay, diagnose, reliability, init."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from agentos.config import settings
from agentos.runtime.reliability_card import ReliabilityCardGenerator
from agentos.runtime.replay_runner import ReplayRunner
from agentos.runtime.system_mri import FailureAnalyzer
from agentos.runtime.workflow_runner import WorkflowRunner

# ---------------------------------------------------------------------------
# Init templates
# ---------------------------------------------------------------------------

_SAMPLE_WORKFLOW = """\
name: sample
steps:
  - id: greet
    agent: greeter
    agent_tags: []
    risk_level: low
    input: "world"
    requires_approval: false
  - id: summarize
    agent: summarizer
    agent_tags: []
    risk_level: medium
    input: "Summarize: hello"
    requires_approval: true
"""

_DEFAULT_POLICY = """\
# AgentOS Policy — schema v2.0
version: "2.0"

deny_agents: []
approval_required_agents: []

rules:
  - id: require-approval-high-risk
    condition:
      risk_level_gte: high
    action: require_approval
"""

_SAMPLE_ENV = """\
# Copy to .env and fill in values (never commit real keys)
OPENAI_API_KEY=
AGENTOS_FORCE_STUB=false
AGENTOS_SECRET_KEY=change-me
AGENTOS_ENV=development
"""


def _cmd_init(args: argparse.Namespace) -> int:
    """Scaffold a new AgentOS project in the current directory."""
    target = Path(args.dir).resolve()
    target.mkdir(parents=True, exist_ok=True)

    created: list[str] = []

    def _write(rel: str, content: str) -> None:
        p = target / rel
        if p.exists() and not args.force:
            print(f"  skip   {rel}  (already exists; use --force to overwrite)")
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        created.append(rel)
        print(f"  create {rel}")

    print(f"\nInitialising AgentOS project in {target}\n")

    _write("workflows/sample.yaml", _SAMPLE_WORKFLOW)
    _write("policies/default.yaml", _DEFAULT_POLICY)
    _write(".env.example", _SAMPLE_ENV)

    # Create empty run/report dirs so the server starts cleanly
    for d in ("runs", "reports"):
        (target / d).mkdir(exist_ok=True)

    print(f"\n✓ Done — {len(created)} file(s) created.\n")
    print("Next steps:\n")
    print("  1. Start the API server:")
    print("       python -m agentos.server\n")
    print("  2. Open the dashboard:")
    print("       http://localhost:8080/api/health\n")
    print("  3. Run the sample workflow:")
    print("       agentos run workflows/sample.yaml\n")
    return 0


# ---------------------------------------------------------------------------
# Existing commands
# ---------------------------------------------------------------------------

def _cmd_run(args: argparse.Namespace) -> int:
    runner = WorkflowRunner()
    rid = runner.start_run(args.workflow)
    print(rid)
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    rr = ReplayRunner()
    new_id = rr.replay(args.run_id, args.from_step)
    print(new_id)
    return 0


def _cmd_retry(args: argparse.Namespace) -> int:
    rr = ReplayRunner()
    if args.from_step:
        new_id = rr.replay(args.run_id, args.from_step)
    else:
        new_id = rr.retry_after_failure(args.run_id)
    print(new_id)
    return 0


def _cmd_diagnose(args: argparse.Namespace) -> int:
    rep = FailureAnalyzer(args.run_id).analyze()
    print(json.dumps(rep.to_dict(), indent=2))
    return 0


def _cmd_reliability(args: argparse.Namespace) -> int:
    card = ReliabilityCardGenerator(args.agent, days=args.days).generate()
    print(json.dumps(card.to_dict(), indent=2))
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(prog="agentos", description="AgentOS CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # init
    i = sub.add_parser("init", help="Scaffold a new AgentOS project")
    i.add_argument(
        "dir",
        nargs="?",
        default=".",
        help="Target directory (default: current directory)",
    )
    i.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    i.set_defaults(func=_cmd_init)

    # run
    r = sub.add_parser("run", help="Execute a workflow YAML")
    r.add_argument("workflow", type=Path, help="Path to workflow file")
    r.set_defaults(func=_cmd_run)

    # replay
    rp = sub.add_parser("replay", help="Replay a run from a step into a new run id")
    rp.add_argument("run_id")
    rp.add_argument("--from-step", required=True, dest="from_step")
    rp.set_defaults(func=_cmd_replay)

    # retry
    rt = sub.add_parser(
        "retry",
        help="Retry after failure: new run, re-execute from failed step",
    )
    rt.add_argument("run_id")
    rt.add_argument("--from-step", dest="from_step", default=None)
    rt.set_defaults(func=_cmd_retry)

    # diagnose
    d = sub.add_parser("diagnose", help="System MRI diagnosis for a run")
    d.add_argument("run_id")
    d.set_defaults(func=_cmd_diagnose)

    # reliability
    rel = sub.add_parser("reliability", help="Reliability card for an agent")
    rel.add_argument("agent")
    rel.add_argument("--days", type=int, default=30)
    rel.set_defaults(func=_cmd_reliability)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
