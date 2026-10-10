"""Offer engine guarantees: allowance coverage, channel rules, catalogue-only products."""

from __future__ import annotations

import itertools
import re
import unittest

from telekom_profiler.domain.catalog import ALL_ADDONS, ALL_TARIFFS
from telekom_profiler.domain.models import ArchetypeScore, ScoringResult
from telekom_profiler.domain.offers import (
    projected_data_need,
    recommend,
    render_offer_report,
)
from telekom_profiler.domain.profiling import render_ml_profile_report, render_profile_report

PROFILES = (
    "Light / occasional user",
    "Streaming & data-heavy",
    "Voice-centric",
    "Roaming / travel-heavy",
    "Broad usage profile",
    "Streamer",
    "Chatterbox",
    "Essential",
    "Roamer",
    "Messenger",
)
KNOWN_SKUS = {t.sku for t in ALL_TARIFFS} | {a.sku for a in ALL_ADDONS}
SKU_RE = re.compile(r"\b(?:MM|MP|ADD)-[A-Z0-9-]+-\d{3}\b")


def _scoring(name: str) -> ScoringResult:
    return ScoringResult(primary=ArchetypeScore(name, 0.1), secondary=None)


def _usage(data_gb: float, *, voice: float = 300, roaming: float = 1, trend: float = 0) -> dict:
    return {
        "data_gb": data_gb,
        "voice_min": voice,
        "sms_count": 40,
        "roaming_days": roaming,
        "data_trend": trend,
        "voice_trend": 0,
    }


class OfferSizingTests(unittest.TestCase):
    def test_tariff_always_covers_projected_need(self) -> None:
        for profile, data_gb, trend, roaming, voice in itertools.product(
            PROFILES, (0, 0.5, 3, 12, 25, 45, 70, 95, 120, 150), (-30, 0, 25, 50), (0, 5, 15),
            (20, 300, 2000),
        ):
            usage = _usage(data_gb, voice=voice, roaming=roaming, trend=trend)
            rec = recommend(usage, _scoring(profile))
            need = projected_data_need(data_gb, trend)
            with self.subTest(profile=profile, data=data_gb, trend=trend, roaming=roaming):
                self.assertTrue(rec.tariff.covers(need), f"{rec.tariff.sku} < {need:.1f} GB")
                if rec.alternative is not None:
                    self.assertTrue(rec.alternative.covers(need))

    def test_declining_trend_does_not_shrink_need(self) -> None:
        self.assertAlmostEqual(projected_data_need(40, -30), projected_data_need(40, 0))

    def test_broad_usage_reference_customer_not_undersized(self) -> None:
        # Regression: Broad usage (≈59 GB) used to be offered MagentaMobil S (30 GB).
        rec = recommend(_usage(59, voice=618), _scoring("Broad usage profile"))
        self.assertEqual(rec.tariff.sku, "MM-L-001")

    def test_light_user_gets_prepaid(self) -> None:
        rec = recommend(_usage(4, voice=80), _scoring("Light / occasional user"))
        self.assertEqual(rec.tariff.family, "prepaid")
        self.assertEqual(rec.tariff.sku, "MP-PP-M-001")

    def test_prepaid_s_only_with_low_voice(self) -> None:
        tiny = recommend(_usage(0.5, voice=30), _scoring("Light / occasional user"))
        self.assertEqual(tiny.tariff.sku, "MP-PP-S-001")
        chatty = recommend(_usage(0.5, voice=200), _scoring("Light / occasional user"))
        self.assertNotEqual(chatty.tariff.sku, "MP-PP-S-001")

    def test_traveller_gets_at_least_l_and_pass(self) -> None:
        rec = recommend(_usage(20, roaming=12), _scoring("Roaming / travel-heavy"))
        self.assertIn(rec.tariff.sku, ("MM-L-001", "MM-XL-001"))
        self.assertIn("ADD-TS-2DAY-001", {a.sku for a in rec.addons})
        long_stay = recommend(_usage(20, roaming=20), _scoring("Roaming / travel-heavy"))
        self.assertIn("ADD-TS-4W-LG2-001", {a.sku for a in long_stay.addons})

    def test_no_travel_pass_without_travel(self) -> None:
        rec = recommend(_usage(60, roaming=1), _scoring("Streaming & data-heavy"))
        self.assertFalse(rec.addons)


class CatalogOnlyProductTests(unittest.TestCase):
    FORBIDDEN = ("Data Boost", "EU Roaming Plus", "World Roaming Pack", "M+", "Travel Mobil")

    def _assert_catalog_only(self, text: str) -> None:
        unknown = set(SKU_RE.findall(text)) - KNOWN_SKUS
        self.assertFalse(unknown, f"unknown SKUs: {unknown}")
        for phrase in self.FORBIDDEN:
            self.assertNotIn(phrase, text)

    def test_offer_reports_reference_catalog_only(self) -> None:
        for profile in PROFILES:
            for data_gb, roaming in ((2, 0), (60, 3), (120, 16)):
                usage = _usage(data_gb, roaming=roaming, trend=20)
                self._assert_catalog_only(render_offer_report("", usage, scoring=_scoring(profile)))

    def test_profile_reports_reference_catalog_only(self) -> None:
        for data_gb, voice, sms, roaming in ((2, 50, 10, 0), (90, 1500, 200, 12)):
            usage = {**_usage(data_gb, voice=voice, roaming=roaming, trend=20), "sms_count": sms}
            self._assert_catalog_only(render_profile_report(usage))
            self._assert_catalog_only(
                render_ml_profile_report("Broad usage profile", usage, [], profile={})
            )

    def test_ml_report_shows_customer_numbers(self) -> None:
        usage = _usage(77, voice=640)
        report = render_ml_profile_report(
            "Broad usage profile",
            usage,
            [],
            profile={"centroid": {"avg_monthly_data_gb": 59.2, "avg_monthly_voice_min": 618}},
        )
        self.assertIn("| Data (GB / month) | 77 | 59 |", report)
        self.assertIn("| Voice (min / month) | 640 | 618 |", report)


if __name__ == "__main__":
    unittest.main()
