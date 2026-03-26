"""HTTP client for AgentOS API."""

from __future__ import annotations

from typing import Any

import requests

from agentos_sdk.exceptions import AgentOSError
from agentos_sdk.models import Run


class AgentOS:
    """
    Thin client over the AgentOS REST API.

    Example::

        os = AgentOS(project="my-project", base_url="http://localhost:8080")
        os.run("workflows/demo.yaml")
    """

    def __init__(
        self,
        *,
        project: str = "default",
        api_key: str | None = None,
        base_url: str = "http://localhost:8080",
        timeout: float = 60.0,
    ) -> None:
        self.project = project
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(self, method: str, path: str, **kw: Any) -> Any:
        url = f"{self.base_url}{path}"
        r = self._session.request(
            method,
            url,
            headers=self._headers(),
            timeout=self.timeout,
            **kw,
        )
        if r.status_code >= 400:
            raise AgentOSError(f"{method} {path} failed: {r.status_code} {r.text}")
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    def run(self, workflow_path: str) -> str:
        """Start a workflow run; returns ``run_id``."""
        data = self._request(
            "POST",
            "/api/runs",
            json={"workflow_path": workflow_path, "project": self.project},
        )
        if not isinstance(data, dict) or "run_id" not in data:
            raise AgentOSError("Invalid response from /api/runs")
        return str(data["run_id"])

    def replay(self, run_id: str, from_step: str) -> str:
        """Replay from a step into a new run."""
        data = self._request(
            "POST",
            f"/api/runs/{run_id}/replay",
            json={"from_step": from_step},
        )
        if not isinstance(data, dict) or "run_id" not in data:
            raise AgentOSError("Invalid response from replay")
        return str(data["run_id"])

    def diagnose(self, run_id: str) -> dict[str, Any]:
        """Return System MRI :class:`DiagnosticReport` as JSON."""
        data = self._request("GET", f"/api/runs/{run_id}/diagnosis")
        if not isinstance(data, dict):
            raise AgentOSError("Invalid diagnosis payload")
        return data

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Fetch run state, events, and step timeline."""
        return self._request("GET", f"/api/runs/{run_id}")

    def list_runs(self) -> list[Run]:
        rows = self._request("GET", "/api/runs")
        if not isinstance(rows, list):
            return []
        return [Run.model_validate(x) for x in rows]
