"""Tests for agentos_sdk HTTP client."""

from unittest.mock import MagicMock, patch

import pytest

from agentos_sdk.client import AgentOS


@patch("agentos_sdk.client.requests.Session")
def test_run_returns_run_id(mock_session_cls: MagicMock) -> None:
    sess = MagicMock()
    mock_session_cls.return_value = sess
    r = MagicMock()
    r.status_code = 201
    r.content = b'{"run_id":"abc"}'
    r.json.return_value = {"run_id": "abc"}
    sess.request.return_value = r

    c = AgentOS(base_url="http://test")
    assert c.run("workflows/x.yaml") == "abc"


@patch("agentos_sdk.client.requests.Session")
def test_diagnose(mock_session_cls: MagicMock) -> None:
    sess = MagicMock()
    mock_session_cls.return_value = sess
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"run_id": "x", "failure_type": "unknown"}
    sess.request.return_value = r

    c = AgentOS(base_url="http://test")
    d = c.diagnose("run1")
    assert d["failure_type"] == "unknown"
