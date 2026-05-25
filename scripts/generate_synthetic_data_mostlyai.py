#!/usr/bin/env python3
"""Generate a synthetic 12-month private mobile usage panel via MOSTLY AI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from telekom_profiler.ml.features import load_usage_panel
from telekom_profiler.ml.mostlyai_generator import generate_panel_with_mostlyai
from telekom_profiler.paths import ARTIFACTS_DIR, RAW_DATA_DIR


def _default_input() -> Path | None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    candidates = sorted(RAW_DATA_DIR.glob("private_mobile_usage_*_subscribers_12_months.csv"))
    return candidates[-1] if candidates else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a private mobile usage CSV with MOSTLY AI"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Source CSV used to train MOSTLY AI (default: latest data/raw/private_mobile_usage_*_subscribers_12_months.csv)",
    )
    parser.add_argument("--subscribers", type=int, default=1000, help="Number of synthetic subscribers")
    parser.add_argument("--months", type=int, default=12, help="Months per subscriber in the output")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used for repair / resampling")
    parser.add_argument(
        "--max-training-time",
        type=int,
        default=2,
        help="MOSTLY AI max training time in minutes",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="MOSTLY AI workspace directory (default: artifacts/mostlyai/<output-stem>)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: data/raw/private_mobile_usage_mostlyai_<subscribers>_subscribers_12_months.csv)",
    )
    args = parser.parse_args()

    input_csv = args.input or _default_input()
    if input_csv is None:
        print(
            "No source CSV found. Generate a seed panel first with "
            "'python scripts/generate_synthetic_data.py' or pass --input.",
            file=sys.stderr,
        )
        sys.exit(1)

    output = args.output
    if output is None:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        output = (
            RAW_DATA_DIR
            / f"private_mobile_usage_mostlyai_{args.subscribers}_subscribers_12_months.csv"
        )

    workspace = args.workspace
    if workspace is None:
        workspace = ARTIFACTS_DIR / "mostlyai" / output.stem

    panel = load_usage_panel(input_csv)
    synthetic = generate_panel_with_mostlyai(
        panel,
        n_subscribers=args.subscribers,
        months=args.months,
        seed=args.seed,
        max_training_time=args.max_training_time,
        workspace_dir=workspace,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    synthetic.to_csv(output, index=False)
    print(
        f"Wrote {len(synthetic)} rows "
        f"({args.subscribers} subscribers × {args.months} months) → {output}"
    )
    print(f"MOSTLY AI workspace → {workspace}")


if __name__ == "__main__":
    main()
