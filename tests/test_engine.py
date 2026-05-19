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

    def test_reset_engine_clears_singleton(self) -> None:
        from telekom_profiler.services import get_engine

        a = get_engine()
        reset_engine()
        b = get_engine()
        self.assertIsNot(a, b)


if __name__ == "__main__":
    unittest.main()
