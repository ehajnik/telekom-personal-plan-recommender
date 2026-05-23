"""Tests for domain models and scoring."""

import unittest
from unittest.mock import patch

from telekom_profiler.domain import CustomerUsage, build_scoring_result
from telekom_profiler.services import ProfilerEngine
from telekom_profiler.services.analysis import profile_customer_structured
from telekom_profiler.services.providers import RuleBasedProfileProvider

HEAVY_DATA = {
    "data_gb": 95,
    "voice_min": 200,
    "sms_count": 30,
    "roaming_days": 8,
    "data_trend": 15,
    "voice_trend": -5,
}


class ModelTests(unittest.TestCase):
    def test_customer_usage_round_trip(self) -> None:
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        self.assertEqual(usage.as_dict(), {k: float(v) for k, v in HEAVY_DATA.items()})

    def test_customer_usage_validate_rejects_out_of_range(self) -> None:
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        with self.assertRaises(ValueError):
            CustomerUsage(
                data_gb=999,
                voice_min=usage.voice_min,
                sms_count=usage.sms_count,
                roaming_days=usage.roaming_days,
                data_trend=usage.data_trend,
                voice_trend=usage.voice_trend,
            ).validate()

    def test_customer_usage_clamp(self) -> None:
        usage = CustomerUsage.from_mapping(
            {**HEAVY_DATA, "data_gb": 999, "data_trend": 100},
            clamp=True,
        )
        self.assertEqual(usage.data_gb, 150.0)
        self.assertEqual(usage.data_trend, 50.0)

    def test_profile_result_state_round_trip(self) -> None:
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        scoring = build_scoring_result(usage)
        from telekom_profiler.domain.models import ProfileResult

        original = ProfileResult(
            markdown="### test",
            usage=usage,
            scoring=scoring,
            source="test",
        )
        restored = ProfileResult.from_state_dict(original.to_state_dict())
        assert restored is not None
        self.assertEqual(restored.scoring.primary_name, "Streamer")
        self.assertEqual(restored.markdown, "### test")

    def test_scoring_primary_streamer(self) -> None:
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        scoring = build_scoring_result(usage)
        self.assertEqual(scoring.primary_name, "Streamer")
        self.assertIn(scoring.confidence, ("High", "Medium", "Low"))

    def test_rule_based_profile_result_has_scoring(self) -> None:
        engine = ProfilerEngine(profile_provider=RuleBasedProfileProvider())
        result = engine.profile(CustomerUsage.from_mapping(HEAVY_DATA))
        self.assertIsNotNone(result.scoring)
        self.assertEqual(result.source, "rule_based")
        self.assertIn("Streamer", result.markdown)

    @patch("telekom_profiler.services.providers.llm_enabled", return_value=False)
    def test_structured_profile_api(self, _mock: object) -> None:
        result = profile_customer_structured(HEAVY_DATA)
        self.assertFalse(result.is_placeholder)
        self.assertEqual(result.scoring.primary_name, "Streamer")


if __name__ == "__main__":
    unittest.main()
