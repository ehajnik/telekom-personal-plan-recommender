"""Consumer archetype scoring and overlay detection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from telekom_profiler.config.sliders import USAGE_SLIDERS
from telekom_profiler.config.thresholds import (
    BUDGET_DATA_GB_MAX,
    BUDGET_ROAMING_DAYS_MAX,
    BUDGET_VOICE_MIN_MAX,
    CONFIDENCE_HIGH_RATIO_MIN,
    CONFIDENCE_MEDIUM_RATIO_MIN,
    DATA_TREND_GROWTH_MIN,
    ROAMING_HEAVY_DAYS_MIN,
    VOICE_TREND_DECLINE_MAX,
)

ARCHETYPE_NAMES: Final[tuple[str, ...]] = (
    "Streamer",
    "Chatterbox",
    "Essential",
    "Roamer",
    "Messenger",
)

ARCHETYPE_CENTROIDS: Final[dict[str, tuple[float, float, float, float]]] = {
    "Streamer": (100.0, 150.0, 20.0, 3.0),
    "Chatterbox": (12.0, 2000.0, 80.0, 2.0),
    "Essential": (8.0, 200.0, 30.0, 1.0),
    "Roamer": (35.0, 400.0, 25.0, 15.0),
    "Messenger": (25.0, 100.0, 200.0, 1.0),
}

_USAGE_KEYS: Final[tuple[str, ...]] = (
    "data_gb",
    "voice_min",
    "sms_count",
    "roaming_days",
)


def usage_slider_maxima() -> dict[str, float]:
    """Upper bounds from UI slider config (single source of truth)."""
    return {key: float(spec[2]) for key, spec in USAGE_SLIDERS.items()}


def normalize_usage(data: Mapping[str, float]) -> tuple[float, float, float, float]:
    maxima = usage_slider_maxima()
    return cast(
        tuple[float, float, float, float],
        tuple(float(data[key]) / maxima[key] for key in _USAGE_KEYS),
    )


def _centroid_distance(
    point: tuple[float, float, float, float],
    centroid: tuple[float, float, float, float],
) -> float:
    return sum(abs(a - b) for a, b in zip(point, centroid, strict=True))


def compute_archetype_distances(data: Mapping[str, float]) -> list[tuple[str, float]]:
    point = normalize_usage(data)
    scored: list[tuple[str, float]] = []
    for name in ARCHETYPE_NAMES:
        centroid_dict = dict(zip(_USAGE_KEYS, ARCHETYPE_CENTROIDS[name], strict=True))
        scored.append((name, _centroid_distance(point, normalize_usage(centroid_dict))))
    return sorted(scored, key=lambda item: item[1])


def compute_overlays(data: Mapping[str, float]) -> list[str]:
    overlays: list[str] = []
    if data.get("data_trend", 0) > DATA_TREND_GROWTH_MIN:
        overlays.append("Data growth (rising data usage trend)")
    if data.get("voice_trend", 0) < VOICE_TREND_DECLINE_MAX:
        overlays.append("Voice decline (falling voice usage trend)")
    if data.get("roaming_days", 0) >= ROAMING_HEAVY_DAYS_MIN:
        overlays.append("Roaming-heavy (frequent days abroad)")
    if (
        data["data_gb"] < BUDGET_DATA_GB_MAX
        and data["voice_min"] < BUDGET_VOICE_MIN_MAX
        and data["roaming_days"] <= BUDGET_ROAMING_DAYS_MAX
    ):
        overlays.append("Budget-sensitive (low overall usage)")
    return overlays


def confidence_label(primary_score: float, secondary_score: float) -> str:
    if secondary_score <= 0:
        return "High"
    ratio = (secondary_score - primary_score) / secondary_score
    if ratio > CONFIDENCE_HIGH_RATIO_MIN:
        return "High"
    if ratio > CONFIDENCE_MEDIUM_RATIO_MIN:
        return "Medium"
    return "Low"
