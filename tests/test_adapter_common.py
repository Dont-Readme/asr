from __future__ import annotations

import unittest

from src.adapters.common import normalize_language_name, unique_csv


class AdapterCommonTest(unittest.TestCase):
    def test_normalize_language_name_handles_short_codes(self) -> None:
        self.assertEqual(normalize_language_name("ko"), "Korean")
        self.assertEqual(normalize_language_name("en"), "English")
        self.assertEqual(normalize_language_name("korean"), "Korean")

    def test_unique_csv_preserves_order(self) -> None:
        self.assertEqual(unique_csv(["Korean", "English", "Korean", ""]), "Korean,English")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
