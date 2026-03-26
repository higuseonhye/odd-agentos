"""LLM step gating (stub vs OpenAI)."""

import pytest

from agentos.config import settings as st
from agentos.runtime import llm_step


def test_stub_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setattr(st, "OPENAI_API_KEY", "")
    monkeypatch.setattr(st, "AGENTOS_FORCE_STUB", False)
    assert llm_step.should_use_openai() is False


def test_stub_when_forced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(st, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(st, "AGENTOS_FORCE_STUB", True)
    assert llm_step.should_use_openai() is False


def test_openai_when_key_and_not_forced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(st, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(st, "AGENTOS_FORCE_STUB", False)
    assert llm_step.should_use_openai() is True
