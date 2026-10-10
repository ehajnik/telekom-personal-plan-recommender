"""Catalogue integrity: structured catalogue vs LLM reference markdown."""

from __future__ import annotations

import re
import unittest

from telekom_profiler.domain.catalog import (
    ALL_ADDONS,
    ALL_TARIFFS,
    POSTPAID,
    PREPAID,
    cheapest_covering,
    tariff_by_sku,
)
from telekom_profiler.paths import DATA_DIR

PLANS_MD = (DATA_DIR / "plans_and_options.md").read_text(encoding="utf-8")
SUMMARY_MD = (DATA_DIR / "tariffs_private.md").read_text(encoding="utf-8")


def _md_row(sku: str) -> str:
    for line in PLANS_MD.splitlines():
        if line.startswith(f"| {sku} |"):
            return line
    raise AssertionError(f"{sku} missing from plans_and_options.md")


class CatalogConsistencyTests(unittest.TestCase):
    def test_every_tariff_sku_and_price_in_markdown(self) -> None:
        for tariff in ALL_TARIFFS:
            row = _md_row(tariff.sku)
            self.assertIn(f"€{tariff.price_eur:.2f}", row, tariff.sku)
            self.assertIn(tariff.name, row, tariff.sku)

    def test_every_tariff_data_allowance_in_markdown(self) -> None:
        for tariff in ALL_TARIFFS:
            row = _md_row(tariff.sku)
            expected = "Unlimited" if tariff.data_gb is None else f"{tariff.data_gb:g} GB"
            self.assertIn(expected, row, tariff.sku)

    def test_postpaid_annual_roaming_volume_in_markdown(self) -> None:
        for tariff in POSTPAID:
            self.assertIn(f"| {tariff.lg23_data_gb_per_year:g} GB |", _md_row(tariff.sku))

    def test_every_addon_sku_in_markdown(self) -> None:
        for addon in ALL_ADDONS:
            row = _md_row(addon.sku)
            price = re.search(r"€\d+\.\d{2}", addon.price_label)
            if price:
                self.assertIn(price.group(0), row, addon.sku)

    def test_summary_prices_match_catalog(self) -> None:
        for tariff in POSTPAID + PREPAID:
            self.assertIn(f"€{tariff.price_eur:.2f}", SUMMARY_MD, tariff.sku)

    def test_no_retired_products_in_reference_data(self) -> None:
        for retired in ("Travel Mobil Basic", "ADD-SPEC-001", "WeekPass |", "13 GB"):
            self.assertNotIn(retired, PLANS_MD)


class CatalogHelperTests(unittest.TestCase):
    def test_cheapest_covering_picks_smallest_sufficient_tier(self) -> None:
        self.assertEqual(cheapest_covering(POSTPAID, 25).sku, "MM-S-001")
        self.assertEqual(cheapest_covering(POSTPAID, 100).sku, "MM-L-001")
        self.assertEqual(cheapest_covering(POSTPAID, 101).sku, "MM-XL-001")
        self.assertEqual(cheapest_covering(PREPAID, 81).sku, "MP-PP-MAX-001")

    def test_tariff_by_sku(self) -> None:
        self.assertEqual(tariff_by_sku("MM-L-001").data_gb, 100)
        with self.assertRaises(KeyError):
            tariff_by_sku("NOPE")


if __name__ == "__main__":
    unittest.main()
