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
# Optional ground-truth column written by the synthetic generator (evaluation only;
# never used as a training feature).
SEED_ARCHETYPE_COL: Final[str] = "seed_archetype"

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
    "broad_usage",
)

# Ground-truth mapping seed archetype → runtime profile label (evaluation only).
SEED_TO_PROFILE_LABEL: Final[dict[str, str]] = {
    "light_user": "Light / occasional user",
    "streaming_heavy": "Streaming & data-heavy",
    "voice_centric": "Voice-centric",
    "travel_heavy": "Roaming / travel-heavy",
    "broad_usage": "Broad usage profile",
}

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

# Clustering space (configured in ``app_config.yaml``). Only features that can be computed
# exactly from the six-slider ``CustomerUsage`` input, so batch and UI inference agree.
CLUSTER_FEATURES: Final[tuple[str, ...]] = (
    *tuple(_MODEL.get("cluster_features", [])),
)

# Trend units (computed from the 12-month OLS slope in ``features.build_subscriber_features``):
#   data_trend, voice_trend  → relative change in % per year (same unit as the UI sliders)
#   roaming_trend            → change in roaming days / month over one year
#   lines_trend              → change in active lines over one year
TREND_COLS: Final[tuple[str, ...]] = (
    "data_trend",
    "voice_trend",
    "roaming_trend",
    "lines_trend",
)

# Overlay thresholds
MIXED_PROFILE_RATIO: Final[float] = float(_OVERLAYS.get("mixed_profile_ratio", 1.3))
DATA_TREND_GROWING_MIN: Final[float] = float(_OVERLAYS.get("data_trend_growing_min", 10.0))
DATA_TREND_SHRINKING_MAX: Final[float] = float(_OVERLAYS.get("data_trend_shrinking_max", -10.0))
VOICE_TREND_DECLINING_MAX: Final[float] = float(_OVERLAYS.get("voice_trend_declining_max", -10.0))
ROAMING_TREND_GROWING_MIN: Final[float] = float(_OVERLAYS.get("roaming_trend_growing_min", 2.0))
LINES_TREND_GROWING_MIN: Final[float] = float(_OVERLAYS.get("lines_trend_growing_min", 0.5))

# Canonical anchor per named label in human units (``data_gb_mean``, ``voice_min_mean`` …).
# ``train.assign_labels`` maps each anchor into the clustering space
# (``features.anchor_feature_row``) and solves a globally-optimal label↔cluster assignment
# via ``scipy.optimize.linear_sum_assignment``.
LABEL_CANONICAL_CENTROIDS: Final[dict[str, dict[str, float]]] = {
    k: {kk: float(vv) for kk, vv in v.items()}
    for k, v in dict(_MODEL.get("fixed_centroids", {})).items()
}
