"""Consumer archetype scoring and overlay detection."""

from __future__ import annotations

from typing import Final

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

_SLIDER_MAX: Final[dict[str, float]] = {
    "data_gb": 150.0,
    "voice_min": 3000.0,
    "sms_count": 500.0,
    "roaming_days": 30.0,
}


def normalize_usage(data: dict[str, float]) -> tuple[float, float, float, float]:
    return tuple(data[key] / _SLIDER_MAX[key] for key in _USAGE_KEYS)


def _centroid_distance(
    point: tuple[float, float, float, float],
    centroid: tuple[float, float, float, float],
) -> float:
    return sum(abs(a - b) for a, b in zip(point, centroid, strict=True))


def compute_archetype_distances(data: dict[str, float]) -> list[tuple[str, float]]:
    point = normalize_usage(data)
    scored: list[tuple[str, float]] = []
    for name in ARCHETYPE_NAMES:
        centroid_dict = dict(zip(_USAGE_KEYS, ARCHETYPE_CENTROIDS[name], strict=True))
        scored.append((name, _centroid_distance(point, normalize_usage(centroid_dict))))
    return sorted(scored, key=lambda item: item[1])


def compute_overlays(data: dict[str, float]) -> list[str]:
    overlays: list[str] = []
    if data.get("data_trend", 0) > 10:
        overlays.append("Data growth (rising data usage trend)")
    if data.get("voice_trend", 0) < -10:
        overlays.append("Voice decline (falling voice usage trend)")
    if data.get("roaming_days", 0) >= 8:
        overlays.append("Roaming-heavy (frequent days abroad)")
    if data["data_gb"] < 12 and data["voice_min"] < 300 and data["roaming_days"] <= 2:
        overlays.append("Budget-sensitive (low overall usage)")
    return overlays


def confidence_label(primary_score: float, secondary_score: float) -> str:
    if secondary_score <= 0:
        return "High"
    ratio = (secondary_score - primary_score) / secondary_score
    if ratio > 0.3:
        return "High"
    if ratio > 0.15:
        return "Medium"
    return "Low"
