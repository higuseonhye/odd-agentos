"""Environment-driven configuration for AgentOS (dev + production)."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_path(key: str, default: Path) -> Path:
    v = os.environ.get(key)
    return Path(v).expanduser() if v else default


def _env_int(key: str, default: int) -> int:
    v = os.environ.get(key)
    if v is None or not v.strip():
        return default
    try:
        return int(v.strip(), 10)
    except ValueError:
        return default


def _cors_origins() -> list[str] | None:
    """
    Comma-separated allowed origins for CORS (e.g. ``https://app.example.com``).
    If unset in development, all origins are allowed. In production, defaults to none
    (same-origin only unless you set this).
    """
    raw = os.environ.get("AGENTOS_CORS_ORIGINS", "").strip()
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


# --- Core paths
RUNS_DIR = _env_path("AGENTOS_RUNS_DIR", _REPO_ROOT / "runs")
REPORTS_DIR = _env_path("AGENTOS_REPORTS_DIR", _REPO_ROOT / "reports")
POLICY_PATH = _env_path(
    "AGENTOS_POLICY_PATH",
    _REPO_ROOT / "policies" / "default.yaml",
)

# --- Identity & secrets
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
# If true, workflow steps always use the deterministic stub (ignore OPENAI_API_KEY).
AGENTOS_FORCE_STUB = _env_bool("AGENTOS_FORCE_STUB", False)
AGENTOS_LOG_PAYLOADS = _env_bool("AGENTOS_LOG_PAYLOADS", False)
AGENTOS_TENANT_ID = os.environ.get("AGENTOS_TENANT_ID", "default")
SECRET_KEY = os.environ.get("AGENTOS_SECRET_KEY", "dev-change-me")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# --- Runtime mode: development | production
AGENTOS_ENV = os.environ.get("AGENTOS_ENV", "development").strip().lower()
IS_PRODUCTION = AGENTOS_ENV == "production"

# --- HTTP API (Flask dev server; production should use gunicorn + this bind)
API_HOST = os.environ.get("AGENTOS_API_HOST", "0.0.0.0")
API_PORT = _env_int("AGENTOS_API_PORT", 8080)
FLASK_DEBUG = _env_bool("FLASK_DEBUG", default=not IS_PRODUCTION)

# --- Logging
LOG_LEVEL = os.environ.get("AGENTOS_LOG_LEVEL", "INFO" if IS_PRODUCTION else "DEBUG")

# --- CORS (see _cors_origins)
CORS_ORIGINS = _cors_origins()
