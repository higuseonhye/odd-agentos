"""AgentOS CLI — run workflows, replay, diagnose, reliability."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentos.config import settings
from agentos.runtime.reliability_card import ReliabilityCardGenerator
from agentos.runtime.replay_runner import ReplayRunner
from agentos.runtime.system_mri import FailureAnalyzer
from agentos.runtime.workflow_runner import WorkflowRunner


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


def main() -> int:
    p = argparse.ArgumentParser(prog="agentos", description="AgentOS CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Execute a workflow YAML")
    r.add_argument("workflow", type=Path, help="Path to workflow file")
    r.set_defaults(func=_cmd_run)

    rp = sub.add_parser("replay", help="Replay a run from a step into a new run id")
    rp.add_argument("run_id")
    rp.add_argument("--from-step", required=True, dest="from_step")
    rp.set_defaults(func=_cmd_replay)

    rt = sub.add_parser(
        "retry",
        help="Retry after failure: new run, re-execute from failed step (or --from-step)",
    )
    rt.add_argument("run_id")
    rt.add_argument("--from-step", dest="from_step", default=None)
    rt.set_defaults(func=_cmd_retry)

    d = sub.add_parser("diagnose", help="System MRI diagnosis for a run")
    d.add_argument("run_id")
    d.set_defaults(func=_cmd_diagnose)

    rel = sub.add_parser("reliability", help="Reliability card for an agent")
    rel.add_argument("agent")
    rel.add_argument("--days", type=int, default=30)
    rel.set_defaults(func=_cmd_reliability)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
