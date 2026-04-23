"""Optional OpenAI execution for workflow steps (stub when disabled or on failure)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from agentos.config import settings
from agentos.observability import obs

log = logging.getLogger(__name__)


def _model_name() -> str:
    return os.environ.get("AGENTOS_OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def run_openai_chat(
    agent_name: str,
    user_input: Any,
    *,
    log_payloads: bool = False,
) -> tuple[str, str | None, str | None]:
    """
    Call OpenAI Chat Completions.

    Returns ``(text_output, prompt_for_snapshot, response_for_snapshot)``.
    When ``log_payloads`` is false, the last two are short placeholders for audit only.
    """
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai package is required for LLM execution") from e

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    system = (
        f"You are the agent `{agent_name}` in AgentOS. "
        "Reply concisely with a single useful answer. No markdown unless asked."
    )
    user = str(user_input)
    model = _model_name()

    _t0 = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        obs.record_llm_call(
            model=model,
            policy=agent_name,
            latency_ms=(time.perf_counter() - _t0) * 1000,
            status="success",
            tokens_in=resp.usage.prompt_tokens,
            tokens_out=resp.usage.completion_tokens,
        )
    except Exception as exc:
        obs.record_llm_call(
            model=model,
            policy=agent_name,
            latency_ms=(time.perf_counter() - _t0) * 1000,
            status="error",
            error=str(exc),
        )
        raise

    choice = resp.choices[0].message
    text = (choice.content or "").strip()
    out = text or f"[{agent_name}] (empty model output)"
    if log_payloads:
        prompt_log = f"[model={model}]\n--- system ---\n{system}\n--- user ---\n{user}"
        response_log = text
    else:
        prompt_log = f"[model={model}] chars system={len(system)} user={len(user)}"
        response_log = f"[omitted set AGENTOS_LOG_PAYLOADS=true for full text]"
    return out, prompt_log, response_log


def should_use_openai() -> bool:
    """Use OpenAI when key is set and execution is not forced to stub."""
    if settings.AGENTOS_FORCE_STUB:
        return False
    return bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())