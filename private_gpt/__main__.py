"""PrivateGPT FastAPI service entrypoint.

This module is executed via `python -m private_gpt` (see Dockerfile and tooling).

It must be robust in environments where:
1) The orchestrator injects the listening port via the `PORT` environment variable
   (common for PaaS/preview systems).
2) Optional UI dependencies (Gradio) may not be installed, but the API should still
   start and become ready.
"""

from __future__ import annotations

import logging
import os

import uvicorn

from private_gpt.settings.settings import settings

logger = logging.getLogger(__name__)


def _parse_int_env(var_name: str) -> int | None:
    """Parse an int environment variable. Returns None if unset/blank/invalid."""
    raw = os.environ.get(var_name)
    if raw is None or not str(raw).strip():
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; falling back to settings.", var_name, raw)
        return None


def _parse_bool_env(var_name: str) -> bool | None:
    """Parse a bool env var. Returns None if unset/blank."""
    raw = os.environ.get(var_name)
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _apply_env_overrides() -> None:
    """Apply environment overrides to avoid startup failures in minimal installs.

    Contract:
      - If PGPT_UI_ENABLED is set to a falsey value, force-disable the UI at runtime
        by setting `UI_ENABLED=false` for YAML envvar expansion.
      - This keeps behavior centralized (settings.yaml uses env expansion already).
    """
    ui_enabled = _parse_bool_env("PGPT_UI_ENABLED")
    if ui_enabled is False:
        # settings.yaml reads `ui.enabled` as a literal boolean (not env-expanded),
        # so we need a runtime escape hatch. The launcher checks settings.ui.enabled,
        # thus we also provide a secondary override consumed by launcher (see patch there).
        os.environ.setdefault("PGPT_UI_ENABLED_EFFECTIVE", "false")


_apply_env_overrides()

# NOTE: Importing/creating the app triggers settings loading + DI setup, and may mount
# optional UI. Ensure env overrides are applied *before* this import.
from private_gpt.main import app

# Prefer the platform-injected PORT (preview systems), otherwise use settings.
port = _parse_int_env("PORT") or settings().server.port
host = os.environ.get("HOST", "0.0.0.0")

logger.info("Starting PrivateGPT API server on %s:%s", host, port)

# Set log_config=None to not use uvicorn's logging configuration and use ours instead.
# https://github.com/tiangolo/fastapi/discussions/7457#discussioncomment-5141108
uvicorn.run(app, host=host, port=port, log_config=None)
