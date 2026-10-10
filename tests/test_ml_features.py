"""Tests for ML feature engineering and training."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from telekom_profiler.domain.models import CustomerUsage
from telekom_profiler.ml.features import (
    build_subscriber_features,
    features_from_usage,
    load_usage_panel,
)
from telekom_profiler.ml.schema import CLUSTER_FEATURES, PROFILE_LABELS, TREND_COLS


class ProfileCharacteristicsTests(unittest.TestCase):
    def test_document_schema(self) -> None:
        from telekom_profiler.ml.profile_characteristics import (
            build_profile_characteristics_document,
            build_profile_entry,
            load_profiles_document,
        )

        row = {
            "data_gb_mean": 40.0,
            "voice_min_mean": 200.0,
            "sms_count_mean": 30.0,
            "roaming_days_mean": 5.0,
            "countries_visited_mean": 3.0,
            "lines_total_mean": 2.0,
            "lines_active_mean": 1.5,
            "active_line_ratio": 0.75,
            "roaming_days_ratio": 0.15,
            "roaming_intensity": 0.45,
            "data_per_active_line": 26.0,
            "pct_idle_lines": 0.25,
            "session_intensity": 1200.0,
            "evening_peak_share": 0.4,
            "weekend_share": 0.35,
            "plan_tier_mean": 2.0,
            "plan_usage_gap": 1.0,
            "avg_session_mb_mean": 30.0,
            "active_days_mean": 20.0,
            "data_trend": 0.1,
            "voice_trend": -0.05,
            "roaming_trend": 0.02,
            "lines_trend": 0.0,
        }
        entry = build_profile_entry("Streaming & data-heavy", 2, row)
        doc = build_profile_characteristics_document({"Streaming & data-heavy": entry})
        self.assertIn("profiles", doc)
        self.assertIn("overlays", doc)
        self.assertIsInstance(entry["signature"], list)
        self.assertIn("avg_monthly_data_gb", entry["centroid"])
        self.assertIn("data_gb", entry["slider_defaults"])
        loaded = load_profiles_document(doc)
        self.assertEqual(loaded["profiles"]["Streaming & data-heavy"]["cluster_idx"], 2)


def _find_synthetic_csv(repo: Path) -> Path | None:
    raw = repo / "data/raw"
    if not raw.is_dir():
        return None
    matches = sorted(
        raw.glob("private_mobile_usage_*_subscribers_12_months.csv"),
        key=lambda path: path.stat().st_mtime,
    )
    return matches[-1] if matches else None


def _linear_panel(data_start: float, data_step: float, voice_start: float) -> pd.DataFrame:
    rows = []
    for month in range(1, 13):
        rows.append(
            {
                "subscriber_id": "SUB00001",
                "month": month,
                "data_gb": data_start + data_step * (month - 1),
                "voice_min": voice_start,
                "sms_count": 20.0,
                "roaming_days": 1.0,
                "countries_visited": 1.0,
                "night_usage_ratio": 0.2,
                "weekend_usage_ratio": 0.3,
                "avg_session_mb": 50.0,
                "active_days": 20.0,
                "plan_tier": 2.0,
                "lines_total": 1.0,
                "lines_active": 1.0,
            }
        )
    return pd.DataFrame(rows)


class TrendUnitTests(unittest.TestCase):
    def test_data_trend_is_percent_per_year(self) -> None:
        # +0.1 GB/month on a 20.55 GB mean → 0.1 × 12 / 20.55 ≈ +5.84 % per year.
        features = build_subscriber_features(_linear_panel(20.0, 0.1, 300.0))
        self.assertAlmostEqual(float(features.loc[0, "data_trend"]), 5.839, places=2)
        self.assertAlmostEqual(float(features.loc[0, "voice_trend"]), 0.0)

    def test_trend_clipped_to_slider_range(self) -> None:
        features = build_subscriber_features(_linear_panel(1.0, 2.0, 300.0))
        self.assertEqual(float(features.loc[0, "data_trend"]), 50.0)

    def test_slider_trend_passes_through_unchanged(self) -> None:
        usage = CustomerUsage.from_mapping(
            {"data_gb": 10, "voice_min": 100, "sms_count": 10, "roaming_days": 0,
             "data_trend": 12, "voice_trend": -20}
        )
        row = features_from_usage(usage)
        self.assertEqual(row["data_trend"], 12.0)
        self.assertEqual(row["voice_trend"], -20.0)
        self.assertEqual(row["countries_visited_mean"], 0.0)

    def test_cluster_features_computable_from_sliders(self) -> None:
        usage = CustomerUsage.defaults()
        row = features_from_usage(usage)
        for col in CLUSTER_FEATURES:
            self.assertIn(col, row)


class MlFeatureTests(unittest.TestCase):
    def test_profile_count_and_labels(self) -> None:
        self.assertEqual(len(PROFILE_LABELS), 5)
        self.assertNotIn("Family / multi-line", PROFILE_LABELS)

    def test_cluster_features_exclude_trends(self) -> None:
        for col in TREND_COLS:
            self.assertNotIn(col, CLUSTER_FEATURES)
        self.assertNotIn("lines_total_mean", CLUSTER_FEATURES)
        self.assertNotIn("lines_active_mean", CLUSTER_FEATURES)

    def test_build_subscriber_features_shape(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        csv = _find_synthetic_csv(repo)
        if csv is None:
            self.skipTest("Synthetic CSV not generated; run scripts/generate_synthetic_data.py")
        panel = load_usage_panel(csv)
        features = build_subscriber_features(panel)
        self.assertGreater(len(features), 0)
        for col in CLUSTER_FEATURES:
            self.assertIn(col, features.columns)
        for col in TREND_COLS:
            self.assertIn(col, features.columns)


class MlTrainTests(unittest.TestCase):
    def test_train_meets_silhouette(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        csv = _find_synthetic_csv(repo)
        if csv is None:
            self.skipTest("Synthetic CSV not generated")
        from telekom_profiler.ml.train import train_and_save

        with tempfile.TemporaryDirectory() as tmp:
            summary = train_and_save(
                csv,
                Path(tmp),
                min_silhouette=0.5,
            )
            self.assertGreaterEqual(summary["silhouette"], 0.5)
            self.assertEqual(summary["n_clusters"], 5)
            self.assertTrue((Path(tmp) / "frozen_centroids.json").is_file())
            self.assertEqual(sorted(summary["label_map"].values()), sorted(PROFILE_LABELS))

    def test_anchor_without_cluster_features_raises(self) -> None:
        from unittest.mock import patch

        import numpy as np
        from sklearn.preprocessing import StandardScaler

        from telekom_profiler.ml import train

        sample = np.random.default_rng(0).normal(size=(20, len(CLUSTER_FEATURES)))
        scaler = StandardScaler().fit(sample)
        bad = {label: {"unrelated_feature": 1.0} for label in PROFILE_LABELS}
        with patch.object(train, "LABEL_CANONICAL_CENTROIDS", bad):
            with self.assertRaises(ValueError):
                train.assign_labels(np.zeros((5, len(CLUSTER_FEATURES))), scaler)


class MlInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._artifacts = Path(__file__).resolve().parents[1] / "artifacts"
        if not (cls._artifacts / "frozen_centroids.json").is_file():
            raise unittest.SkipTest("Artifacts not trained; run scripts/subscriber_profiling.py")

    def test_predict_subscriber(self) -> None:
        from telekom_profiler.ml.inference import predict_subscriber

        pred = predict_subscriber("SUB00001")
        self.assertTrue(pred.primary_label)
        self.assertGreaterEqual(len(pred.distances), 5)

    def test_features_from_usage(self) -> None:
        usage = CustomerUsage.from_mapping(
            {
                "data_gb": 100,
                "voice_min": 200,
                "sms_count": 30,
                "roaming_days": 5,
                "data_trend": 10,
                "voice_trend": 0,
            }
        )
        row = features_from_usage(usage)
        self.assertIn("data_gb_mean", row)
        self.assertAlmostEqual(row["data_gb_mean"], 100.0)
        self.assertEqual(row["lines_total_mean"], 1.0)
        self.assertEqual(row["lines_active_mean"], 1.0)

    def test_profile_templates_classify_as_themselves(self) -> None:
        from telekom_profiler.ml.inference import predict_from_features
        from telekom_profiler.ml.profile_characteristics import HARD_CODED_SLIDER_DEFAULTS

        for label, preset in HARD_CODED_SLIDER_DEFAULTS.items():
            usage = CustomerUsage.from_mapping(preset)
            pred = predict_from_features(features_from_usage(usage))
            self.assertEqual(pred.primary_label, label)

    def test_artifacts_are_mutually_consistent(self) -> None:
        label_map = json.loads((self._artifacts / "label_map.json").read_text(encoding="utf-8"))
        frozen = json.loads((self._artifacts / "frozen_centroids.json").read_text(encoding="utf-8"))
        cluster_features = json.loads(
            (self._artifacts / "cluster_features.json").read_text(encoding="utf-8")
        )
        profiles = json.loads(
            (self._artifacts / "profile_characteristics.json").read_text(encoding="utf-8")
        )
        cluster_map = pd.read_csv(self._artifacts / "subscriber_cluster_map.csv")
        labels = set(label_map.values())
        self.assertEqual(labels, set(PROFILE_LABELS))
        self.assertEqual(set(frozen["centroids_unscaled"]), labels)
        self.assertEqual(set(profiles["profiles"]), labels)
        self.assertTrue(set(cluster_map["cluster_label"]).issubset(labels))
        self.assertEqual(tuple(cluster_features), CLUSTER_FEATURES)
        self.assertEqual(tuple(frozen["cluster_features"]), CLUSTER_FEATURES)


if __name__ == "__main__":
    unittest.main()
