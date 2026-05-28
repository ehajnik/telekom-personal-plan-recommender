"""Profiler mode: ML artifacts vs legacy rule-based archetypes."""

from __future__ import annotations

import os
from typing import Final, Literal

from dotenv import load_dotenv

from telekom_profiler.paths import ARTIFACTS_DIR, REPO_ROOT

load_dotenv(REPO_ROOT / ".env")

ProfilerMode = Literal["auto", "ml", "rules"]

PROFILER_MODE: Final[str] = os.getenv("PROFILER_MODE", "auto").lower()


def artifacts_available() -> bool:
    """True when trained K-Means artifacts exist."""
    required = (
        ARTIFACTS_DIR / "label_map.json",
        ARTIFACTS_DIR / "profile_characteristics.json",
        ARTIFACTS_DIR / "frozen_centroids.json",
    )
    return all(p.is_file() for p in required)


def effective_profiler_mode() -> ProfilerMode:
    """Resolve ``auto`` to ``ml`` when artifacts exist, else ``rules``."""
    mode = os.getenv("PROFILER_MODE", PROFILER_MODE).lower()
    if mode == "auto":
        return "ml" if artifacts_available() else "rules"
    if mode in ("ml", "rules"):
        return mode  # type: ignore[return-value]
    return "ml" if artifacts_available() else "rules"


def use_ml_scoring() -> bool:
    return effective_profiler_mode() == "ml"
