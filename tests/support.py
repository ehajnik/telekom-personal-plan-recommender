"""Shared test helpers."""

from __future__ import annotations

import os


def use_rule_based_profiler() -> None:
    """Force legacy L1 archetypes for deterministic unit tests."""
    os.environ["PROFILER_MODE"] = "rules"
    try:
        from telekom_profiler.ml.inference import clear_artifacts_cache

        clear_artifacts_cache()
    except ImportError:
        pass
