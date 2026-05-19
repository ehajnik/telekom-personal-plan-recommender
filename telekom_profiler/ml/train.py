"""Train K-Means subscriber profiles and write artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from telekom_profiler.ml.features import build_subscriber_features, feature_matrix, load_usage_panel
from telekom_profiler.ml.overlays import compute_ml_overlays
from telekom_profiler.ml.profile_characteristics import (
    build_profile_characteristics_document,
    build_profile_entry,
)
from telekom_profiler.ml.schema import (
    CLUSTER_FEATURES,
    LABEL_DISCRIMINATORS,
    PROFILE_LABELS,
    SUBSCRIBER_ID_COL,
)


def _align_labels(centroids_unscaled: NDArray[np.floating]) -> dict[int, str]:
    """
    Map cluster index → human profile name by inspecting centroid features.

    Each label claims the cluster with the highest (or lowest for idle) value
    on its discriminator column; unresolved clusters get remaining labels.
    """
    feature_idx = {name: i for i, name in enumerate(CLUSTER_FEATURES)}
    n_clusters = centroids_unscaled.shape[0]
    assigned: dict[int, str] = {}
    used_clusters: set[int] = set()

    # Sort labels by specificity: underutilized (min pct_idle), roaming, voice, streaming, light
    order = [
        "Underutilized / overspending",
        "Roaming / travel-heavy",
        "Voice-centric",
        "Streaming & data-heavy",
        "Light / occasional user",
    ]

    for label in order:
        col = LABEL_DISCRIMINATORS[label]
        idx = feature_idx[col]
        values = centroids_unscaled[:, idx]
        if label == "Underutilized / overspending":
            rank = np.argsort(values)[::-1]  # highest idle first
        elif label == "Light / occasional user":
            rank = np.argsort(values)  # lowest data first
        elif label == "Streaming & data-heavy":
            rank = np.argsort(values)[::-1]
        else:
            rank = np.argsort(values)[::-1]
        for cluster_idx in rank:
            ci = int(cluster_idx)
            if ci not in used_clusters:
                assigned[ci] = label
                used_clusters.add(ci)
                break

    for ci in range(n_clusters):
        if ci not in assigned:
            for label in PROFILE_LABELS:
                if label not in assigned.values():
                    assigned[ci] = label
                    break
            else:
                assigned[ci] = PROFILE_LABELS[ci % len(PROFILE_LABELS)]

    return assigned


def _confidence(primary_d: float, secondary_d: float | None) -> str:
    if secondary_d is None or secondary_d < 1e-9:
        return "High"
    ratio = primary_d / secondary_d
    if ratio < 0.75:
        return "High"
    if ratio < 0.9:
        return "Medium"
    return "Low"


def train_and_save(
    input_csv: Path,
    artifacts_dir: Path,
    *,
    n_clusters: int = 5,
    min_silhouette: float = 0.5,
    random_state: int = 42,
) -> dict[str, Any]:
    """Full training pipeline; returns summary metrics."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    panel = load_usage_panel(input_csv)
    features_df = build_subscriber_features(panel)
    features_df.to_csv(artifacts_dir / "subscriber_features.csv", index=False)

    x, subscriber_ids = feature_matrix(features_df)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    print(f"Fitting K-Means (k={n_clusters})...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    cluster_indices = kmeans.fit_predict(x_scaled)
    sil = float(silhouette_score(x_scaled, cluster_indices))
    print(f"Silhouette score: {sil:.4f} (target >= {min_silhouette})")
    if sil < min_silhouette:
        raise RuntimeError(
            f"Silhouette {sil:.4f} below minimum {min_silhouette}; "
            "adjust synthetic data separation or features."
        )

    centroids_scaled = kmeans.cluster_centers_
    centroids_unscaled = scaler.inverse_transform(centroids_scaled)
    label_map = _align_labels(centroids_unscaled)
    label_map_json = {str(k): v for k, v in label_map.items()}

    # Per-cluster centroid rows as dicts
    centroid_rows: list[dict[str, float]] = []
    for i in range(n_clusters):
        row = {CLUSTER_FEATURES[j]: float(centroids_unscaled[i, j]) for j in range(len(CLUSTER_FEATURES))}
        centroid_rows.append(row)

    profiles_by_label: dict[str, Any] = {}
    for cluster_idx, label in label_map.items():
        row = centroid_rows[cluster_idx]
        row_with_trends = {**row}
        members = features_df[cluster_indices == cluster_idx]
        if len(members):
            for tc in ("data_trend", "voice_trend", "roaming_trend", "lines_trend"):
                row_with_trends[tc] = float(members[tc].mean())
        profiles_by_label[label] = build_profile_entry(label, cluster_idx, row_with_trends)

    profile_characteristics = build_profile_characteristics_document(profiles_by_label)

    # Distances in scaled space to each centroid
    map_rows: list[dict[str, Any]] = []
    for i, sid in enumerate(subscriber_ids):
        point = x_scaled[i : i + 1]
        dists = np.linalg.norm(centroids_scaled - point, axis=1)
        order = np.argsort(dists)
        primary_idx = int(order[0])
        secondary_idx = int(order[1]) if len(order) > 1 else primary_idx
        primary_dist = float(dists[primary_idx])
        secondary_dist = float(dists[secondary_idx])
        label = label_map[primary_idx]

        feat_row = features_df.iloc[i].to_dict()
        overlays = compute_ml_overlays(
            feat_row,
            primary_distance=primary_dist,
            secondary_distance=secondary_dist,
        )

        dist_cols = {f"dist_{label_map[j]}": float(dists[j]) for j in range(n_clusters)}
        map_rows.append(
            {
                SUBSCRIBER_ID_COL: sid,
                "cluster_idx": primary_idx,
                "cluster_label": label,
                "primary_distance": primary_dist,
                "secondary_distance": secondary_dist,
                "confidence": _confidence(primary_dist, secondary_dist),
                "overlays": "|".join(overlays),
                **dist_cols,
                **{k: feat_row.get(k) for k in ("data_trend", "voice_trend", "roaming_trend", "lines_trend")},
            }
        )

    cluster_map_df = pd.DataFrame(map_rows)
    cluster_map_df.to_csv(artifacts_dir / "subscriber_cluster_map.csv", index=False)

    joblib.dump(kmeans, artifacts_dir / "kmeans.pkl")
    joblib.dump(scaler, artifacts_dir / "scaler.pkl")
    (artifacts_dir / "label_map.json").write_text(
        json.dumps(label_map_json, indent=2),
        encoding="utf-8",
    )
    (artifacts_dir / "profile_characteristics.json").write_text(
        json.dumps(profile_characteristics, indent=2),
        encoding="utf-8",
    )
    (artifacts_dir / "cluster_features.json").write_text(
        json.dumps(list(CLUSTER_FEATURES), indent=2),
        encoding="utf-8",
    )

    return {
        "silhouette": sil,
        "n_subscribers": len(subscriber_ids),
        "label_map": label_map_json,
    }
