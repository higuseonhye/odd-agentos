"""Optional tracing decorator (logs to stdout; wire to HTTP in production)."""

from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def trace(
    *,
    requires_approval: bool = False,
    risk_level: str = "low",
) -> Callable[[F], F]:
    """
    Mark a function for AgentOS-style tracing.

    This stub records timing and flags; connect to :class:`agentos_sdk.client.AgentOS`
    in your app to POST runs to the control plane.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            sig = inspect.signature(fn)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            print(
                f"[agentos.trace] {fn.__name__} risk={risk_level} "
                f"approval={requires_approval} args={dict(bound.arguments)}",
            )
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                print(f"[agentos.trace] {fn.__name__} done in {elapsed:.1f}ms")

        return wrapper  # type: ignore[return-value]

    return decorator
