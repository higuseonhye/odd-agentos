"""Central logging setup for the API process."""

from __future__ import annotations

import logging
import sys

from agentos.config import settings


def configure_logging() -> None:
    """Idempotent root logger configuration (structured for production)."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        ),
    )
    root.setLevel(level)
    root.addHandler(handler)
