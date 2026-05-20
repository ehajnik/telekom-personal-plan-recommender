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
from telekom_profiler.ml.training_report import write_training_excel_report
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
    parser.add_argument("--clusters", type=int, default=5, help="K-Means clusters")
    parser.add_argument("--seed", type=int, default=42, help="Random state")
    parser.add_argument(
        "--excel-report",
        type=Path,
        default=None,
        help="Excel report path (default: artifacts/training_report.xlsx)",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Skip Excel report (e.g. when openpyxl is not installed)",
    )
    args = parser.parse_args()

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
        n_clusters=args.clusters,
        min_silhouette=args.min_silhouette,
        random_state=args.seed,
    )
    print(f"Training complete. Silhouette={summary['silhouette']:.4f}, n={summary['n_subscribers']}")
    print(f"Artifacts → {args.artifacts}")
    if args.no_excel:
        print("Excel report skipped (--no-excel)")
        return
    excel_report = args.excel_report or (args.artifacts / "training_report.xlsx")
    try:
        write_training_excel_report(input_csv, args.artifacts, summary, excel_report)
    except RuntimeError as exc:
        print(f"WARNING: {exc}", file=sys.stderr)
        print("Training artifacts were saved; re-run after installing openpyxl.", file=sys.stderr)
        sys.exit(1)
    print(f"Excel report → {excel_report}")


if __name__ == "__main__":
    main()
