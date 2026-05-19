"""
Provider protocols for profiling and offer generation.

Implement these interfaces to plug in segmentation APIs, PCM catalog services,
or alternate LLM backends without changing the Gradio UI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from telekom_profiler.domain.models import CustomerUsage, ProfileResult


@runtime_checkable
class ProfileProvider(Protocol):
    """Produces a customer profile from usage data."""

    def profile(self, usage: CustomerUsage) -> ProfileResult:
        """Return a profile artefact (markdown + optional scoring metadata)."""
        ...


@runtime_checkable
class OfferProvider(Protocol):
    """Produces a tariff recommendation from a profile and usage context."""

    def recommend(self, profile: ProfileResult, usage: CustomerUsage) -> str:
        """Return offer markdown for display or downstream systems."""
        ...
