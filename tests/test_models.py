from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import build_kit_mappings, normalize_kit_templates, parse_kit_mapping_entry


class KitMappingTests(unittest.TestCase):
    def test_parse_simple_entry(self):
        mapping = parse_kit_mapping_entry("PUMPHOUSE")
        self.assertIsNotNone(mapping)
        assert mapping is not None
        self.assertEqual(mapping.display_name, "PUMPHOUSE")
        self.assertEqual(mapping.kit_name, "PUMPHOUSE")
        self.assertEqual(mapping.fabrication_relative_path, "PUMPHOUSE")

    def test_parse_alias_entry(self):
        mapping = parse_kit_mapping_entry("BODY | PAINT PACK => NESTS\\PAINT PACK")
        self.assertIsNotNone(mapping)
        assert mapping is not None
        self.assertEqual(mapping.display_name, "BODY")
        self.assertEqual(mapping.kit_name, "PAINT PACK")
        self.assertEqual(mapping.fabrication_relative_path, "NESTS\\PAINT PACK")

    def test_build_kit_mappings_dedupes_display_name(self):
        mappings = build_kit_mappings(
            [
                "BODY | PAINT PACK",
                "BODY | OTHER PACK",
                "PUMPHOUSE",
            ]
        )
        self.assertEqual([mapping.display_name for mapping in mappings], ["BODY", "PUMPHOUSE"])

    def test_normalize_kit_templates_preserves_alias_shape(self):
        normalized = normalize_kit_templates(["BODY | PAINT PACK => NESTS\\PAINT PACK", "PUMPHOUSE"])
        self.assertEqual(
            normalized,
            ["BODY | PAINT PACK => NESTS\\PAINT PACK", "PUMPHOUSE"],
        )


if __name__ == "__main__":
    unittest.main()
