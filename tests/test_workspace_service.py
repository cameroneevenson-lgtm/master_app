from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import MasterSettings
from services.workspace_service import build_workspace_rows, ensure_project_scaffold


def _make_fixture_root() -> Path:
    base = ROOT / "_runtime" / "test_tmp" / uuid4().hex
    base.mkdir(parents=True, exist_ok=True)
    return base


class WorkspaceServiceTests(unittest.TestCase):
    def test_build_workspace_rows_detects_unique_spreadsheet(self):
        root = _make_fixture_root()
        try:
            release_root = root / "release"
            fabrication_root = root / "fabrication"
            truck = "F55334"
            kit = "PAINT PACK"

            (fabrication_root / truck / kit).mkdir(parents=True)
            (fabrication_root / truck / kit / "TruckBom.xlsx").write_text("placeholder", encoding="utf-8")

            settings = MasterSettings(
                release_root=str(release_root),
                fabrication_root=str(fabrication_root),
                kit_templates=["BODY | PAINT PACK"],
            )
            rows = build_workspace_rows(truck, settings)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].spreadsheet_path.name, "TruckBom.xlsx")
            self.assertIn("Spreadsheet ready", rows[0].status_summary)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_ensure_project_scaffold_creates_placeholder_rpd(self):
        root = _make_fixture_root()
        try:
            settings = MasterSettings(
                release_root=str(root / "release"),
                fabrication_root=str(root / "fabrication"),
                kit_templates=["BODY | PAINT PACK"],
                rpd_template_path="",
            )
            row = build_workspace_rows("F55334", settings)[0]
            mode, created = ensure_project_scaffold(row, settings)
            self.assertEqual(mode, "minimal_placeholder")
            self.assertTrue(row.project_dir.exists())
            self.assertTrue(row.rpd_path.exists())
            self.assertGreaterEqual(len(created), 3)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
