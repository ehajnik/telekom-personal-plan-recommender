"""Domain logic: models, archetypes, profiling, and offer recommendation."""

from telekom_profiler.domain.archetypes import (
    ARCHETYPE_CENTROIDS,
    ARCHETYPE_NAMES,
    compute_archetype_distances,
    compute_overlays,
    usage_slider_maxima,
)
from telekom_profiler.domain.models import (
    ArchetypeScore,
    CustomerUsage,
    ProfileResult,
    ScoringResult,
)
from telekom_profiler.domain.offers import render_offer_report
from telekom_profiler.domain.profiling import render_profile_report
from telekom_profiler.domain.scoring import build_scoring_result

__all__ = [
    "ARCHETYPE_CENTROIDS",
    "ARCHETYPE_NAMES",
    "ArchetypeScore",
    "CustomerUsage",
    "ProfileResult",
    "ScoringResult",
    "build_scoring_result",
    "compute_archetype_distances",
    "compute_overlays",
    "render_offer_report",
    "render_profile_report",
    "usage_slider_maxima",
]
