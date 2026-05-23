"""Tests for ProfilerEngine."""

import unittest

from telekom_profiler.domain import CustomerUsage
from telekom_profiler.services import ProfilerEngine, reset_engine
from telekom_profiler.services.providers import RuleBasedOfferProvider, RuleBasedProfileProvider

HEAVY_DATA = {
    "data_gb": 95,
    "voice_min": 200,
    "sms_count": 30,
    "roaming_days": 8,
    "data_trend": 15,
    "voice_trend": -5,
}

LIGHT_DATA = {
    "data_gb": 5,
    "voice_min": 50,
    "sms_count": 10,
    "roaming_days": 1,
    "data_trend": 0,
    "voice_trend": 0,
}


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_engine()

    def tearDown(self) -> None:
        reset_engine()

    def test_recommend_accepts_profile_result(self) -> None:
        engine = ProfilerEngine(
            profile_provider=RuleBasedProfileProvider(),
            offer_provider=RuleBasedOfferProvider(),
        )
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        profile = engine.profile(usage)
        offer = engine.recommend(profile, usage)
        self.assertIn("MagentaMobil", offer)
        self.assertIn("Streamer", offer)

    def test_recommend_rescores_for_current_usage(self) -> None:
        engine = ProfilerEngine(
            profile_provider=RuleBasedProfileProvider(),
            offer_provider=RuleBasedOfferProvider(),
        )
        profile = engine.profile(CustomerUsage.from_mapping(LIGHT_DATA))
        self.assertEqual(profile.scoring.primary_name, "Essential")
        offer = engine.recommend(profile, CustomerUsage.from_mapping(HEAVY_DATA))
        self.assertIn("XL", offer)
        self.assertIn("Streamer", offer)

    def test_profile_clamps_out_of_range_usage(self) -> None:
        engine = ProfilerEngine(
            profile_provider=RuleBasedProfileProvider(),
            offer_provider=RuleBasedOfferProvider(),
        )
        result = engine.profile({**HEAVY_DATA, "data_gb": 999})
        self.assertEqual(result.usage.data_gb, 150.0)

    def test_reset_engine_clears_singleton(self) -> None:
        from telekom_profiler.services import get_engine

        a = get_engine()
        reset_engine()
        b = get_engine()
        self.assertIsNot(a, b)


if __name__ == "__main__":
    unittest.main()
