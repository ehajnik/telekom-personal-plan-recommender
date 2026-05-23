"""Tests for ML scoring fallback to legacy L1 archetypes."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from telekom_profiler.domain import CustomerUsage, build_scoring_result

HEAVY_DATA = {
    "data_gb": 95,
    "voice_min": 200,
    "sms_count": 30,
    "roaming_days": 8,
    "data_trend": 15,
    "voice_trend": -5,
}


class ScoringFallbackTests(unittest.TestCase):
    @patch("telekom_profiler.domain.scoring.use_ml_scoring", return_value=True)
    @patch(
        "telekom_profiler.ml.inference.predict_from_features",
        side_effect=KeyError("missing feature"),
    )
    def test_key_error_sets_legacy_fallback_metadata(
        self,
        _pred: object,
        _ml: object,
    ) -> None:
        result = build_scoring_result(CustomerUsage.from_mapping(HEAVY_DATA))
        self.assertEqual(result.backend, "legacy")
        self.assertIsNotNone(result.fallback_reason)
        self.assertIn("ml_lookup_failed", result.fallback_reason or "")
        self.assertEqual(result.primary_name, "Streamer")

    @patch("telekom_profiler.domain.scoring.use_ml_scoring", return_value=True)
    @patch(
        "telekom_profiler.ml.inference.predict_from_features",
        side_effect=FileNotFoundError("no artifacts"),
    )
    def test_missing_artifacts_sets_legacy_fallback_metadata(
        self,
        _pred: object,
        _ml: object,
    ) -> None:
        result = build_scoring_result(CustomerUsage.from_mapping(HEAVY_DATA))
        self.assertEqual(result.backend, "legacy")
        self.assertIn("ml_artifacts_missing", result.fallback_reason or "")


if __name__ == "__main__":
    unittest.main()
