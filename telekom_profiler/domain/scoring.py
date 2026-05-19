"""Build structured ``ScoringResult`` from usage data (shared by rules and LLM paths)."""

from __future__ import annotations

from telekom_profiler.domain.archetypes import (
    compute_archetype_distances,
    compute_overlays,
    confidence_label,
)
from telekom_profiler.domain.models import ArchetypeScore, CustomerUsage, ScoringResult


def build_scoring_result(usage: CustomerUsage) -> ScoringResult:
    """Compute archetype ranking and overlays for the given usage snapshot."""
    data = usage.as_dict()
    distances = compute_archetype_distances(data)
    primary_name, primary_dist = distances[0]
    secondary: ArchetypeScore | None = None
    if len(distances) > 1:
        sec_name, sec_dist = distances[1]
        secondary = ArchetypeScore(sec_name, sec_dist)

    sec_dist_val = secondary.distance if secondary else 0.0
    return ScoringResult(
        primary=ArchetypeScore(primary_name, primary_dist),
        secondary=secondary,
        all_distances=tuple(ArchetypeScore(n, d) for n, d in distances),
        overlays=tuple(compute_overlays(data)),
        confidence=confidence_label(primary_dist, sec_dist_val),
    )
