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

# Seven seed archetypes used only in synthetic generation. The trainer chooses
# k via elbow + silhouette over ``[k_min, k_max]`` (default ``[2, 10]``); on the
# standard panel auto-selection settles around k = 5-6 depending on size and
# seed, and the named ``PROFILE_LABELS`` are mapped to clusters via
# ``train.assign_labels`` regardless of the chosen k.
SEED_ARCHETYPES: Final[tuple[str, ...]] = (
    "light_user",
    "streaming_heavy",
    "international_traveler",
    "voice_senior",
    "family_multiline",
    "price_sensitive",
    "power_user_5g",
)

# Human-readable cluster labels assigned post-training via Hungarian matching
# (``train.assign_labels``) against ``LABEL_CANONICAL_CENTROIDS``. When the
# chosen k exceeds the number of named labels, extra clusters receive
# auto-generated ``Profile N`` names with a rules-based signature.
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

# Canonical centroid per named label, in the same feature space as ``CLUSTER_FEATURES``.
# Used by ``train.assign_labels`` to solve a globally-optimal label↔cluster assignment
# via ``scipy.optimize.linear_sum_assignment``. Values are midpoints of the synthetic
# archetype ranges plus derived features computed the same way as
# ``features._add_derived_baseline``. Features not listed here are excluded from the
# cost (treated as "don't care" for that label).
LABEL_CANONICAL_CENTROIDS: Final[dict[str, dict[str, float]]] = {
    "Light / occasional user": {
        "data_gb_mean": 1.5,
        "voice_min_mean": 50.0,
        "sms_count_mean": 15.0,
        "roaming_days_mean": 0.25,
        "countries_visited_mean": 0.25,
        "lines_total_mean": 1.0,
        "lines_active_mean": 1.0,
        "plan_tier_mean": 1.0,
        "active_line_ratio": 1.0,
        "pct_idle_lines": 0.0,
        "roaming_intensity": 0.002,
        "data_per_active_line": 1.5,
        "session_intensity": 7.5,
    },
    "Streaming & data-heavy": {
        "data_gb_mean": 117.0,
        "voice_min_mean": 165.0,
        "sms_count_mean": 22.0,
        "roaming_days_mean": 0.5,
        "countries_visited_mean": 0.5,
        "lines_total_mean": 1.0,
        "lines_active_mean": 1.0,
        "plan_tier_mean": 4.5,
        "active_line_ratio": 1.0,
        "pct_idle_lines": 0.0,
        "roaming_intensity": 0.008,
        "data_per_active_line": 117.0,
        "session_intensity": 70200.0,
    },
    "Voice-centric": {
        "data_gb_mean": 4.5,
        "voice_min_mean": 1800.0,
        "sms_count_mean": 37.0,
        "roaming_days_mean": 1.0,
        "countries_visited_mean": 0.5,
        "lines_total_mean": 1.0,
        "lines_active_mean": 1.0,
        "plan_tier_mean": 1.5,
        "active_line_ratio": 1.0,
        "pct_idle_lines": 0.0,
        "roaming_intensity": 0.017,
        "data_per_active_line": 4.5,
        "session_intensity": 22.5,
    },
    "Roaming / travel-heavy": {
        "data_gb_mean": 32.0,
        "voice_min_mean": 225.0,
        "sms_count_mean": 30.0,
        "roaming_days_mean": 15.0,
        "countries_visited_mean": 8.5,
        "lines_total_mean": 1.5,
        "lines_active_mean": 1.5,
        "plan_tier_mean": 2.5,
        "active_line_ratio": 1.0,
        "pct_idle_lines": 0.0,
        "roaming_intensity": 4.25,
        "data_per_active_line": 32.0,
        "session_intensity": 5120.0,
    },
    "Underutilized / overspending": {
        "data_gb_mean": 5.0,
        "voice_min_mean": 60.0,
        "sms_count_mean": 17.0,
        "roaming_days_mean": 0.5,
        "countries_visited_mean": 0.5,
        "lines_total_mean": 4.0,
        "lines_active_mean": 1.0,
        "plan_tier_mean": 4.5,
        "active_line_ratio": 0.25,
        "pct_idle_lines": 0.75,
        "roaming_intensity": 0.008,
        "data_per_active_line": 20.0,
        "session_intensity": 25.0,
    },
}
