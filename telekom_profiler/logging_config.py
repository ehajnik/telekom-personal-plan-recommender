"""Application logging setup."""

from __future__ import annotations

import logging
import os


def configure_logging(level: int | None = None) -> None:
    """Configure root logger for the profiler (idempotent)."""
    log_level = level
    if log_level is None:
        env = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, env, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
