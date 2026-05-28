"""Tests for Ollama fallback providers."""

import os
import unittest
from unittest.mock import patch

from telekom_profiler.config.profiler_settings import artifacts_available
from telekom_profiler.domain import CustomerUsage
from telekom_profiler.ml.inference import clear_artifacts_cache
from telekom_profiler.services import reset_engine
from telekom_profiler.services.fallback import FallbackOfferProvider, FallbackProfileProvider
from telekom_profiler.services.providers import (
    MlProfileProvider,
    OllamaOfferProvider,
    OllamaProfileProvider,
    RuleBasedOfferProvider,
    RuleBasedProfileProvider,
)

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
        self.assertEqual(result.source, "litellm/ollama")
        self.assertIn("LLM", result.markdown)

    @patch(
        "telekom_profiler.services.providers.chat_completion",
        side_effect=RuntimeError("Ollama down"),
    )
    def test_offer_falls_back_on_ollama_error(self, _mock: object) -> None:
        provider = FallbackOfferProvider(
            OllamaOfferProvider(),
            RuleBasedOfferProvider(),
        )
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        profile = RuleBasedProfileProvider().profile(usage)
        offer = provider.recommend(profile, usage)
        self.assertIn("MagentaMobil", offer)

    @patch.dict(os.environ, {"PROFILER_MODE": "ml"})
    @patch(
        "telekom_profiler.services.providers.chat_completion",
        side_effect=RuntimeError("Ollama down"),
    )
    def test_profile_falls_back_to_ml_when_mode_ml(self, _mock: object) -> None:
        if not artifacts_available():
            self.skipTest("ML artifacts not trained")
        clear_artifacts_cache()
        reset_engine()
        provider = FallbackProfileProvider(
            OllamaProfileProvider(),
            MlProfileProvider(),
        )
        usage = CustomerUsage.from_mapping(HEAVY_DATA)
        result = provider.profile(usage)
        self.assertEqual(result.source, "rule_based_fallback")
        self.assertIn("### 1. Primary usage profile", result.markdown)
        self.assertIn(result.scoring.primary_name, result.markdown)


if __name__ == "__main__":
    unittest.main()
