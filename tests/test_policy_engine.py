"""Tests for PolicyEngine and failure classification."""

import json
from pathlib import Path

import pytest

from agentos.runtime.policy_engine import PolicyAction, PolicyEngine, StepContext


def test_deny_by_agent_tags(tmp_path: Path) -> None:
    p = tmp_path / "pol.yaml"
    p.write_text(
        """
version: "2.0"
deny_agents: []
approval_required_agents: []
rules:
  - id: block-financial
    condition:
      agent_tags_include: ["financial"]
    action: deny
    reason: blocked
""",
        encoding="utf-8",
    )
    eng = PolicyEngine(p)
    d = eng.evaluate(
        StepContext(
            step_id="s1",
            agent_name="x",
            agent_tags=["financial", "other"],
            risk_level="low",
        ),
    )
    assert d.action == PolicyAction.DENY
    assert d.rule_id == "block-financial"


def test_require_approval_high_risk(tmp_path: Path) -> None:
    p = tmp_path / "pol.yaml"
    p.write_text(
        """
version: "2.0"
rules:
  - id: high
    condition:
      risk_level_gte: high
    action: require_approval
    reason: risky
""",
        encoding="utf-8",
    )
    eng = PolicyEngine(p)
    d = eng.evaluate(
        StepContext(step_id="s1", agent_name="a", risk_level="high"),
    )
    assert d.action == PolicyAction.REQUIRE_APPROVAL


def test_legacy_deny_list(tmp_path: Path) -> None:
    p = tmp_path / "pol.yaml"
    p.write_text(
        """
version: "1.0"
deny_agents: ["badbot"]
approval_required_agents: []
rules: []
""",
        encoding="utf-8",
    )
    eng = PolicyEngine(p)
    d = eng.evaluate(StepContext(step_id="s1", agent_name="badbot"))
    assert d.action == PolicyAction.DENY


def test_system_mri_rule_based(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentos.config import settings as st
    from agentos.runtime import system_mri

    monkeypatch.setattr(st, "RUNS_DIR", tmp_path)
    run_id = "r1"
    rd = tmp_path / run_id
    rd.mkdir()
    (rd / "events.jsonl").write_text(
        json.dumps({"type": "policy_violation", "step_id": "a"}) + "\n",
        encoding="utf-8",
    )
    rep = system_mri.FailureAnalyzer(run_id).analyze()
    assert rep.failure_type == "policy_violation"
    assert rep.affected_steps
