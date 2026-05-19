"""Tests for Ollama fallback providers."""

import unittest
from unittest.mock import patch

from telekom_profiler.domain import CustomerUsage
from telekom_profiler.services.fallback import FallbackProfileProvider
from telekom_profiler.services.providers import OllamaProfileProvider, RuleBasedProfileProvider

HEAVY_DATA = {
    "data_gb": 95,
    "voice_min": 200,
    "sms_count": 30,
    "roaming_days": 8,
    "data_trend": 15,
    "voice_trend": -5,
}


class FallbackProviderTests(unittest.TestCase):
    @patch(
        "telekom_profiler.services.providers.chat_completion",
        side_effect=RuntimeError("Ollama down"),
    )
    def test_profile_falls_back_on_ollama_error(self, _mock: object) -> None:
        provider = FallbackProfileProvider(
            OllamaProfileProvider(),
            RuleBasedProfileProvider(),
        )
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        result = provider.profile(usage)
        self.assertEqual(result.source, "rule_based_fallback")
        self.assertIn("Streamer", result.markdown)
        self.assertIn("fallback_reason", result.metadata)

    @patch(
        "telekom_profiler.services.providers.chat_completion",
        return_value="### 1. Primary archetype\n**LLM**",
    )
    def test_profile_uses_primary_when_ollama_ok(self, _mock: object) -> None:
        provider = FallbackProfileProvider(
            OllamaProfileProvider(),
            RuleBasedProfileProvider(),
        )
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        result = provider.profile(usage)
        self.assertEqual(result.source, "ollama")
        self.assertIn("LLM", result.markdown)


if __name__ == "__main__":
    unittest.main()
