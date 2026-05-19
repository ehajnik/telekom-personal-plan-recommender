"""Automated sanity checks (same coverage as scripts/sanity_check.py)."""

import unittest
from pathlib import Path
from unittest.mock import patch

from telekom_profiler import create_demo
from telekom_profiler.paths import ASSETS_DIR, DATA_DIR, PROMPT_TEMPLATES_DIR, THEME_DIR
from telekom_profiler.prompts import build_offer_prompt, build_profile_prompt
from telekom_profiler.services.analysis import profile_customer, recommend_offer

SAMPLE = {
    "data_gb": 95.0,
    "voice_min": 200.0,
    "sms_count": 30.0,
    "roaming_days": 8.0,
    "data_trend": 15.0,
    "voice_trend": -5.0,
}


class SanityTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        paths = [
            ASSETS_DIR / "telekom-logo.svg",
            DATA_DIR / "consumer_archetypes.md",
            DATA_DIR / "tariffs_private.md",
            PROMPT_TEMPLATES_DIR / "run_profile.md",
            PROMPT_TEMPLATES_DIR / "run_offer.md",
            THEME_DIR / "app.css",
        ]
        for path in paths:
            self.assertTrue(path.is_file(), f"missing {path}")

    def test_prompts_have_no_raw_placeholders(self) -> None:
        prompt = build_profile_prompt(SAMPLE)
        self.assertNotIn("{slider_features}", prompt)
        offer = build_offer_prompt("profile text")
        self.assertNotIn("{tariffs_and_options}", offer)

    @patch("telekom_profiler.services.analysis.llm_enabled", return_value=False)
    def test_end_to_end_fallback(self, _mock: object) -> None:
        profile = profile_customer(SAMPLE)
        offer = recommend_offer(profile, SAMPLE)
        self.assertIn("Streamer", profile)
        self.assertIn("MagentaMobil", offer)

    def test_demo_instantiates(self) -> None:
        demo = create_demo()
        self.assertEqual(demo.__class__.__name__, "Blocks")

    def test_app_entry_exists(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "app.py").is_file())


if __name__ == "__main__":
    unittest.main()
