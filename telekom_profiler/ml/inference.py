"""Load trained artifacts and score subscribers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from telekom_profiler.config.profiler_settings import artifacts_available as _settings_artifacts
from telekom_profiler.domain.models import ArchetypeScore, CustomerUsage, ScoringResult
from telekom_profiler.ml.features import features_from_usage, metrics_snapshot
from telekom_profiler.ml.overlays import compute_ml_overlays
from telekom_profiler.ml.schema import CLUSTER_FEATURES, SUBSCRIBER_ID_COL
from telekom_profiler.paths import ARTIFACTS_DIR


@dataclass(frozen=True)
class MlPrediction:
    """Result of ML inference for one subscriber or feature row."""

    subscriber_id: str | None
    primary_label: str
    cluster_idx: int
    distances: tuple[ArchetypeScore, ...]
    overlays: tuple[str, ...]
    confidence: str
    feature_row: dict[str, float]
    metrics: dict[str, float]


@dataclass
class _ArtifactBundle:
    kmeans: KMeans
    scaler: StandardScaler
    label_map: dict[int, str]
    profile_characteristics: dict[str, Any]
    cluster_map: pd.DataFrame
    cluster_features: tuple[str, ...]


def artifacts_available(artifacts_dir: Path | None = None) -> bool:
    if artifacts_dir is not None:
        required = ("kmeans.pkl", "scaler.pkl", "label_map.json", "profile_characteristics.json")
        base = Path(artifacts_dir)
        return all((base / name).is_file() for name in required)
    return _settings_artifacts()


@lru_cache(maxsize=1)
def load_artifacts(artifacts_dir: str | None = None) -> _ArtifactBundle:
    base = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
    if not artifacts_available(base):
        raise FileNotFoundError(f"ML artifacts not found under {base}")

    label_raw = json.loads((base / "label_map.json").read_text(encoding="utf-8"))
    label_map = {int(k): v for k, v in label_raw.items()}
    profile_chars = json.loads(
        (base / "profile_characteristics.json").read_text(encoding="utf-8")
    )
    cluster_features = tuple(
        json.loads((base / "cluster_features.json").read_text(encoding="utf-8"))
    )
    cluster_map = pd.read_csv(base / "subscriber_cluster_map.csv")

    return _ArtifactBundle(
        kmeans=joblib.load(base / "kmeans.pkl"),
        scaler=joblib.load(base / "scaler.pkl"),
        label_map=label_map,
        profile_characteristics=profile_chars,
        cluster_map=cluster_map,
        cluster_features=cluster_features,
    )


def clear_artifacts_cache() -> None:
    load_artifacts.cache_clear()


def _distances_to_scores(
    dists: NDArray[np.floating],
    label_map: dict[int, str],
) -> tuple[ArchetypeScore, ...]:
    order = np.argsort(dists)
    return tuple(
        ArchetypeScore(label_map[int(i)], float(dists[int(i)]))
        for i in order
    )


def _confidence(primary_d: float, secondary_d: float | None) -> str:
    if secondary_d is None or secondary_d < 1e-9:
        return "High"
    ratio = primary_d / secondary_d
    if ratio < 0.75:
        return "High"
    if ratio < 0.9:
        return "Medium"
    return "Low"


def predict_from_features(
    feature_row: dict[str, float],
    *,
    subscriber_id: str | None = None,
    artifacts_dir: str | None = None,
) -> MlPrediction:
    """Score a feature dict (from CSV row or slider override)."""
    bundle = load_artifacts(artifacts_dir)
    cols = bundle.cluster_features or CLUSTER_FEATURES
    x = np.array([[float(feature_row[c]) for c in cols]], dtype=float)
    x_scaled = bundle.scaler.transform(x)
    centroids = bundle.kmeans.cluster_centers_
    dists = np.linalg.norm(centroids - x_scaled, axis=1)
    order = np.argsort(dists)
    primary_idx = int(order[0])
    secondary_idx = int(order[1]) if len(order) > 1 else primary_idx
    primary_dist = float(dists[primary_idx])
    secondary_dist = float(dists[secondary_idx])
    label = bundle.label_map[primary_idx]
    scores = _distances_to_scores(dists, bundle.label_map)
    overlays = tuple(
        compute_ml_overlays(
            feature_row,
            primary_distance=primary_dist,
            secondary_distance=secondary_dist,
        )
    )
    return MlPrediction(
        subscriber_id=subscriber_id,
        primary_label=label,
        cluster_idx=primary_idx,
        distances=scores,
        overlays=overlays,
        confidence=_confidence(primary_dist, secondary_dist),
        feature_row=feature_row,
        metrics=metrics_snapshot(feature_row),
    )


def predict_subscriber(
    subscriber_id: str,
    *,
    usage_override: CustomerUsage | None = None,
    artifacts_dir: str | None = None,
) -> MlPrediction:
    """Load subscriber from cluster map; optional slider override replaces features."""
    bundle = load_artifacts(artifacts_dir)
    cm = bundle.cluster_map
    match = cm[cm[SUBSCRIBER_ID_COL].astype(str) == str(subscriber_id)]
    if match.empty:
        raise KeyError(f"Unknown subscriber_id: {subscriber_id}")

    if usage_override is not None:
        row = features_from_usage(usage_override)
        return predict_from_features(row, subscriber_id=subscriber_id, artifacts_dir=artifacts_dir)

    # Rebuild feature row from subscriber_features if present
    features_path = (Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR) / "subscriber_features.csv"
    if features_path.is_file():
        feat_df = pd.read_csv(features_path)
        feat_match = feat_df[feat_df[SUBSCRIBER_ID_COL].astype(str) == str(subscriber_id)]
        if not feat_match.empty:
            row = feat_match.iloc[0].to_dict()
            return predict_from_features(row, subscriber_id=subscriber_id, artifacts_dir=artifacts_dir)

    # Fallback: use cluster map stored trends + profile defaults
    row = features_from_usage(_defaults_for_subscriber(match.iloc[0], bundle))
    return predict_from_features(row, subscriber_id=subscriber_id, artifacts_dir=artifacts_dir)


def _defaults_for_subscriber(map_row: pd.Series, bundle: _ArtifactBundle) -> CustomerUsage:
    label = str(map_row["cluster_label"])
    chars = bundle.profile_characteristics.get(label, {})
    sliders = chars.get("slider_defaults", {})
    return CustomerUsage.from_mapping(
        {
            "data_gb": sliders.get("data_gb", 30),
            "voice_min": sliders.get("voice_min", 400),
            "sms_count": sliders.get("sms_count", 50),
            "roaming_days": sliders.get("roaming_days", 2),
            "data_trend": float(map_row.get("data_trend", 0)) * 50,
            "voice_trend": float(map_row.get("voice_trend", 0)) * 50,
        }
    )


def list_subscriber_ids(artifacts_dir: str | None = None) -> list[str]:
    bundle = load_artifacts(artifacts_dir)
    return bundle.cluster_map[SUBSCRIBER_ID_COL].astype(str).tolist()


def scoring_result_from_prediction(pred: MlPrediction) -> ScoringResult:
    primary = pred.distances[0]
    secondary = pred.distances[1] if len(pred.distances) > 1 else None
    return ScoringResult(
        primary=primary,
        secondary=secondary,
        all_distances=pred.distances,
        overlays=pred.overlays,
        confidence=pred.confidence,
    )


def get_slider_defaults_for_subscriber(
    subscriber_id: str,
    artifacts_dir: str | None = None,
) -> dict[str, int]:
    bundle = load_artifacts(artifacts_dir)
    cm = bundle.cluster_map
    match = cm[cm[SUBSCRIBER_ID_COL].astype(str) == str(subscriber_id)]
    if match.empty:
        return {}
    label = str(match.iloc[0]["cluster_label"])
    chars = bundle.profile_characteristics.get(label, {})
    sliders = dict(chars.get("slider_defaults", {}))
    row = match.iloc[0]
    sliders["data_trend"] = int(min(50, max(-50, round(float(row.get("data_trend", 0)) * 50))))
    sliders["voice_trend"] = int(min(50, max(-50, round(float(row.get("voice_trend", 0)) * 50))))
    return sliders
