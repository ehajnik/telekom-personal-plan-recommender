"""Unit tests for domain logic."""

import unittest

from telekom_profiler.domain import (
    CustomerUsage,
    build_scoring_result,
    compute_archetype_distances,
    render_offer_report,
    render_profile_report,
)
from telekom_profiler.prompts import build_profile_prompt

HEAVY_DATA = {
    "data_gb": 95,
    "voice_min": 200,
    "sms_count": 30,
    "roaming_days": 8,
    "data_trend": 15,
    "voice_trend": -5,
}


class DomainTests(unittest.TestCase):
    def test_heavy_data_user_maps_to_streamer(self) -> None:
        primary, _ = compute_archetype_distances(HEAVY_DATA)[0]
        self.assertEqual(primary, "Streamer")
        self.assertIn("Streamer", render_profile_report(HEAVY_DATA))

    def test_offer_references_magenta_mobil(self) -> None:
        profile = render_profile_report(HEAVY_DATA)
        offer = render_offer_report(profile, HEAVY_DATA)
        self.assertIn("MagentaMobil", offer)

    def test_profile_prompt_substitutes_placeholders(self) -> None:
        data = {**HEAVY_DATA, "data_gb": 30, "roaming_days": 2}
        prompt = build_profile_prompt(data)
        self.assertIn("data_gb: 30 GB", prompt)
        self.assertNotIn("{slider_features}", prompt)
        self.assertNotIn("{required_primary}", prompt)
        primary = build_scoring_result(CustomerUsage.from_mapping(data)).primary_name
        self.assertIn(primary, prompt)


if __name__ == "__main__":
    unittest.main()
