"""Cross-cutting overlay flags (trajectory and mixed-profile signals)."""

from __future__ import annotations

from collections.abc import Mapping

from telekom_profiler.ml.schema import (
    DATA_TREND_GROWING_MIN,
    DATA_TREND_SHRINKING_MAX,
    LINES_TREND_GROWING_MIN,
    MIXED_PROFILE_RATIO,
    ROAMING_TREND_GROWING_MIN,
    VOICE_TREND_DECLINING_MAX,
)


def compute_ml_overlays(
    row: Mapping[str, float],
    *,
    primary_distance: float,
    secondary_distance: float | None,
) -> list[str]:
    """Overlays from trends and cluster geometry (not cluster assignment)."""
    flags: list[str] = []

    data_t = float(row.get("data_trend", 0))
    voice_t = float(row.get("voice_trend", 0))
    roam_t = float(row.get("roaming_trend", 0))
    lines_t = float(row.get("lines_trend", 0))

    if data_t >= DATA_TREND_GROWING_MIN:
        flags.append("Data appetite growing")
    elif data_t <= DATA_TREND_SHRINKING_MAX:
        flags.append("Data appetite shrinking")

    if voice_t <= VOICE_TREND_DECLINING_MAX:
        flags.append("Voice declining → data migration")

    if roam_t >= ROAMING_TREND_GROWING_MIN:
        flags.append("Roaming increasing")

    if lines_t >= LINES_TREND_GROWING_MIN:
        flags.append("Family fleet growing")

    if (
        secondary_distance is not None
        and primary_distance > 1e-9
        and secondary_distance < MIXED_PROFILE_RATIO * primary_distance
    ):
        flags.append("Mixed profile")

    return flags
