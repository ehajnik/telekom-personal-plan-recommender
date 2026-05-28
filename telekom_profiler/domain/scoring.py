"""Build structured ``ScoringResult`` from usage data (ML or legacy L1 fallback)."""

from __future__ import annotations

import logging

from telekom_profiler.config.profiler_settings import use_ml_scoring
from telekom_profiler.domain.archetypes import (
    compute_archetype_distances,
    compute_overlays,
    confidence_label,
)
from telekom_profiler.domain.models import ArchetypeScore, CustomerUsage, ScoringResult
from telekom_profiler.runtime_context import subscriber_id_var

_logger = logging.getLogger(__name__)


def _legacy_scoring_result(data: dict[str, float]) -> ScoringResult:
    distances = compute_archetype_distances(data)
    primary_name, primary_dist = distances[0]
    secondary: ArchetypeScore | None = None
    if len(distances) > 1:
        sec_name, sec_dist = distances[1]
        secondary = ArchetypeScore(sec_name, sec_dist)

    sec_dist_val = secondary.distance if secondary else 0.0
    legacy_overlays = list(compute_overlays(data))
    return ScoringResult(
        primary=ArchetypeScore(primary_name, primary_dist),
        secondary=secondary,
        all_distances=tuple(ArchetypeScore(n, d) for n, d in distances),
        overlays=tuple(legacy_overlays),
        confidence=confidence_label(primary_dist, sec_dist_val),
        backend="legacy",
    )


def _legacy_fallback(usage: CustomerUsage, reason: str) -> ScoringResult:
    _logger.warning("ML scoring unavailable (%s), using legacy L1 archetypes", reason)
    result = _legacy_scoring_result(usage.as_dict())
    return ScoringResult(
        primary=result.primary,
        secondary=result.secondary,
        all_distances=result.all_distances,
        overlays=result.overlays,
        confidence=result.confidence,
        backend="legacy",
        fallback_reason=reason,
    )


def build_scoring_result(
    usage: CustomerUsage,
    *,
    subscriber_id: str | None = None,
) -> ScoringResult:
    """Compute profile ranking and overlays for the given usage snapshot."""
    sid = subscriber_id or subscriber_id_var.get()
    if use_ml_scoring():
        try:
            from telekom_profiler.ml.features import features_from_usage
            from telekom_profiler.ml.inference import (
                predict_from_features,
                predict_subscriber,
                scoring_result_from_prediction,
            )

            if sid:
                pred = predict_subscriber(str(sid), usage_override=usage)
            else:
                pred = predict_from_features(features_from_usage(usage))
            return scoring_result_from_prediction(pred)
        except FileNotFoundError as exc:
            return _legacy_fallback(usage, f"ml_artifacts_missing: {exc}")
        except KeyError as exc:
            return _legacy_fallback(usage, f"ml_lookup_failed: {exc}")

    return _legacy_scoring_result(usage.as_dict())
