#!/usr/bin/env python3
"""Generate synthetic 12-month private mobile usage panel for PoC training."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from telekom_profiler.ml.schema import MONTH_COL, SEED_ARCHETYPES, SUBSCRIBER_ID_COL
from telekom_profiler.paths import RAW_DATA_DIR

# Fixed five seed archetypes keyed by ``SEED_ARCHETYPES``.
# These ranges intentionally mirror the active five-profile taxonomy.
ARCHETYPE_PARAMS: dict[str, dict[str, tuple[float, float]]] = {
    "light_user": {
        "data_gb": (0.5, 2.5),
        "voice_min": (15.0, 80.0),
        "sms_count": (5.0, 25.0),
        "roaming_days": (0.0, 0.5),
        "countries_visited": (0.0, 0.5),
        "lines_total": (1.0, 1.0),
        "lines_active": (1.0, 1.0),
        "plan_tier": (1.0, 1.0),
    },
    "streaming_heavy": {
        "data_gb": (100.0, 130.0),
        "voice_min": (250.0, 420.0),
        "sms_count": (20.0, 55.0),
        "roaming_days": (1.0, 5.0),
        "countries_visited": (0.5, 2.5),
        "lines_total": (1.0, 1.0),
        "lines_active": (1.0, 1.0),
        "plan_tier": (3.5, 4.5),
    },
    "voice_centric": {
        "data_gb": (3.0, 9.0),
        "voice_min": (1200.0, 1800.0),
        "sms_count": (45.0, 80.0),
        "roaming_days": (0.0, 3.0),
        "countries_visited": (0.0, 1.5),
        "lines_total": (1.0, 1.0),
        "lines_active": (1.0, 1.0),
        "plan_tier": (1.0, 2.0),
    },
    "travel_heavy": {
        "data_gb": (30.0, 52.0),
        "voice_min": (210.0, 420.0),
        "sms_count": (30.0, 65.0),
        "roaming_days": (10.0, 16.0),
        "countries_visited": (5.0, 9.0),
        "lines_total": (1.0, 1.0),
        "lines_active": (1.0, 1.0),
        "plan_tier": (2.0, 3.0),
    },
    "underutilized_overspending": {
        "data_gb": (50.0, 82.0),
        "voice_min": (450.0, 800.0),
        "sms_count": (60.0, 120.0),
        "roaming_days": (2.0, 5.0),
        "countries_visited": (1.5, 3.5),
        "lines_total": (1.0, 1.0),
        "lines_active": (1.0, 1.0),
        "plan_tier": (3.0, 4.0),
    },
}


def _sample_month(
    rng: np.random.Generator,
    archetype: str,
    month_idx: int,
    data_slope: float,
    voice_slope: float,
    roam_slope: float,
) -> dict[str, float]:
    params = ARCHETYPE_PARAMS[archetype]
    row: dict[str, float] = {}
    for col in params:
        lo, hi = params[col]
        base = rng.uniform(lo, hi)
        if col == "data_gb":
            base += data_slope * month_idx + rng.normal(0, 0.8)
        elif col == "voice_min":
            base += voice_slope * month_idx + rng.normal(0, 15.0)
        elif col == "roaming_days":
            base += roam_slope * month_idx + rng.normal(0, 0.15)
        elif col == "lines_total":
            base = float(rng.integers(int(lo), int(hi) + 1))
        elif col == "lines_active":
            base = min(base, float(row.get("lines_total", base)))
        row[col] = max(0.0, base)

    row["night_usage_ratio"] = float(np.clip(rng.uniform(0.15, 0.55) + (0.1 if row["data_gb"] > 50 else 0), 0, 1))
    row["weekend_usage_ratio"] = float(np.clip(rng.uniform(0.25, 0.6), 0, 1))
    row["avg_session_mb"] = float(max(1.0, row["data_gb"] * rng.uniform(2.0, 8.0)))
    row["active_days"] = float(np.clip(rng.uniform(8, 28), 1, 31))
    return row


def generate_panel(
    n_subscribers: int,
    *,
    months: int = 12,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    archetypes = list(SEED_ARCHETYPES)
    rows: list[dict[str, float | str | int]] = []

    for i in range(n_subscribers):
        sid = f"SUB{i + 1:05d}"
        archetype = archetypes[i % len(archetypes)]

        data_slope = rng.uniform(-0.8, 0.8)
        voice_slope = rng.uniform(-1.5, 1.5)
        roam_slope = rng.uniform(-0.15, 0.15)

        for month in range(1, months + 1):
            row = _sample_month(rng, archetype, month - 1, data_slope, voice_slope, roam_slope)
            rows.append(
                {
                    SUBSCRIBER_ID_COL: sid,
                    MONTH_COL: month,
                    **row,
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
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows ({args.subscribers} subscribers × {args.months} months) → {out}")


if __name__ == "__main__":
    main()
