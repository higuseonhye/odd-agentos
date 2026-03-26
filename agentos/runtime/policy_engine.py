"""YAML policy engine with hot reload (mtime-based)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class PolicyAction(str, Enum):
    """Actions a policy rule can mandate."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    PAUSE_AND_ALERT = "pause_and_alert"


@dataclass
class StepContext:
    """Minimal context for evaluating policies before a step runs."""

    step_id: str
    agent_name: str
    agent_tags: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low | medium | high
    tool_calls_per_minute: int = 0


@dataclass
class PolicyDecision:
    """Result of policy evaluation for one step."""

    action: PolicyAction
    reason: str
    rule_id: str | None = None
    notify: list[str] = field(default_factory=list)


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _risk_gte(a: str, b: str) -> bool:
    return _RISK_ORDER.get(a.lower(), 0) >= _RISK_ORDER.get(b.lower(), 0)


def _tags_include(tags: list[str], required: list[str]) -> bool:
    tset = {x.lower() for x in tags}
    return all(r.lower() in tset for r in required)


def _match_condition(step: StepContext, cond: dict[str, Any]) -> bool:
    if not cond:
        return True
    if "agent_tags_include" in cond:
        if not _tags_include(step.agent_tags, list(cond["agent_tags_include"])):
            return False
    if "risk_level_gte" in cond:
        if not _risk_gte(step.risk_level, str(cond["risk_level_gte"])):
            return False
    if "tool_calls_per_minute_gt" in cond:
        if step.tool_calls_per_minute <= int(cond["tool_calls_per_minute_gt"]):
            return False
    return True


def _parse_action(raw: str) -> PolicyAction:
    mapping = {
        "allow": PolicyAction.ALLOW,
        "deny": PolicyAction.DENY,
        "require_approval": PolicyAction.REQUIRE_APPROVAL,
        "pause_and_alert": PolicyAction.PAUSE_AND_ALERT,
    }
    return mapping.get(raw.lower(), PolicyAction.ALLOW)


class PolicyEngine:
    """Loads policy YAML and evaluates steps. Reloads when file mtime changes."""

    def __init__(self, policy_path: str | Path) -> None:
        self._path = Path(policy_path)
        self._mtime: float = 0.0
        self._data: dict[str, Any] = {}

    def _load_if_stale(self) -> None:
        if not self._path.is_file():
            self._data = {"version": "2.0", "deny_agents": [], "approval_required_agents": [], "rules": []}
            return
        mtime = self._path.stat().st_mtime
        if mtime != self._mtime or not self._data:
            with self._path.open("r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
            self._mtime = mtime

    def reload(self) -> None:
        """Force reload from disk."""
        self._mtime = 0.0
        self._data = {}
        self._load_if_stale()

    def evaluate(self, step: StepContext) -> PolicyDecision:
        """
        Evaluate policies for a step. First matching v2 rule wins (deny > pause > require_approval).
        Then v1 deny_agents / approval_required_agents.
        """
        self._load_if_stale()
        data = self._data

        for rule in data.get("rules") or []:
            cond = rule.get("condition") or {}
            if not _match_condition(step, cond):
                continue
            action = _parse_action(str(rule.get("action", "allow")))
            if action == PolicyAction.ALLOW:
                continue
            return PolicyDecision(
                action=action,
                reason=str(rule.get("reason", "")),
                rule_id=rule.get("id"),
                notify=list(rule.get("notify") or []),
            )

        deny = {str(x).lower() for x in (data.get("deny_agents") or [])}
        if step.agent_name.lower() in deny:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="Agent on deny_agents list",
                rule_id="legacy:deny_agents",
            )

        appr = {str(x).lower() for x in (data.get("approval_required_agents") or [])}
        if step.agent_name.lower() in appr:
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason="Agent on approval_required_agents list",
                rule_id="legacy:approval_required_agents",
            )

        return PolicyDecision(action=PolicyAction.ALLOW, reason="", rule_id=None)
