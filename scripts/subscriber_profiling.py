#!/usr/bin/env python3
"""Train K-Means subscriber profiles and write artifacts/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from telekom_profiler.ml.schema import MONTH_COL, RAW_NUMERIC_COLS, SUBSCRIBER_ID_COL
from telekom_profiler.ml.train import train_and_save
from telekom_profiler.paths import ARTIFACTS_DIR, RAW_DATA_DIR


def _build_sanity_rows(panel: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    numeric_cols = [MONTH_COL, *RAW_NUMERIC_COLS]

    extra_text_cols = [c for c in panel.columns if c not in {SUBSCRIBER_ID_COL, *numeric_cols}]
    rows.append(
        {
            "check": "No non-numeric training feature columns",
            "status": "PASS" if not extra_text_cols else "FAIL",
            "details": "none" if not extra_text_cols else ", ".join(extra_text_cols),
        }
    )

    missing_numeric = panel[numeric_cols].isna().sum().sum()
    rows.append(
        {
            "check": "No nulls in numeric columns",
            "status": "PASS" if missing_numeric == 0 else "FAIL",
            "details": f"null_count={int(missing_numeric)}",
        }
    )

    months_ok = panel[MONTH_COL].between(1, 12).all()
    rows.append(
        {
            "check": "Month index in [1, 12]",
            "status": "PASS" if months_ok else "FAIL",
            "details": f"min={int(panel[MONTH_COL].min())}, max={int(panel[MONTH_COL].max())}",
        }
    )

    non_negative_cols = [c for c in RAW_NUMERIC_COLS if c not in {"night_usage_ratio", "weekend_usage_ratio"}]
    negatives = int((panel[non_negative_cols] < 0).sum().sum())
    rows.append(
        {
            "check": "Non-negative usage values",
            "status": "PASS" if negatives == 0 else "FAIL",
            "details": f"negative_cells={negatives}",
        }
    )

    ratio_cols = ["night_usage_ratio", "weekend_usage_ratio"]
    ratio_ok = panel[ratio_cols].apply(lambda s: s.between(0, 1).all()).all()
    rows.append(
        {
            "check": "Usage ratio columns in [0, 1]",
            "status": "PASS" if bool(ratio_ok) else "FAIL",
            "details": ", ".join(ratio_cols),
        }
    )

    active_le_total = (panel["lines_active"] <= panel["lines_total"]).all()
    rows.append(
        {
            "check": "lines_active <= lines_total",
            "status": "PASS" if bool(active_le_total) else "FAIL",
            "details": "validated row-wise",
        }
    )
    return rows


def _require_openpyxl() -> None:
    try:
        import openpyxl  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "openpyxl is required for Excel reports. Install ML dependencies:\n"
            "  pip install -r requirements-ml.txt\n"
            "  # or: pip install -e \".[ml]\""
        ) from exc


def _write_excel_report(input_csv: Path, artifacts_dir: Path, summary: dict[str, object], out_xlsx: Path) -> None:
    _require_openpyxl()
    panel = pd.read_csv(input_csv)
    features = pd.read_csv(artifacts_dir / "subscriber_features.csv")
    cluster_map = pd.read_csv(artifacts_dir / "subscriber_cluster_map.csv")

    sanity_df = pd.DataFrame(_build_sanity_rows(panel))
    overview_df = pd.DataFrame(
        [
            {"metric": "input_csv", "value": str(input_csv)},
            {"metric": "n_rows_monthly_panel", "value": len(panel)},
            {"metric": "n_subscribers", "value": int(summary["n_subscribers"])},
            {"metric": "silhouette", "value": float(summary["silhouette"])},
            {"metric": "clusters", "value": cluster_map["cluster_label"].nunique()},
            {"metric": "label_map", "value": json.dumps(summary.get("label_map", {}), ensure_ascii=True)},
        ]
    )
    cluster_counts = cluster_map["cluster_label"].value_counts().rename_axis("cluster_label").reset_index(name="count")
    confidence_counts = (
        cluster_map["confidence"].value_counts().rename_axis("confidence").reset_index(name="count")
    )
    numeric_summary = features.describe().T.reset_index().rename(columns={"index": "feature"})

    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        overview_df.to_excel(writer, sheet_name="overview", index=False)
        sanity_df.to_excel(writer, sheet_name="sanity_checks", index=False)
        cluster_counts.to_excel(writer, sheet_name="cluster_counts", index=False)
        confidence_counts.to_excel(writer, sheet_name="confidence_counts", index=False)
        numeric_summary.to_excel(writer, sheet_name="feature_summary", index=False)


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
        _write_excel_report(input_csv, args.artifacts, summary, excel_report)
    except RuntimeError as exc:
        print(f"WARNING: {exc}", file=sys.stderr)
        print("Training artifacts were saved; re-run after installing openpyxl.", file=sys.stderr)
        sys.exit(1)
    print(f"Excel report → {excel_report}")


if __name__ == "__main__":
    main()
