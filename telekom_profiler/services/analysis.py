"""Public service API — thin wrappers over ``ProfilerEngine``."""

from __future__ import annotations

from typing import Mapping

from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.services.engine import ProfilerEngine, get_engine


def profile_customer(data: Mapping[str, float], *, engine: ProfilerEngine | None = None) -> str:
    """
    Build a customer profile markdown string.

    Uses Ollama when ``OLLAMA_ENABLED`` is true; otherwise rule-based rendering.
    For structured output (scoring metadata), use ``engine.profile()`` instead.
    """
    result = (engine or get_engine()).profile(data)
    return result.markdown


def recommend_offer(
    profile_text: str,
    data: Mapping[str, float],
    *,
    engine: ProfilerEngine | None = None,
) -> str:
    """
    Build an offer recommendation markdown string.

    ``profile_text`` must be real profile output (not a UI placeholder).
    """
    return (engine or get_engine()).recommend(profile_text, data)


def profile_customer_structured(
    data: Mapping[str, float],
    *,
    engine: ProfilerEngine | None = None,
) -> ProfileResult:
    """Return a typed ``ProfileResult`` (preferred for new integrations)."""
    return (engine or get_engine()).profile(data)


__all__ = [
    "profile_customer",
    "profile_customer_structured",
    "recommend_offer",
]
