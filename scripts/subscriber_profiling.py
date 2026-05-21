#!/usr/bin/env python3
"""Train K-Means subscriber profiles and write artifacts/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from telekom_profiler.ml.train import train_and_save
from telekom_profiler.paths import ARTIFACTS_DIR, RAW_DATA_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Train private mobile subscriber profiles")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Input CSV (default: latest data/raw/private_mobile_usage_*_12_months.csv)",
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=ARTIFACTS_DIR,
        help="Output artifacts directory",
    )
    parser.add_argument("--min-silhouette", type=float, default=0.5, help="Minimum silhouette score")
    parser.add_argument(
        "--clusters",
        default="auto",
        help="K-Means clusters: integer or 'auto' for elbow + silhouette selection (default: auto)",
    )
    parser.add_argument(
        "--k-min", type=int, default=2, help="Minimum k to evaluate when --clusters=auto"
    )
    parser.add_argument(
        "--k-max", type=int, default=10, help="Maximum k to evaluate when --clusters=auto"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random state")
    args = parser.parse_args()

    clusters: int | str
    if isinstance(args.clusters, str) and args.clusters.lower() == "auto":
        clusters = "auto"
    else:
        try:
            clusters = int(args.clusters)
        except (TypeError, ValueError) as exc:
            parser.error(f"--clusters must be 'auto' or an integer, got {args.clusters!r}: {exc}")

    input_csv = args.input
    if input_csv is None:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        candidates = sorted(RAW_DATA_DIR.glob("private_mobile_usage_*_subscribers_12_months.csv"))
        if not candidates:
            print(
                "No input CSV found. Run: python scripts/generate_synthetic_data.py",
                file=sys.stderr,
            )
            sys.exit(1)
        input_csv = candidates[-1]

    summary = train_and_save(
        input_csv,
        args.artifacts,
        n_clusters=clusters,
        k_min=args.k_min,
        k_max=args.k_max,
        min_silhouette=args.min_silhouette,
        random_state=args.seed,
    )
    print(
        f"Training complete. k={summary['n_clusters']}, "
        f"silhouette={summary['silhouette']:.4f}, n={summary['n_subscribers']}"
    )
    print(f"Artifacts → {args.artifacts}")


if __name__ == "__main__":
    main()
