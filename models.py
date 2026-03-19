from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

APP_DIR = Path(__file__).resolve().parent
TOOLS_DIR = APP_DIR.parent

DEFAULT_RELEASE_ROOT = r"L:\BATTLESHIELD\F-LARGE FLEET"
DEFAULT_FABRICATION_ROOT = r"W:\LASER\For Battleshield Fabrication"
DEFAULT_TRUCK_EXPLORER_LAUNCHER = str(TOOLS_DIR / "truck_nest_explorer" / "truck_nest_explorer.bat")
DEFAULT_DASHBOARD_LAUNCHER = str(TOOLS_DIR / "fabrication_flow_dashboard" / "run_app.bat")
DEFAULT_RADAN_KITTER_LAUNCHER = str(TOOLS_DIR / "radan_kitter" / "radan_kitter.bat")
DEFAULT_INVENTOR_TO_RADAN_ENTRY = str(TOOLS_DIR / "inventor_to_radan" / "inventor_to_radan.bat")
DEFAULT_DASHBOARD_DB_PATH = str(TOOLS_DIR / "fabrication_flow_dashboard" / "fabrication_flow.db")
DEFAULT_TRUCK_REGISTRY_PATH = str(TOOLS_DIR / "fabrication_flow_dashboard" / "truck_registry.csv")
DEFAULT_RPD_TEMPLATE_PATH = str(TOOLS_DIR / "truck_nest_explorer" / "Template" / "Template.rpd")
DEFAULT_VENV_PYTHON = r"C:\Tools\.venv\Scripts\python.exe"
DEFAULT_SUPPORT_FOLDERS = ("_bak", "_out", "_kits")
DEFAULT_KIT_TEMPLATES = [
    "PAINT PACK",
    "INTERIOR PACK",
    "EXTERIOR PACK",
    "CONSOLE PACK",
    "CHASSIS PACK",
    "PUMP HOUSE => PUMP PACK\\PUMP HOUSE",
    "PUMP COVERING => PUMP PACK\\COVERING",
    "PUMP MOUNTS => PUMP PACK\\MOUNTS",
    "PUMP BRACKETS => PUMP PACK\\BRACKETS",
    "STEP PACK",
    "OPERATIONAL PANELS => PUMP PACK\\OPERATIONAL PANELS",
]
TRUCK_NUMBER_PATTERN = re.compile(r"^F\d{5}$", re.IGNORECASE)

MINIMAL_RPD_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<Project xmlns="http://www.radan.com/ns/project">
  <Name>{project_name}</Name>
  <Parts />
</Project>
"""


def clean_text(value: object) -> str:
    return str(value or "").strip()


def natural_sort_key(value: str) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", value)]


@dataclass(frozen=True)
class KitMapping:
    display_name: str
    kit_name: str
    fabrication_relative_path: str


def _normalize_relative_path(value: object) -> str:
    text = str(value or "").strip().replace("/", "\\")
    parts = [segment.strip() for segment in text.split("\\") if segment.strip()]
    return "\\".join(parts)


def parse_kit_mapping_entry(value: object) -> KitMapping | None:
    text = clean_text(value)
    if not text:
        return None

    if "=>" in text:
        name_part, fabrication_relative_path = [part.strip() for part in text.split("=>", 1)]
    else:
        name_part = text
        fabrication_relative_path = ""

    if "|" in name_part:
        display_name, kit_name = [part.strip() for part in name_part.split("|", 1)]
    else:
        display_name = name_part
        kit_name = name_part

    display_name = clean_text(display_name)
    kit_name = clean_text(kit_name)
    fabrication_relative_path = _normalize_relative_path(fabrication_relative_path or kit_name)
    if not display_name or not kit_name or not fabrication_relative_path:
        return None

    return KitMapping(
        display_name=display_name,
        kit_name=kit_name,
        fabrication_relative_path=fabrication_relative_path,
    )


def build_kit_mappings(values: list[object] | None) -> list[KitMapping]:
    cleaned: list[KitMapping] = []
    seen_display_names: set[str] = set()
    seen_kit_names: set[str] = set()
    for raw in values or list(DEFAULT_KIT_TEMPLATES):
        mapping = parse_kit_mapping_entry(raw)
        if mapping is None:
            continue
        display_key = mapping.display_name.casefold()
        kit_key = mapping.kit_name.casefold()
        if display_key in seen_display_names or kit_key in seen_kit_names:
            continue
        seen_display_names.add(display_key)
        seen_kit_names.add(kit_key)
        cleaned.append(mapping)
    return cleaned


def normalize_kit_templates(values: list[object] | None) -> list[str]:
    normalized: list[str] = []
    for mapping in build_kit_mappings(values):
        if mapping.display_name.casefold() == mapping.kit_name.casefold():
            name_text = mapping.kit_name
        else:
            name_text = f"{mapping.display_name} | {mapping.kit_name}"
        if mapping.fabrication_relative_path.casefold() == mapping.kit_name.casefold():
            normalized.append(name_text)
        else:
            normalized.append(f"{name_text} => {mapping.fabrication_relative_path}")
    return normalized


@dataclass
class MasterSettings:
    release_root: str = DEFAULT_RELEASE_ROOT
    fabrication_root: str = DEFAULT_FABRICATION_ROOT
    truck_explorer_launcher: str = DEFAULT_TRUCK_EXPLORER_LAUNCHER
    dashboard_launcher: str = DEFAULT_DASHBOARD_LAUNCHER
    radan_kitter_launcher: str = DEFAULT_RADAN_KITTER_LAUNCHER
    inventor_to_radan_entry: str = DEFAULT_INVENTOR_TO_RADAN_ENTRY
    dashboard_db_path: str = DEFAULT_DASHBOARD_DB_PATH
    truck_registry_path: str = DEFAULT_TRUCK_REGISTRY_PATH
    rpd_template_path: str = DEFAULT_RPD_TEMPLATE_PATH
    python_executable: str = DEFAULT_VENV_PYTHON
    create_support_folders: bool = True
    kit_templates: list[str] = field(default_factory=lambda: list(DEFAULT_KIT_TEMPLATES))


@dataclass(frozen=True)
class AppAdapterStatus:
    label: str
    path_text: str
    exists: bool


@dataclass(frozen=True)
class HomeSnapshot:
    discovered_truck_count: int
    dashboard_truck_count: int
    registry_truck_count: int
    active_registry_truck_count: int
    release_root_exists: bool
    fabrication_root_exists: bool
    dashboard_db_exists: bool
    adapters: tuple[AppAdapterStatus, ...]


@dataclass(frozen=True)
class DashboardTruckSummary:
    truck_number: str
    planned_start_date: str
    notes: str
    is_visible: bool
    build_order: int
    kit_count: int
    complete_kit_count: int

    @property
    def progress_summary(self) -> str:
        if self.kit_count <= 0:
            return "No kits"
        return f"{self.complete_kit_count}/{self.kit_count} complete"


@dataclass(frozen=True)
class DashboardKitRow:
    kit_name: str
    release_state: str
    front_stage: str
    back_stage: str
    blocked: bool
    blocked_reason: str
    pdf_links: str


@dataclass(frozen=True)
class WorkspaceKitRow:
    truck_number: str
    display_name: str
    kit_name: str
    project_name: str
    fabrication_relative_path: str
    release_kit_dir: Path
    project_dir: Path
    rpd_path: Path
    fabrication_kit_dir: Path
    spreadsheet_path: Path | None
    import_csv_path: Path | None
    report_path: Path | None
    nest_summary_pdf_path: Path | None
    support_dirs: tuple[Path, ...]
    status_summary: str
