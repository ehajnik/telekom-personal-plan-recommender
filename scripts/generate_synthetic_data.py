#!/usr/bin/env python3
"""Generate synthetic 12-month private mobile usage panel for PoC training.

Each subscriber is assigned one seed archetype and draws a **persistent personal
baseline** from that archetype's ranges. Monthly values then vary around the
baseline with multiplicative noise, a personal relative trend, and (for roaming)
holiday seasonality. This keeps within-segment heterogeneity realistic instead
of collapsing every subscriber onto the archetype midpoint.

The ground-truth archetype is written to a sidecar file
(``<panel>.labels.csv``: ``subscriber_id, seed_archetype``) so the segmentation can be
evaluated (``scripts/evaluate_model.py``) without putting label text into the
training CSV.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from telekom_profiler.ml.schema import (
    MONTH_COL,
    SEED_ARCHETYPE_COL,
    SEED_ARCHETYPES,
    SUBSCRIBER_ID_COL,
)
from telekom_profiler.paths import RAW_DATA_DIR

# Personal baseline ranges per seed archetype (uniform draw once per subscriber).
# ``plan_tier`` is the subscriber's *current* tariff tier (1 = XS … 5 = XL).
ARCHETYPE_PARAMS: dict[str, dict[str, tuple[float, float]]] = {
    "light_user": {
        "data_gb": (0.5, 6.0),
        "voice_min": (20.0, 150.0),
        "sms_count": (5.0, 30.0),
        "roaming_days": (0.0, 1.0),
        "countries_visited": (1.0, 1.0),
        "active_days": (8.0, 20.0),
        "plan_tier": (1.0, 2.0),
    },
    "streaming_heavy": {
        "data_gb": (70.0, 140.0),
        "voice_min": (150.0, 450.0),
        "sms_count": (10.0, 50.0),
        "roaming_days": (0.5, 4.0),
        "countries_visited": (1.0, 2.0),
        "active_days": (26.0, 30.0),
        "plan_tier": (4.0, 5.0),
    },
    "voice_centric": {
        "data_gb": (2.0, 12.0),
        "voice_min": (1000.0, 2200.0),
        "sms_count": (30.0, 100.0),
        "roaming_days": (0.0, 2.0),
        "countries_visited": (1.0, 1.5),
        "active_days": (24.0, 30.0),
        "plan_tier": (1.0, 3.0),
    },
    "travel_heavy": {
        "data_gb": (20.0, 60.0),
        "voice_min": (200.0, 600.0),
        "sms_count": (20.0, 70.0),
        "roaming_days": (8.0, 18.0),
        "countries_visited": (2.0, 6.0),
        "active_days": (24.0, 30.0),
        "plan_tier": (3.0, 4.0),
    },
    "broad_usage": {
        "data_gb": (35.0, 80.0),
        "voice_min": (400.0, 900.0),
        "sms_count": (60.0, 180.0),
        "roaming_days": (1.0, 5.0),
        "countries_visited": (1.0, 3.0),
        "active_days": (26.0, 30.0),
        "plan_tier": (3.0, 4.0),
    },
}

# Annual relative trend ranges (fraction per year): data grows on average, voice declines.
DATA_TREND_RANGE: tuple[float, float] = (-0.30, 0.45)
VOICE_TREND_RANGE: tuple[float, float] = (-0.40, 0.15)

# Monthly multiplicative noise (log-normal sigma).
DATA_NOISE_SIGMA = 0.12
VOICE_NOISE_SIGMA = 0.12
SMS_NOISE_SIGMA = 0.15

# Roaming seasonality by calendar month (Jan … Dec); mean ≈ 1.0.
ROAMING_SEASONALITY: tuple[float, ...] = (
    0.7, 0.7, 0.85, 1.0, 1.0, 1.15, 1.6, 1.6, 1.1, 0.9, 0.7, 0.7,
)


def _draw_baseline(rng: np.random.Generator, archetype: str) -> dict[str, float]:
    params = ARCHETYPE_PARAMS[archetype]
    base = {col: float(rng.uniform(lo, hi)) for col, (lo, hi) in params.items()}
    base["plan_tier"] = float(np.clip(round(base["plan_tier"]), 1, 5))
    base["data_trend"] = float(rng.uniform(*DATA_TREND_RANGE))
    base["voice_trend"] = float(rng.uniform(*VOICE_TREND_RANGE))
    base["session_scale"] = float(rng.uniform(0.6, 1.4))
    return base


def _sample_month(
    rng: np.random.Generator,
    base: dict[str, float],
    month_idx: int,
) -> dict[str, float]:
    """One month of usage around the subscriber's personal baseline."""
    t = month_idx / 12.0  # fraction of a year since the panel start
    data = base["data_gb"] * max(0.05, 1 + base["data_trend"] * t)
    data *= rng.lognormal(0.0, DATA_NOISE_SIGMA)
    voice = base["voice_min"] * max(0.05, 1 + base["voice_trend"] * t)
    voice *= rng.lognormal(0.0, VOICE_NOISE_SIGMA)
    sms = base["sms_count"] * rng.lognormal(0.0, SMS_NOISE_SIGMA)

    season = ROAMING_SEASONALITY[month_idx % 12]
    roaming = float(min(30, rng.poisson(base["roaming_days"] * season)))
    if roaming == 0:
        countries = 0.0
    else:
        countries = float(
            np.clip(round(base["countries_visited"] * rng.uniform(0.6, 1.4)), 1, roaming)
        )

    active_days = float(np.clip(base["active_days"] + rng.normal(0, 1.5), 1, 30))
    # Average data per session (MB): grows sub-linearly with monthly volume.
    session_mb = base["session_scale"] * 25.0 * np.sqrt(max(data, 0.1) * 10.0)

    night = rng.uniform(0.15, 0.35) + (0.1 if data > 50 else 0.0)
    return {
        "data_gb": round(max(0.0, data), 3),
        "voice_min": round(max(0.0, voice), 1),
        "sms_count": float(round(max(0.0, sms))),
        "roaming_days": roaming,
        "countries_visited": countries,
        "night_usage_ratio": round(float(np.clip(night, 0, 1)), 3),
        "weekend_usage_ratio": round(float(rng.uniform(0.25, 0.45)), 3),
        "avg_session_mb": round(float(max(1.0, session_mb)), 1),
        "active_days": round(active_days, 1),
        "plan_tier": base["plan_tier"],
        "lines_total": 1.0,
        "lines_active": 1.0,
    }


def labels_path_for(panel_path: Path) -> Path:
    """Sidecar ground-truth file next to a panel CSV."""
    return panel_path.with_name(panel_path.stem + ".labels.csv")


def generate_panel(
    n_subscribers: int,
    *,
    months: int = 12,
    seed: int = 42,
) -> pd.DataFrame:
    """Return a long-format monthly panel (one row per subscriber × month).

    Includes the ``seed_archetype`` column; ``main`` splits it into the sidecar file.
    """
    rng = np.random.default_rng(seed)
    archetypes = list(SEED_ARCHETYPES)
    rows: list[dict[str, float | str | int]] = []

    for i in range(n_subscribers):
        sid = f"SUB{i + 1:05d}"
        archetype = archetypes[i % len(archetypes)]
        base = _draw_baseline(rng, archetype)
        for month in range(1, months + 1):
            rows.append(
                {
                    SUBSCRIBER_ID_COL: sid,
                    MONTH_COL: month,
                    **_sample_month(rng, base, month - 1),
                    SEED_ARCHETYPE_COL: archetype,
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic private mobile usage CSV")
    parser.add_argument("--subscribers", type=int, default=1000, help="Number of subscribers")
    parser.add_argument("--months", type=int, default=12, help="Months per subscriber")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: data/raw/private_mobile_usage_<subscribers>_subscribers_12_months.csv)",
    )
    args = parser.parse_args()

    out = args.output
    if out is None:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = RAW_DATA_DIR / f"private_mobile_usage_{args.subscribers}_subscribers_12_months.csv"

    df = generate_panel(args.subscribers, months=args.months, seed=args.seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns=[SEED_ARCHETYPE_COL]).to_csv(out, index=False)
    labels = df.groupby(SUBSCRIBER_ID_COL, sort=True)[SEED_ARCHETYPE_COL].first().reset_index()
    labels.to_csv(labels_path_for(out), index=False)
    print(f"Wrote {len(df)} rows ({args.subscribers} subscribers × {args.months} months) → {out}")
    print(f"Ground-truth labels → {labels_path_for(out)}")


if __name__ == "__main__":
    main()
