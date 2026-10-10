#!/usr/bin/env python3
"""Evaluate the frozen segmentation against the synthetic ground truth.

Reports, for a synthetic panel with known seed archetypes:

* **batch accuracy** — subscriber features (12-month means) → frozen centroids
* **slider accuracy** — the same subscribers entered through the six UI sliders
  (rounded means + trends → ``features_from_usage``) → frozen centroids; this is the
  path the Gradio app and API use
* **template round-trip** — every profile template is classified as its own profile
* **anchor drift** — trained cluster member means vs ``model.fixed_centroids``
* optional k-selection diagnostic (elbow + silhouette) to justify ``n_profiles``

Ground truth comes from the generator's sidecar ``<panel>.labels.csv`` (or a
``seed_archetype`` column if present).

Exit code is non-zero when accuracy falls below ``--min-accuracy`` so the script can
gate CI. ``--print-anchors`` emits a ``fixed_centroids`` YAML block computed from the
ground truth, for refreshing ``app_config.yaml`` after the generator changes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from telekom_profiler.domain.models import CustomerUsage
from telekom_profiler.ml.features import (
    build_subscriber_features,
    features_from_usage,
    load_usage_panel,
)
from telekom_profiler.ml.inference import clear_artifacts_cache, predict_from_features
from telekom_profiler.ml.profile_characteristics import HARD_CODED_SLIDER_DEFAULTS
from telekom_profiler.ml.schema import (
    LABEL_CANONICAL_CENTROIDS,
    SEED_ARCHETYPE_COL,
    SEED_TO_PROFILE_LABEL,
    SUBSCRIBER_ID_COL,
)
from telekom_profiler.paths import ARTIFACTS_DIR, RAW_DATA_DIR

_ANCHOR_COLS = (
    "data_gb_mean",
    "voice_min_mean",
    "sms_count_mean",
    "roaming_days_mean",
    "countries_visited_mean",
    "active_days_mean",
    "plan_tier_mean",
)
_DRIFT_COLS = ("data_gb_mean", "voice_min_mean", "sms_count_mean", "roaming_days_mean")


def _latest_panel() -> Path | None:
    candidates = sorted(
        RAW_DATA_DIR.glob("private_mobile_usage_*_subscribers_12_months.csv"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def slider_usage(row: pd.Series) -> CustomerUsage:
    """Subscriber means rounded the way an agent would set the UI sliders."""
    return CustomerUsage.from_mapping(
        {
            "data_gb": round(float(row["data_gb_mean"])),
            "voice_min": round(float(row["voice_min_mean"])),
            "sms_count": round(float(row["sms_count_mean"])),
            "roaming_days": round(float(row["roaming_days_mean"])),
            "data_trend": round(float(row["data_trend"])),
            "voice_trend": round(float(row["voice_trend"])),
        },
        clamp=True,
    )


def _accuracy_report(truth: pd.Series, predicted: pd.Series, title: str) -> float:
    acc = float((truth == predicted).mean())
    print(f"\n{title}: {acc:.1%} ({int((truth == predicted).sum())}/{len(truth)})")
    print(pd.crosstab(truth.rename("truth"), predicted.rename("predicted")).to_string())
    return acc


def _print_anchors(features: pd.DataFrame) -> None:
    means = features.groupby(SEED_ARCHETYPE_COL)[list(_ANCHOR_COLS)].mean()
    print("  fixed_centroids:")
    for seed, label in SEED_TO_PROFILE_LABEL.items():
        if seed not in means.index:
            continue
        print(f"    {label}:")
        for col in _ANCHOR_COLS:
            print(f"      {col}: {means.loc[seed, col]:.2f}")


def _k_selection(features: pd.DataFrame) -> None:
    from sklearn.preprocessing import StandardScaler

    from telekom_profiler.ml.features import feature_matrix
    from telekom_profiler.ml.train import select_k

    x, _ = feature_matrix(features)
    select_k(StandardScaler().fit_transform(x), k_min=2, k_max=9)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate frozen ML segmentation")
    parser.add_argument("--input", type=Path, default=None, help="Panel CSV with seed_archetype")
    parser.add_argument("--artifacts", type=Path, default=ARTIFACTS_DIR)
    parser.add_argument("--min-accuracy", type=float, default=0.9)
    parser.add_argument("--max-anchor-drift", type=float, default=0.25,
                        help="Max relative drift of trained member means vs anchors")
    parser.add_argument("--print-anchors", action="store_true")
    parser.add_argument("--k-selection", action="store_true")
    parser.add_argument("--json", type=Path, default=None, help="Write metrics JSON here")
    args = parser.parse_args()

    panel_path = args.input or _latest_panel()
    if panel_path is None:
        print("No panel found. Run scripts/generate_synthetic_data.py first.", file=sys.stderr)
        return 1
    panel = load_usage_panel(panel_path)
    labels_path = panel_path.with_name(panel_path.stem + ".labels.csv")
    if SEED_ARCHETYPE_COL in panel.columns:
        seeds = panel.groupby(SUBSCRIBER_ID_COL)[SEED_ARCHETYPE_COL].first()
    elif labels_path.is_file():
        seeds = pd.read_csv(labels_path).set_index(SUBSCRIBER_ID_COL)[SEED_ARCHETYPE_COL]
    else:
        print(f"No ground truth for {panel_path.name} (expected {labels_path.name}).",
              file=sys.stderr)
        return 1

    features = build_subscriber_features(panel)
    features[SEED_ARCHETYPE_COL] = features[SUBSCRIBER_ID_COL].astype(str).map(
        seeds.rename(index=str)
    )
    if features[SEED_ARCHETYPE_COL].isna().any():
        print("Ground-truth labels do not cover every subscriber.", file=sys.stderr)
        return 1
    print(f"Panel: {panel_path.name} ({len(features)} subscribers)")

    if args.print_anchors:
        _print_anchors(features)
        return 0
    if args.k_selection:
        _k_selection(features)

    clear_artifacts_cache()
    artifacts = str(args.artifacts)
    truth = features[SEED_ARCHETYPE_COL].map(SEED_TO_PROFILE_LABEL)
    batch = features.apply(
        lambda r: predict_from_features(r.to_dict(), artifacts_dir=artifacts).primary_label,
        axis=1,
    )
    slider = features.apply(
        lambda r: predict_from_features(
            features_from_usage(slider_usage(r)), artifacts_dir=artifacts
        ).primary_label,
        axis=1,
    )
    batch_acc = _accuracy_report(truth, batch, "Batch accuracy (12-month features)")
    slider_acc = _accuracy_report(truth, slider, "Slider accuracy (UI / API path)")

    print("\nTemplate round-trip:")
    template_ok = True
    for label, preset in HARD_CODED_SLIDER_DEFAULTS.items():
        usage = CustomerUsage.from_mapping(preset, clamp=True)
        got = predict_from_features(features_from_usage(usage), artifacts_dir=artifacts)
        ok = got.primary_label == label
        template_ok &= ok
        print(f"  {'OK ' if ok else 'BAD'} {label:<26} → {got.primary_label} ({got.confidence})")

    print("\nAnchor drift (trained member means vs model.fixed_centroids):")
    frozen = json.loads((args.artifacts / "frozen_centroids.json").read_text(encoding="utf-8"))
    member_means = frozen.get("cluster_member_means", {})
    max_drift = 0.0
    for label, anchor in LABEL_CANONICAL_CENTROIDS.items():
        trained = member_means.get(label, {})
        parts = []
        for col in _DRIFT_COLS:
            if col in anchor and col in trained:
                drift = abs(trained[col] - anchor[col]) / max(abs(anchor[col]), 1.0)
                max_drift = max(max_drift, drift)
                parts.append(f"{col.removesuffix('_mean')} {drift:.0%}")
        print(f"  {label:<26} {', '.join(parts) or 'n/a (retrain to record member means)'}")

    metrics = {
        "panel": panel_path.name,
        "n_subscribers": int(len(features)),
        "batch_accuracy": round(batch_acc, 4),
        "slider_accuracy": round(slider_acc, 4),
        "templates_ok": template_ok,
        "max_anchor_drift": round(max_drift, 4),
        "silhouette": frozen.get("training", {}).get("silhouette"),
    }
    if args.json:
        args.json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nSummary: {json.dumps(metrics)}")

    failures = []
    if min(batch_acc, slider_acc) < args.min_accuracy:
        failures.append(f"accuracy below {args.min_accuracy:.0%}")
    if not template_ok:
        failures.append("profile template misclassified")
    if member_means and max_drift > args.max_anchor_drift:
        failures.append(f"anchor drift {max_drift:.0%} > {args.max_anchor_drift:.0%}")
    if failures:
        print("FAILED: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("Evaluation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
