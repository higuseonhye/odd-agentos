"""Pydantic models for runs, steps, and events."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Step(BaseModel):
    """A workflow step as returned by the API."""

    id: str
    agent: str | None = None
    status: str = "pending"
    requires_approval: bool = False
    detail: dict[str, Any] | None = None


class Run(BaseModel):
    """Run summary or detail envelope."""

    run_id: str
    status: str | None = None
    workflow_name: str | None = None
    started_at: str | None = None
    step_count: int | None = None


class Event(BaseModel):
    """One line from events.jsonl."""

    type: str
    schema_version: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Event:
        known = {"type", "schema_version"}
        extra = {k: v for k, v in d.items() if k not in known}
        return cls(type=str(d.get("type", "")), schema_version=d.get("schema_version"), data=extra)
