"""Column and feature definitions for the private mobile profiling pipeline."""

from __future__ import annotations

from typing import Final

from telekom_profiler.config.app_config import model_config, runtime_config

_MODEL = model_config()
_RUNTIME = runtime_config()
_OVERLAYS = _RUNTIME.get("overlay_thresholds", {})

# Monthly panel grain
SUBSCRIBER_ID_COL: Final[str] = "subscriber_id"
MONTH_COL: Final[str] = "month"

# Raw monthly columns (synthetic CSV)
RAW_NUMERIC_COLS: Final[tuple[str, ...]] = (
    "data_gb",
    "voice_min",
    "sms_count",
    "roaming_days",
    "countries_visited",
    "night_usage_ratio",
    "weekend_usage_ratio",
    "avg_session_mb",
    "active_days",
    "plan_tier",
    "lines_total",
    "lines_active",
)

# Seed archetypes used only for synthetic panel generation.
# Keep this aligned with the fixed five-profile runtime setup.
SEED_ARCHETYPES: Final[tuple[str, ...]] = (
    "light_user",
    "streaming_heavy",
    "voice_centric",
    "travel_heavy",
    "underutilized_overspending",
)

# Human-readable cluster labels assigned post-training via Hungarian matching
# (``train.assign_labels``) against ``LABEL_CANONICAL_CENTROIDS``. When the
# chosen k exceeds the number of named labels, extra clusters receive
# auto-generated ``Profile N`` names with a rules-based signature.
PROFILE_LABELS: Final[tuple[str, ...]] = (
    *tuple(_MODEL.get("profile_labels", [])),
)

PROFILE_EMOJI: Final[dict[str, str]] = dict(_MODEL.get("profile_emoji", {}))

# Subscriber-level means (12-month aggregate)
MEAN_COLS: Final[tuple[str, ...]] = tuple(f"{c}_mean" for c in RAW_NUMERIC_COLS)

# Derived baseline features — used for clustering ONLY.
# NOTE: trend features (data_trend, voice_trend, roaming_trend, lines_trend) are
# intentionally excluded — they capture TRAJECTORY not BASELINE BEHAVIOUR.
DERIVED_BASELINE_COLS: Final[tuple[str, ...]] = (
    "active_line_ratio",
    "roaming_intensity",
    "data_per_active_line",
    "pct_idle_lines",
    "roaming_days_ratio",
    "sms_per_gb",
    "voice_per_active_day",
    "data_per_active_day",
    "session_intensity",
    "evening_peak_share",
    "weekend_share",
    "plan_usage_gap",
    "device_smartphone_share",
)

# Core discriminators for K-Means (subset keeps PoC silhouette ≥ 0.5 on synthetic data)
CLUSTER_FEATURES: Final[tuple[str, ...]] = (
    *tuple(_MODEL.get("cluster_features", [])),
)

TREND_COLS: Final[tuple[str, ...]] = (
    "data_trend",
    "voice_trend",
    "roaming_trend",
    "lines_trend",
)

# Overlay thresholds
MIXED_PROFILE_RATIO: Final[float] = float(_OVERLAYS.get("mixed_profile_ratio", 1.3))
DATA_TREND_GROWING_MIN: Final[float] = float(_OVERLAYS.get("data_trend_growing_min", 0.15))
DATA_TREND_SHRINKING_MAX: Final[float] = float(_OVERLAYS.get("data_trend_shrinking_max", -0.15))
VOICE_TREND_DECLINING_MAX: Final[float] = float(_OVERLAYS.get("voice_trend_declining_max", -0.15))
ROAMING_TREND_GROWING_MIN: Final[float] = float(_OVERLAYS.get("roaming_trend_growing_min", 0.2))
LINES_TREND_GROWING_MIN: Final[float] = float(_OVERLAYS.get("lines_trend_growing_min", 0.1))

# Centroid alignment: which unscaled feature is primary discriminator per label
LABEL_DISCRIMINATORS: Final[dict[str, str]] = dict(_MODEL.get("discriminators", {}))

# Canonical centroid per named label, in the same feature space as ``CLUSTER_FEATURES``.
# Used by ``train.assign_labels`` to solve a globally-optimal label↔cluster assignment
# via ``scipy.optimize.linear_sum_assignment``. Values are midpoints of the synthetic
# archetype ranges plus derived features computed the same way as
# ``features._add_derived_baseline``. Features not listed here are excluded from the
# cost (treated as "don't care" for that label).
LABEL_CANONICAL_CENTROIDS: Final[dict[str, dict[str, float]]] = {
    k: {kk: float(vv) for kk, vv in v.items()}
    for k, v in dict(_MODEL.get("fixed_centroids", {})).items()
}
