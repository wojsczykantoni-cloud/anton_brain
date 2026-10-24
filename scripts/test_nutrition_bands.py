#!/usr/bin/env python3
"""Tests for the nutrition bands in build_dashboard.py.

    .venv/bin/python scripts/test_nutrition_bands.py
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_dashboard as bd  # noqa: E402


def day(kcal, protein, carbs, fat):
    return {"kcal": kcal, "protein": protein, "carbs": carbs, "fat": fat}


class BandStatusTest(unittest.TestCase):
    def test_kcal_edges(self):
        band = bd.NUTRITION_BANDS["kcal"]
        cases = {
            2349: "bad", 2350: "mid", 2479: "mid", 2480: "good",
            2740: "good", 2741: "mid", 2870: "mid", 2871: "bad",
        }
        for value, expected in cases.items():
            self.assertEqual(bd.band_status(value, band), expected, value)

    def test_protein_fat_carbs_edges(self):
        b = bd.NUTRITION_BANDS
        self.assertEqual(bd.band_status(169, b["protein"]), "mid")
        self.assertEqual(bd.band_status(241, b["protein"]), "bad")
        self.assertEqual(bd.band_status(49, b["fat"]), "bad")
        self.assertEqual(bd.band_status(86, b["fat"]), "mid")
        self.assertEqual(bd.band_status(330, b["carbs"]), "good")
        self.assertEqual(bd.band_status(361, b["carbs"]), "bad")

    def test_missing(self):
        self.assertIsNone(bd.band_status(None, bd.NUTRITION_BANDS["kcal"]))


class RateDayTest(unittest.TestCase):
    def test_2210_two_yellows_is_mid(self):
        # 231 g carbs and 99 g fat are both yellow.
        self.assertEqual(bd.rate_day(day(2610, 183, 231, 99)), "mid")

    def test_1510_red_protein_is_bad(self):
        self.assertEqual(bd.rate_day(day(2611, 255, 281, 48)), "bad")

    def test_0210_one_red_side_macro_is_mid(self):
        self.assertEqual(bd.rate_day(day(2645, 190, 237, 105)), "mid")

    def test_good(self):
        self.assertEqual(bd.rate_day(day(2610, 200, 290, 70)), "good")
        self.assertEqual(bd.rate_day(day(2610, 200, 240, 70)), "good")  # one yellow

    def test_two_reds_is_bad(self):
        self.assertEqual(bd.rate_day(day(2610, 200, 200, 40)), "bad")

    def test_yellow_kcal_is_mid(self):
        self.assertEqual(bd.rate_day(day(2400, 200, 290, 70)), "mid")

    def test_missing_is_none(self):
        self.assertIsNone(bd.rate_day(None))
        self.assertIsNone(bd.rate_day({"kcal": 2610, "protein": 200, "carbs": 290}))


class RateWeekTest(unittest.TestCase):
    def test_average_and_counts_skip_missing_days(self):
        food = {
            "2026-10-17": day(2600, 200, 290, 70),  # good
            "2026-10-18": day(2610, 183, 231, 99),  # mid
            "2026-10-20": day(2611, 255, 281, 48),  # bad
            "2026-10-23": day(2620, 200, 290, 70),  # good
        }
        week = bd.rate_week(food, date(2026, 10, 23))
        self.assertEqual(len(week["days"]), 7)
        self.assertAlmostEqual(week["avg_kcal"], (2600 + 2610 + 2611 + 2620) / 4)
        self.assertEqual(week["status"], "good")
        self.assertEqual(week["counts"], {"good": 2, "mid": 1, "bad": 1, None: 3})

    def test_week_edges(self):
        band = bd.NUTRITION_BANDS["week_kcal"]
        self.assertEqual(bd.band_status(2559.9, band), "mid")
        self.assertEqual(bd.band_status(2660, band), "good")
        self.assertEqual(bd.band_status(2771, band), "bad")

    def test_no_data(self):
        week = bd.rate_week({}, date(2026, 10, 23))
        self.assertIsNone(week["avg_kcal"])
        self.assertIsNone(week["status"])


class ResolveBandsTest(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(bd.resolve_bands(None), bd.NUTRITION_BANDS)
        self.assertEqual(bd.resolve_bands({"kcal": 2610}), bd.NUTRITION_BANDS)

    def test_override_and_invalid_fallback(self):
        bands = bd.resolve_bands({"bands": {
            "fat": {"green": [55, 80]},                       # yellow kept from default
            "carbs": {"green": [300, 200], "yellow": [1, 2]},  # invalid -> default
            "kcal": "nope",
        }})
        self.assertEqual(bands["fat"], {"green": (55, 80), "yellow": (50, 100)})
        self.assertEqual(bands["carbs"], bd.NUTRITION_BANDS["carbs"])
        self.assertEqual(bands["kcal"], bd.NUTRITION_BANDS["kcal"])
        self.assertEqual(bd.NUTRITION_BANDS["fat"]["green"], (60, 85))  # defaults untouched


if __name__ == "__main__":
    unittest.main(verbosity=2)
