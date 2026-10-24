#!/usr/bin/env python3
"""Tests for the nutrition bands in build_dashboard.py.

    .venv/bin/python scripts/test_nutrition_bands.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_dashboard as bd  # noqa: E402


class BandStatusTest(unittest.TestCase):
    def test_week_edges(self):
        band = bd.NUTRITION_BANDS["week_kcal"]
        self.assertEqual(bd.band_status(2559.9, band), "mid")
        self.assertEqual(bd.band_status(2660, band), "good")
        self.assertEqual(bd.band_status(2771, band), "bad")

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
