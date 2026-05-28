"""Train K-Means subscriber profiles and write artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from telekom_profiler.config.app_config import model_config, training_config
from telekom_profiler.ml.features import build_subscriber_features, feature_matrix, load_usage_panel
from telekom_profiler.ml.overlays import compute_ml_overlays
from telekom_profiler.ml.profile_characteristics import (
    build_hardcoded_profiles_document,
)
from telekom_profiler.ml.schema import (
    CLUSTER_FEATURES,
    LABEL_CANONICAL_CENTROIDS,
    PROFILE_LABELS,
    SUBSCRIBER_ID_COL,
)


def _label_cost_matrix(
    centroids_unscaled: NDArray[np.floating],
    scaler: StandardScaler,
) -> NDArray[np.floating]:
    """Std-normalised squared distance between each named label and each cluster centroid.

    Rows are ``PROFILE_LABELS`` in declaration order; columns are cluster indices.
    Only the features present in ``LABEL_CANONICAL_CENTROIDS[label]`` contribute to
    that label's row, so each label only "cares" about its own discriminators.
    """
    feature_idx = {name: i for i, name in enumerate(CLUSTER_FEATURES)}
    scales = np.where(scaler.scale_ > 1e-9, scaler.scale_, 1.0)
    n_clusters = centroids_unscaled.shape[0]
    n_labels = len(PROFILE_LABELS)
    cost = np.zeros((n_labels, n_clusters), dtype=float)
    for row, label in enumerate(PROFILE_LABELS):
        canonical = LABEL_CANONICAL_CENTROIDS.get(label, {})
        if not canonical:
            cost[row, :] = 0.0
            continue
        for col in range(n_clusters):
            total = 0.0
            for feature, target in canonical.items():
                idx = feature_idx.get(feature)
                if idx is None:
                    continue
                delta = (centroids_unscaled[col, idx] - float(target)) / scales[idx]
                total += float(delta * delta)
            cost[row, col] = total
    return cost


def assign_labels(
    centroids_unscaled: NDArray[np.floating],
    scaler: StandardScaler,
) -> dict[int, str]:
    """Globally-optimal label↔cluster mapping via the Hungarian algorithm.

    Returns ``{cluster_idx: label}`` where each named ``PROFILE_LABELS`` entry is
    matched to its best-fitting cluster according to ``LABEL_CANONICAL_CENTROIDS``.
    Any remaining clusters (when ``k`` exceeds the number of named labels) receive
    generic ``Profile N`` names so downstream consumers can still render them.
    """
    n_clusters = centroids_unscaled.shape[0]
    cost = _label_cost_matrix(centroids_unscaled, scaler)
    label_rows, cluster_cols = linear_sum_assignment(cost)

    assigned: dict[int, str] = {}
    for row, col in zip(label_rows, cluster_cols):
        assigned[int(col)] = PROFILE_LABELS[int(row)]

    next_n = len(PROFILE_LABELS) + 1
    for ci in range(n_clusters):
        if ci not in assigned:
            assigned[ci] = f"Profile {next_n}"
            next_n += 1
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


def _kneedle_elbow(ks: list[int], inertias: list[float]) -> int | None:
    """Return the k at the maximum perpendicular distance from the chord.

    Implements a tiny kneedle-style elbow detector: normalise (k, inertia) to
    [0, 1] and find the point with the largest perpendicular distance to the
    line connecting the first and last points. Returns ``None`` for < 3 points.
    """
    if len(ks) < 3:
        return None
    x = np.asarray(ks, dtype=float)
    y = np.asarray(inertias, dtype=float)
    x_norm = (x - x.min()) / max(x.max() - x.min(), 1e-9)
    y_norm = (y - y.min()) / max(y.max() - y.min(), 1e-9)
    x0, y0 = x_norm[0], y_norm[0]
    x1, y1 = x_norm[-1], y_norm[-1]
    dx, dy = x1 - x0, y1 - y0
    norm = float(np.hypot(dx, dy)) or 1.0
    distances = np.abs(dy * x_norm - dx * y_norm + x1 * y0 - y1 * x0) / norm
    return int(ks[int(np.argmax(distances))])


def select_k(
    x_scaled: NDArray[np.floating],
    *,
    k_min: int = 2,
    k_max: int = 10,
    random_state: int = 42,
) -> tuple[int, list[dict[str, float]]]:
    """Choose the best ``k`` for K-Means via silhouette argmax + elbow cross-check.

    Returns ``(chosen_k, candidates)`` where ``candidates`` is a list of
    ``{"k", "inertia", "silhouette"}`` rows suitable for ``k_selection.json``.
    Silhouette argmax is the primary signal; the kneedle elbow is logged for
    cross-check and any disagreement is printed as a warning.
    """
    if k_min < 2:
        raise ValueError("k_min must be >= 2 (silhouette undefined for k < 2)")
    if k_max < k_min:
        raise ValueError("k_max must be >= k_min")

    n_samples = x_scaled.shape[0]
    upper = min(k_max, max(k_min, n_samples - 1))

    candidates: list[dict[str, float]] = []
    ks: list[int] = []
    inertias: list[float] = []
    silhouettes: list[float] = []
    print(f"Selecting k via elbow + silhouette over k ∈ [{k_min}, {upper}]...")
    for k in range(k_min, upper + 1):
        km = KMeans(n_clusters=k, random_state=random_state, n_init=20).fit(x_scaled)
        sil = float(silhouette_score(x_scaled, km.labels_))
        inertia = float(km.inertia_)
        candidates.append({"k": k, "inertia": inertia, "silhouette": sil})
        ks.append(k)
        inertias.append(inertia)
        silhouettes.append(sil)
        print(f"  k={k:>2}  inertia={inertia:>10.1f}  silhouette={sil:.4f}")

    best_sil_k = ks[int(np.argmax(silhouettes))]
    elbow_k = _kneedle_elbow(ks, inertias)
    chosen = best_sil_k
    if elbow_k is not None and elbow_k != best_sil_k:
        print(
            f"  note: silhouette argmax (k={best_sil_k}) and kneedle elbow "
            f"(k={elbow_k}) disagree; preferring silhouette."
        )
    print(f"Chosen k = {chosen}")
    return chosen, candidates


def train_and_save(
    input_csv: Path,
    artifacts_dir: Path,
    *,
    n_clusters: int | None = None,
    min_silhouette: float | None = None,
    random_state: int | None = None,
) -> dict[str, Any]:
    """Offline training pipeline with fixed profile count."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    train_cfg = training_config()
    model_cfg = model_config()
    fixed_clusters = int(model_cfg.get("n_profiles", 5))
    if n_clusters is not None and int(n_clusters) != fixed_clusters:
        raise ValueError(f"Fixed profile count is {fixed_clusters}; got n_clusters={n_clusters}")
    min_silhouette = float(min_silhouette if min_silhouette is not None else train_cfg.get("min_silhouette", 0.5))
    random_state = int(random_state if random_state is not None else train_cfg.get("random_state", 42))

    panel = load_usage_panel(input_csv)
    features_df = build_subscriber_features(panel)
    features_df.to_csv(artifacts_dir / "subscriber_features.csv", index=False)

    x, subscriber_ids = feature_matrix(features_df)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    n_clusters = fixed_clusters

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
    label_map = assign_labels(centroids_unscaled, scaler)
    label_map_json = {str(k): v for k, v in label_map.items()}

    derived_cols = ("evening_peak_share", "weekend_share")
    centroid_rows: list[dict[str, float]] = []
    for i in range(n_clusters):
        row = {CLUSTER_FEATURES[j]: float(centroids_unscaled[i, j]) for j in range(len(CLUSTER_FEATURES))}
        members = features_df[cluster_indices == i]
        for dc in derived_cols:
            if dc in features_df.columns and len(members):
                row[dc] = float(members[dc].mean())
        centroid_rows.append(row)

    profile_characteristics = build_hardcoded_profiles_document(label_map)

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
    frozen_centroids = {
        "cluster_features": list(CLUSTER_FEATURES),
        "labels": [label_map[i] for i in range(n_clusters)],
        "centroids_unscaled": {
            label_map[i]: {CLUSTER_FEATURES[j]: float(centroids_unscaled[i, j]) for j in range(len(CLUSTER_FEATURES))}
            for i in range(n_clusters)
        },
        "scaler_scale": {
            CLUSTER_FEATURES[i]: float(scaler.scale_[i]) for i in range(len(CLUSTER_FEATURES))
        },
    }
    (artifacts_dir / "frozen_centroids.json").write_text(
        json.dumps(frozen_centroids, indent=2),
        encoding="utf-8",
    )

    return {
        "silhouette": sil,
        "n_subscribers": len(subscriber_ids),
        "n_clusters": n_clusters,
        "label_map": label_map_json,
        "k_selection": None,
    }
