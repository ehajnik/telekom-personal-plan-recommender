"""Tests for analysis service."""

import unittest
from unittest.mock import patch

from telekom_profiler.services.analysis import profile_customer, recommend_offer
from telekom_profiler.services.engine import ProfilerEngine

HEAVY_DATA = {
    "data_gb": 95,
    "voice_min": 200,
    "sms_count": 30,
    "roaming_days": 8,
    "data_trend": 15,
    "voice_trend": -5,
}


class AnalysisServiceTests(unittest.TestCase):
    @patch("telekom_profiler.services.providers.llm_enabled", return_value=False)
    def test_profile_falls_back_without_api_key(self, _mock: object) -> None:
        report = profile_customer(HEAVY_DATA)
        self.assertIn("Streamer", report)

    @patch("telekom_profiler.services.providers.llm_enabled", return_value=True)
    @patch(
        "telekom_profiler.services.providers.chat_completion",
        return_value="### 1. Primary archetype\n**LLM**",
    )
    def test_profile_uses_ollama_when_enabled(
        self, _mock_chat: object, _mock_enabled: object
    ) -> None:
        engine = ProfilerEngine()
        report = profile_customer(HEAVY_DATA, engine=engine)
        self.assertIn("LLM", report)

    @patch("telekom_profiler.services.providers.llm_enabled", return_value=False)
    def test_offer_falls_back_without_api_key(self, _mock: object) -> None:
        profile = profile_customer(HEAVY_DATA)
        offer = recommend_offer(profile, HEAVY_DATA)
        self.assertIn("MagentaMobil", offer)


if __name__ == "__main__":
    unittest.main()
