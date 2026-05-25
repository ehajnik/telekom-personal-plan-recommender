"""Tests for MOSTLY AI synthetic-data helpers."""

from __future__ import annotations

import unittest

import pandas as pd

from telekom_profiler.ml.mostlyai_generator import (
    build_mostlyai_context,
    normalize_generated_panel,
)


def _sample_panel() -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for subscriber_id, data_base, voice_base in (
        ("SUB00001", 10.0, 120.0),
        ("SUB00002", 60.0, 320.0),
    ):
        for month in range(1, 13):
            rows.append(
                {
                    "subscriber_id": subscriber_id,
                    "month": month,
                    "data_gb": data_base + month,
                    "voice_min": voice_base + month * 3.0,
                    "sms_count": 15 + month,
                    "roaming_days": month % 4,
                    "countries_visited": month % 3,
                    "night_usage_ratio": 0.2 + month * 0.01,
                    "weekend_usage_ratio": 0.3 + month * 0.01,
                    "avg_session_mb": 40.0 + month,
                    "active_days": 15 + month,
                    "plan_tier": 2,
                    "lines_total": 2,
                    "lines_active": 2,
                }
            )
    return pd.DataFrame(rows)


class MostlyAiContextTests(unittest.TestCase):
    def test_build_context_adds_month_counts(self) -> None:
        context = build_mostlyai_context(_sample_panel())
        self.assertEqual(set(context["subscriber_id"]), {"SUB00001", "SUB00002"})
        self.assertTrue((context["months_observed"] == 12).all())
        self.assertIn("data_gb_mean", context.columns)
        self.assertIn("data_trend", context.columns)


class MostlyAiNormalizationTests(unittest.TestCase):
    def test_normalize_generated_panel_repairs_shape_and_ranges(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "subscriber_id": "alpha",
                    "month": 3,
                    "data_gb": 20.0,
                    "voice_min": 100.0,
                    "sms_count": 11.2,
                    "roaming_days": 1.0,
                    "countries_visited": 3.0,
                    "night_usage_ratio": 1.4,
                    "weekend_usage_ratio": -0.1,
                    "avg_session_mb": 0.5,
                    "active_days": 40.0,
                    "plan_tier": 6.0,
                    "lines_total": 0.2,
                    "lines_active": 4.8,
                },
                {
                    "subscriber_id": "alpha",
                    "month": 1,
                    "data_gb": 22.0,
                    "voice_min": 90.0,
                    "sms_count": 10.7,
                    "roaming_days": 0.0,
                    "countries_visited": 2.0,
                    "night_usage_ratio": 0.5,
                    "weekend_usage_ratio": 0.4,
                    "avg_session_mb": 5.0,
                    "active_days": 20.0,
                    "plan_tier": 0.0,
                    "lines_total": 2.0,
                    "lines_active": 1.0,
                },
            ]
        )

        repaired = normalize_generated_panel(raw, n_subscribers=2, months=4, seed=7)

        self.assertEqual(len(repaired), 8)
        self.assertEqual(repaired["subscriber_id"].nunique(), 2)
        for subscriber_id, group in repaired.groupby("subscriber_id", sort=True):
            self.assertEqual(group["month"].tolist(), [1, 2, 3, 4], subscriber_id)
        self.assertTrue(repaired["night_usage_ratio"].between(0.0, 1.0).all())
        self.assertTrue(repaired["weekend_usage_ratio"].between(0.0, 1.0).all())
        self.assertTrue((repaired["avg_session_mb"] >= 1.0).all())
        self.assertTrue((repaired["plan_tier"] <= 5.0).all())
        self.assertTrue((repaired["lines_total"] >= 1.0).all())
        self.assertTrue((repaired["lines_active"] <= repaired["lines_total"]).all())
        self.assertTrue((repaired["countries_visited"] <= repaired["roaming_days"]).all())


if __name__ == "__main__":
    unittest.main()
