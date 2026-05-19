"""Domain logic: archetypes, profiling, and offer recommendation."""

from telekom_profiler.domain.archetypes import (
    compute_archetype_distances,
    compute_overlays,
)
from telekom_profiler.domain.offers import render_offer_report
from telekom_profiler.domain.profiling import render_profile_report

__all__ = [
    "compute_archetype_distances",
    "compute_overlays",
    "render_offer_report",
    "render_profile_report",
]
