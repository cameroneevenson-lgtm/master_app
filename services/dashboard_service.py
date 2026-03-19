from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from models import DashboardKitRow, DashboardTruckSummary, HomeSnapshot, MasterSettings
from services.adapter_service import adapter_statuses

STAGE_LABELS = {
    0: "Release",
    1: "Laser",
    2: "Bend",
    3: "Weld",
    4: "Complete",
}


def _stage_label(stage_id: int | None) -> str:
    return STAGE_LABELS.get(int(stage_id or 0), str(stage_id or 0))


def load_dashboard_truck_summaries(db_path: str | Path) -> list[DashboardTruckSummary]:
    target = Path(str(db_path))
    if not target.exists():
        return []

    with sqlite3.connect(str(target)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                t.truck_number,
                COALESCE(t.planned_start_date, '') AS planned_start_date,
                COALESCE(t.notes, '') AS notes,
                COALESCE(t.is_visible, 1) AS is_visible,
                COALESCE(t.build_order, 0) AS build_order,
                COUNT(k.id) AS kit_count,
                SUM(CASE WHEN COALESCE(k.front_stage_id, 0) = 4 THEN 1 ELSE 0 END) AS complete_kit_count
            FROM Truck t
            LEFT JOIN TruckKit k
                ON k.truck_id = t.id
                AND COALESCE(k.is_active, 1) = 1
            GROUP BY t.id, t.truck_number, t.planned_start_date, t.notes, t.is_visible, t.build_order
            ORDER BY COALESCE(t.build_order, 0), t.truck_number
            """
        ).fetchall()

    return [
        DashboardTruckSummary(
            truck_number=str(row["truck_number"] or "").strip(),
            planned_start_date=str(row["planned_start_date"] or "").strip(),
            notes=str(row["notes"] or "").strip(),
            is_visible=bool(row["is_visible"]),
            build_order=int(row["build_order"] or 0),
            kit_count=int(row["kit_count"] or 0),
            complete_kit_count=int(row["complete_kit_count"] or 0),
        )
        for row in rows
        if str(row["truck_number"] or "").strip()
    ]


def load_dashboard_kit_rows(db_path: str | Path, truck_number: str) -> list[DashboardKitRow]:
    target = Path(str(db_path))
    wanted = str(truck_number or "").strip()
    if not target.exists() or not wanted:
        return []

    with sqlite3.connect(str(target)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                k.kit_name,
                COALESCE(k.release_state, '') AS release_state,
                COALESCE(k.front_stage_id, 0) AS front_stage_id,
                COALESCE(k.back_stage_id, 0) AS back_stage_id,
                COALESCE(k.blocked, 0) AS blocked,
                COALESCE(k.blocked_reason, '') AS blocked_reason,
                COALESCE(k.pdf_links, '') AS pdf_links
            FROM Truck t
            JOIN TruckKit k
                ON k.truck_id = t.id
            WHERE t.truck_number = ?
              AND COALESCE(k.is_active, 1) = 1
            ORDER BY COALESCE(k.kit_order, 0), k.kit_name
            """,
            (wanted,),
        ).fetchall()

    return [
        DashboardKitRow(
            kit_name=str(row["kit_name"] or "").strip(),
            release_state=str(row["release_state"] or "").strip(),
            front_stage=_stage_label(int(row["front_stage_id"] or 0)),
            back_stage=_stage_label(int(row["back_stage_id"] or 0)),
            blocked=bool(row["blocked"]),
            blocked_reason=str(row["blocked_reason"] or "").strip(),
            pdf_links=str(row["pdf_links"] or "").strip(),
        )
        for row in rows
    ]


def load_truck_registry_stats(csv_path: str | Path) -> tuple[int, int]:
    target = Path(str(csv_path))
    if not target.exists():
        return (0, 0)

    total = 0
    active = 0
    with target.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            truck_number = str(row.get("truck_number") or "").strip()
            if not truck_number:
                continue
            total += 1
            flag = str(row.get("is_active") or "").strip().lower()
            if flag in {"1", "true", "yes", "y", "on"}:
                active += 1
    return (total, active)


def build_home_snapshot(settings: MasterSettings, discovered_truck_count: int) -> HomeSnapshot:
    dashboard_trucks = load_dashboard_truck_summaries(settings.dashboard_db_path)
    registry_total, registry_active = load_truck_registry_stats(settings.truck_registry_path)
    return HomeSnapshot(
        discovered_truck_count=discovered_truck_count,
        dashboard_truck_count=len(dashboard_trucks),
        registry_truck_count=registry_total,
        active_registry_truck_count=registry_active,
        release_root_exists=Path(settings.release_root).exists(),
        fabrication_root_exists=Path(settings.fabrication_root).exists(),
        dashboard_db_exists=Path(settings.dashboard_db_path).exists(),
        adapters=adapter_statuses(settings),
    )

