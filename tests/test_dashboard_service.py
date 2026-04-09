from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import unittest
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.dashboard_service import load_dashboard_kit_rows, load_published_ops_snapshot


def _make_fixture_root() -> Path:
    base = ROOT / "_runtime" / "test_tmp" / uuid4().hex
    base.mkdir(parents=True, exist_ok=True)
    return base


class DashboardServiceTests(unittest.TestCase):
    def test_load_dashboard_kit_rows_uses_real_stage_ids(self):
        root = _make_fixture_root()
        try:
            db_path = root / "fabrication_flow.db"
            with sqlite3.connect(str(db_path)) as connection:
                connection.execute(
                    """
                    CREATE TABLE Truck (
                        id INTEGER PRIMARY KEY,
                        truck_number TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE TruckKit (
                        id INTEGER PRIMARY KEY,
                        truck_id INTEGER NOT NULL,
                        kit_name TEXT NOT NULL,
                        release_state TEXT NOT NULL,
                        front_stage_id INTEGER NOT NULL,
                        back_stage_id INTEGER NOT NULL,
                        blocked INTEGER NOT NULL,
                        blocked_reason TEXT NOT NULL,
                        pdf_links TEXT NOT NULL,
                        is_active INTEGER NOT NULL,
                        kit_order INTEGER NOT NULL
                    )
                    """
                )
                connection.execute("INSERT INTO Truck (id, truck_number) VALUES (1, 'F55334')")
                connection.execute(
                    """
                    INSERT INTO TruckKit (
                        truck_id, kit_name, release_state, front_stage_id, back_stage_id,
                        blocked, blocked_reason, pdf_links, is_active, kit_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (1, "Body", "released", 50, 40, 0, "", "", 1, 1),
                )
                connection.commit()

            rows = load_dashboard_kit_rows(db_path, "F55334")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].front_stage, "Complete")
            self.assertEqual(rows[0].back_stage, "Weld")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_load_published_ops_snapshot_reads_status_json(self):
        root = _make_fixture_root()
        try:
            db_path = root / "fabrication_flow.db"
            db_path.write_text("", encoding="utf-8")
            published_dir = root / "_runtime" / "published"
            published_dir.mkdir(parents=True, exist_ok=True)
            (published_dir / "status.json").write_text(
                json.dumps(
                    {
                        "published_at_utc": "2026-04-08T12:00:00+00:00",
                        "summary": {
                            "active_trucks": 4,
                            "late_releases": 2,
                            "kits_behind_schedule": 3,
                            "blocked_kits": 1,
                            "laser": "dry",
                            "bend_buffer": "low",
                            "weld_feed_a": "ok",
                            "weld_feed_b": "low",
                        },
                        "risk_summary": [
                            {"priority": 95, "title": "Late release", "detail": "2 kits waiting."},
                        ],
                        "truck_rows": [
                            {
                                "truck_number": "F56139",
                                "main_stage": "Release",
                                "sync_state": "Behind",
                                "risk_category": "Late Release",
                                "issue_summary": "2 kit(s) late release.",
                                "tone": "problem",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = load_published_ops_snapshot(db_path)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.active_trucks, 4)
            self.assertEqual(snapshot.late_releases, 2)
            self.assertEqual(snapshot.risk_summary[0].title, "Late release")
            self.assertEqual(snapshot.truck_rows[0].truck_number, "F56139")
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
