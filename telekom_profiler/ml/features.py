"""Load usage panel CSV and build subscriber-level feature matrices."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from telekom_profiler.domain.models import CustomerUsage
from telekom_profiler.ml.schema import (
    CLUSTER_FEATURES,
    MONTH_COL,
    RAW_NUMERIC_COLS,
    SUBSCRIBER_ID_COL,
)


def load_usage_panel(path: Path | str) -> pd.DataFrame:
    """Load monthly subscriber usage CSV."""
    df = pd.read_csv(path)
    required = {SUBSCRIBER_ID_COL, MONTH_COL, *RAW_NUMERIC_COLS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")
    return df


def _ols_slope(values: NDArray[np.floating]) -> float:
    """OLS slope over 12 monthly points (x = 0..n-1)."""
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    y = np.asarray(values, dtype=float)
    if np.std(y) < 1e-9:
        return 0.0
    coef = np.polyfit(x, y, 1)
    return float(coef[0])


def build_subscriber_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate panel to one row per subscriber with baseline + trend columns.

    ``CLUSTER_FEATURES`` are baseline only; ``TREND_COLS`` are for overlays.
    """
    grouped = df.groupby(SUBSCRIBER_ID_COL, sort=True)

    means = grouped[list(RAW_NUMERIC_COLS)].mean().add_suffix("_mean")

    trends = pd.DataFrame(index=means.index)
    for sid, grp in grouped:
        trends.loc[sid, "data_trend"] = _ols_slope(grp["data_gb"].values)
        trends.loc[sid, "voice_trend"] = _ols_slope(grp["voice_min"].values)
        trends.loc[sid, "roaming_trend"] = _ols_slope(grp["roaming_days"].values)
        trends.loc[sid, "lines_trend"] = _ols_slope(grp["lines_active"].values)

    features = means.join(trends)
    features = _add_derived_baseline(features)
    return features.reset_index()


def _add_derived_baseline(features: pd.DataFrame) -> pd.DataFrame:
    """Compute derived columns in place."""
    lt = features["lines_total_mean"].clip(lower=1.0)
    la = features["lines_active_mean"].clip(lower=0.1)
    data = features["data_gb_mean"]
    voice = features["voice_min_mean"]
    roam = features["roaming_days_mean"]
    countries = features["countries_visited_mean"]
    active_days = features["active_days_mean"].clip(lower=1.0)
    plan = features["plan_tier_mean"]

    features["active_line_ratio"] = la / lt
    features["roaming_days_ratio"] = roam / 30.0
    features["roaming_intensity"] = features["roaming_days_ratio"] * countries
    features["data_per_active_line"] = data / features["active_line_ratio"]
    features["pct_idle_lines"] = ((lt - la) / lt).clip(0.0, 1.0)
    features["sms_per_gb"] = features["sms_count_mean"] / data.clip(lower=0.5)
    features["voice_per_active_day"] = voice / active_days
    features["data_per_active_day"] = data / active_days
    features["session_intensity"] = features["avg_session_mb_mean"] * data
    features["evening_peak_share"] = features["night_usage_ratio_mean"]
    features["weekend_share"] = features["weekend_usage_ratio_mean"]
    features["plan_usage_gap"] = (plan - (data / 50.0)).clip(lower=0.0)
    features["device_smartphone_share"] = 1.0  # placeholder if device not encoded
    return features


def features_from_usage(usage: CustomerUsage) -> dict[str, float]:
    """
    Approximate subscriber feature vector from UI sliders (manual override path).

    Maps six slider values to the same feature space used at training time.
    """
    d = usage.as_dict()
    data, voice, sms, roam = d["data_gb"], d["voice_min"], d["sms_count"], d["roaming_days"]
    lines_total = 2.0 if roam > 5 else 1.0
    lines_active = 1.5 if lines_total > 1 else 1.0
    countries = min(12.0, max(1.0, roam * 0.8))
    night_ratio = 0.35 if data > 40 else 0.2
    weekend_ratio = 0.4
    session_mb = min(500.0, data * 3.0)
    active_days = min(28.0, 10.0 + data / 5.0)
    plan_tier = 3.0 if data > 60 else 2.0 if data > 25 else 1.0

    row: dict[str, float] = {
        "data_gb_mean": data,
        "voice_min_mean": voice,
        "sms_count_mean": sms,
        "roaming_days_mean": roam,
        "countries_visited_mean": countries,
        "night_usage_ratio_mean": night_ratio,
        "weekend_usage_ratio_mean": weekend_ratio,
        "avg_session_mb_mean": session_mb,
        "active_days_mean": active_days,
        "plan_tier_mean": plan_tier,
        "lines_total_mean": lines_total,
        "lines_active_mean": lines_active,
        "data_trend": d["data_trend"] / 50.0,
        "voice_trend": d["voice_trend"] / 50.0,
        "roaming_trend": 0.0,
        "lines_trend": 0.0,
    }
    lt = max(lines_total, 1.0)
    la = max(lines_active, 0.1)
    row["active_line_ratio"] = la / lt
    row["roaming_days_ratio"] = roam / 30.0
    row["roaming_intensity"] = row["roaming_days_ratio"] * countries
    row["data_per_active_line"] = data / row["active_line_ratio"]
    row["pct_idle_lines"] = max(0.0, (lt - la) / lt)
    row["sms_per_gb"] = sms / max(data, 0.5)
    row["voice_per_active_day"] = voice / max(active_days, 1.0)
    row["data_per_active_day"] = data / max(active_days, 1.0)
    row["session_intensity"] = session_mb * data
    row["evening_peak_share"] = night_ratio
    row["weekend_share"] = weekend_ratio
    row["plan_usage_gap"] = max(0.0, plan_tier - data / 50.0)
    row["device_smartphone_share"] = 1.0
    return row


def feature_matrix(
    features_df: pd.DataFrame,
    columns: tuple[str, ...] = CLUSTER_FEATURES,
) -> tuple[NDArray[np.floating], list[str]]:
    """Extract numeric matrix and subscriber ids."""
    ids = features_df[SUBSCRIBER_ID_COL].astype(str).tolist()
    x = features_df[list(columns)].astype(float).values
    return x, ids


def metrics_snapshot(row: dict[str, float] | pd.Series) -> dict[str, float]:
    """Key metrics for profile narrative (concrete numbers)."""
    if isinstance(row, pd.Series):
        row = row.to_dict()
    return {
        "avg_monthly_data_gb": float(row.get("data_gb_mean", 0)),
        "avg_monthly_voice_min": float(row.get("voice_min_mean", 0)),
        "avg_monthly_sms": float(row.get("sms_count_mean", 0)),
        "avg_roaming_days": float(row.get("roaming_days_mean", 0)),
        "countries_visited": float(row.get("countries_visited_mean", 0)),
        "active_line_ratio": float(row.get("active_line_ratio", 0)),
        "pct_idle_lines": float(row.get("pct_idle_lines", 0)),
        "session_intensity": float(row.get("session_intensity", 0)),
    }
