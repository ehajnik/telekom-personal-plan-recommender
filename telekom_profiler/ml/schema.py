"""Column and feature definitions for the private mobile profiling pipeline."""

from __future__ import annotations

from typing import Final

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

# Seven seed archetypes used only in synthetic generation (K-Means collapses to k=5)
SEED_ARCHETYPES: Final[tuple[str, ...]] = (
    "light_user",
    "streaming_heavy",
    "international_traveler",
    "voice_senior",
    "family_multiline",
    "price_sensitive",
    "power_user_5g",
)

# Five human-readable cluster labels (assigned post-training via centroid inspection)
PROFILE_LABELS: Final[tuple[str, ...]] = (
    "Light / occasional user",
    "Streaming & data-heavy",
    "Voice-centric",
    "Roaming / travel-heavy",
    "Underutilized / overspending",
)

PROFILE_EMOJI: Final[dict[str, str]] = {
    "Light / occasional user": "🌱",
    "Streaming & data-heavy": "📺",
    "Voice-centric": "📞",
    "Roaming / travel-heavy": "✈️",
    "Underutilized / overspending": "💤",
}

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
    "data_gb_mean",
    "voice_min_mean",
    "sms_count_mean",
    "roaming_days_mean",
    "countries_visited_mean",
    "active_days_mean",
    "avg_session_mb_mean",
    "lines_total_mean",
    "lines_active_mean",
    "plan_tier_mean",
    "active_line_ratio",
    "roaming_intensity",
    "data_per_active_line",
    "pct_idle_lines",
    "session_intensity",
    "plan_usage_gap",
)

TREND_COLS: Final[tuple[str, ...]] = (
    "data_trend",
    "voice_trend",
    "roaming_trend",
    "lines_trend",
)

# Overlay thresholds
MIXED_PROFILE_RATIO: Final[float] = 1.3
DATA_TREND_GROWING_MIN: Final[float] = 0.15
DATA_TREND_SHRINKING_MAX: Final[float] = -0.15
VOICE_TREND_DECLINING_MAX: Final[float] = -0.15
ROAMING_TREND_GROWING_MIN: Final[float] = 0.2
LINES_TREND_GROWING_MIN: Final[float] = 0.1

# Centroid alignment: which unscaled feature is primary discriminator per label
LABEL_DISCRIMINATORS: Final[dict[str, str]] = {
    "Light / occasional user": "data_gb_mean",
    "Streaming & data-heavy": "data_gb_mean",
    "Voice-centric": "voice_min_mean",
    "Roaming / travel-heavy": "roaming_intensity",
    "Underutilized / overspending": "pct_idle_lines",
}
