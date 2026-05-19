"""Tests for ML feature engineering and training."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telekom_profiler.domain.models import CustomerUsage
from telekom_profiler.ml.features import (
    build_subscriber_features,
    features_from_usage,
    load_usage_panel,
)
from telekom_profiler.ml.schema import CLUSTER_FEATURES, TREND_COLS


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


class MlFeatureTests(unittest.TestCase):
    def test_cluster_features_exclude_trends(self) -> None:
        for col in TREND_COLS:
            self.assertNotIn(col, CLUSTER_FEATURES)

    def test_build_subscriber_features_shape(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        csv = repo / "data/raw/private_mobile_usage_1000_subscribers_12_months.csv"
        if not csv.is_file():
            self.skipTest("Synthetic CSV not generated; run scripts/generate_synthetic_data.py")
        panel = load_usage_panel(csv)
        features = build_subscriber_features(panel)
        self.assertEqual(len(features), 1000)
        for col in CLUSTER_FEATURES:
            self.assertIn(col, features.columns)
        for col in TREND_COLS:
            self.assertIn(col, features.columns)


class MlTrainTests(unittest.TestCase):
    def test_train_meets_silhouette(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        csv = repo / "data/raw/private_mobile_usage_1000_subscribers_12_months.csv"
        if not csv.is_file():
            self.skipTest("Synthetic CSV not generated")
        from telekom_profiler.ml.train import train_and_save

        with tempfile.TemporaryDirectory() as tmp:
            summary = train_and_save(
                csv,
                Path(tmp),
                min_silhouette=0.5,
            )
            self.assertGreaterEqual(summary["silhouette"], 0.5)
            self.assertTrue((Path(tmp) / "kmeans.pkl").is_file())


class MlInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._artifacts = Path(__file__).resolve().parents[1] / "artifacts"
        if not (cls._artifacts / "kmeans.pkl").is_file():
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


if __name__ == "__main__":
    unittest.main()
