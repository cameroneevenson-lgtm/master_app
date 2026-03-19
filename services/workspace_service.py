from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from models import (
    DEFAULT_SUPPORT_FOLDERS,
    MINIMAL_RPD_TEMPLATE,
    MasterSettings,
    WorkspaceKitRow,
    build_kit_mappings,
    clean_text,
    natural_sort_key,
    parse_kit_mapping_entry,
    TRUCK_NUMBER_PATTERN,
)
from services.adapter_service import run_tool_capture
from services.dashboard_service import load_dashboard_truck_summaries

SUPPORTED_SPREADSHEET_SUFFIXES = {".xlsx", ".xls", ".csv"}
IGNORED_SPREADSHEET_SUFFIXES = ("_radan.csv",)
MAX_PREVIEW_DEPTH = 2


def _path_from_text(value: str) -> Path | None:
    text = clean_text(value)
    if not text:
        return None
    return Path(text)


def _discover_trucks_from_root(root: Path | None) -> set[str]:
    names: set[str] = set()
    if root is None or not root.exists():
        return names
    for child in root.iterdir():
        if child.is_dir() and TRUCK_NUMBER_PATTERN.fullmatch(child.name):
            names.add(child.name.upper())
    return names


def discover_truck_numbers(settings: MasterSettings) -> list[str]:
    names: set[str] = set()
    names.update(_discover_trucks_from_root(_path_from_text(settings.release_root)))
    names.update(_discover_trucks_from_root(_path_from_text(settings.fabrication_root)))
    for summary in load_dashboard_truck_summaries(settings.dashboard_db_path):
        names.add(summary.truck_number.upper())
    return sorted(names, key=natural_sort_key)


def _is_generated_spreadsheet(path: Path) -> bool:
    return any(path.name.casefold().endswith(suffix) for suffix in IGNORED_SPREADSHEET_SUFFIXES)


def _detect_spreadsheet(folder: Path) -> tuple[Path | None, str]:
    if not folder.exists():
        return (None, "W folder missing")
    candidates = sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.casefold() in SUPPORTED_SPREADSHEET_SUFFIXES
            and not _is_generated_spreadsheet(path)
        ),
        key=lambda path: natural_sort_key(path.name),
    )
    if len(candidates) == 1:
        return (candidates[0], "Spreadsheet ready")
    if len(candidates) == 0:
        return (None, "Spreadsheet missing")
    return (None, "Spreadsheet ambiguous")


def _shallow_files(root: Path, max_depth: int):
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            continue
        for child in sorted(current.iterdir(), key=lambda path: natural_sort_key(path.name), reverse=True):
            if child.is_file():
                yield child, depth
            elif child.is_dir() and depth < max_depth:
                stack.append((child, depth + 1))


def _detect_nest_summary_pdf(release_kit_dir: Path, project_name: str) -> Path | None:
    if not release_kit_dir.exists():
        return None
    wanted = f"{project_name} nest summary.pdf".casefold()
    for candidate, _depth in _shallow_files(release_kit_dir, MAX_PREVIEW_DEPTH):
        if candidate.name.casefold() == wanted:
            return candidate
    return None


def build_workspace_rows(truck_number: str, settings: MasterSettings) -> list[WorkspaceKitRow]:
    truck_text = clean_text(truck_number).upper()
    if not truck_text:
        return []

    release_root = _path_from_text(settings.release_root) or Path(".")
    fabrication_root = _path_from_text(settings.fabrication_root) or Path(".")

    rows: list[WorkspaceKitRow] = []
    for mapping in build_kit_mappings(settings.kit_templates):
        project_name = f"{truck_text} {mapping.kit_name}".strip()
        release_kit_dir = release_root / truck_text / mapping.kit_name
        project_dir = release_kit_dir / project_name
        rpd_path = project_dir / f"{project_name}.rpd"
        fabrication_kit_dir = fabrication_root / truck_text / Path(mapping.fabrication_relative_path)
        support_dirs = tuple(project_dir / name for name in DEFAULT_SUPPORT_FOLDERS)

        spreadsheet_path, spreadsheet_status = _detect_spreadsheet(fabrication_kit_dir)
        import_csv_path = None
        report_path = None
        if spreadsheet_path is not None:
            import_csv_path = project_dir / f"{spreadsheet_path.stem}_Radan.csv"
            report_path = project_dir / f"{spreadsheet_path.stem}_report.txt"

        preview_pdf = _detect_nest_summary_pdf(release_kit_dir, project_name)
        parts: list[str] = []
        parts.append("RPD ready" if rpd_path.exists() else "RPD missing")
        parts.append(spreadsheet_status)
        if preview_pdf is not None:
            parts.append("Nest Summary")
        if import_csv_path is not None and import_csv_path.exists():
            parts.append("Import CSV on L")

        rows.append(
            WorkspaceKitRow(
                truck_number=truck_text,
                display_name=mapping.display_name,
                kit_name=mapping.kit_name,
                project_name=project_name,
                fabrication_relative_path=mapping.fabrication_relative_path,
                release_kit_dir=release_kit_dir,
                project_dir=project_dir,
                rpd_path=rpd_path,
                fabrication_kit_dir=fabrication_kit_dir,
                spreadsheet_path=spreadsheet_path,
                import_csv_path=import_csv_path,
                report_path=report_path,
                nest_summary_pdf_path=preview_pdf,
                support_dirs=support_dirs,
                status_summary=" | ".join(parts),
            )
        )

    return sorted(rows, key=lambda row: natural_sort_key(row.display_name))


def ensure_project_scaffold(row: WorkspaceKitRow, settings: MasterSettings) -> tuple[str, tuple[Path, ...]]:
    created: list[Path] = []
    for path in (row.release_kit_dir, row.project_dir):
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)

    if settings.create_support_folders:
        for support_dir in row.support_dirs:
            if not support_dir.exists():
                support_dir.mkdir(parents=True, exist_ok=True)
                created.append(support_dir)

    created_mode = "existing"
    if not row.rpd_path.exists():
        template_path = Path(str(settings.rpd_template_path or "").strip())
        if template_path.exists() and template_path.is_file():
            row.rpd_path.write_bytes(template_path.read_bytes())
            created_mode = "template_copy"
        else:
            row.rpd_path.write_text(
                MINIMAL_RPD_TEMPLATE.format(project_name=row.project_name),
                encoding="utf-8",
            )
            created_mode = "minimal_placeholder"
        created.append(row.rpd_path)

    return (created_mode, tuple(created))


def run_inventor_and_copy(
    row: WorkspaceKitRow,
    settings: MasterSettings,
) -> tuple[subprocess.CompletedProcess[str], tuple[Path, ...]]:
    if row.spreadsheet_path is None:
        raise FileNotFoundError("No unique spreadsheet was found for this kit.")
    if not row.project_dir.exists():
        raise FileNotFoundError("Project folder does not exist yet.")

    completed = run_tool_capture(
        settings.inventor_to_radan_entry,
        settings,
        argument_path=row.spreadsheet_path,
    )

    copied: list[Path] = []
    source_csv = row.spreadsheet_path.parent / f"{row.spreadsheet_path.stem}_Radan.csv"
    source_report = row.spreadsheet_path.parent / f"{row.spreadsheet_path.stem}_report.txt"
    if source_csv.exists() and row.import_csv_path is not None:
        shutil.copy2(source_csv, row.import_csv_path)
        copied.append(row.import_csv_path)
    if source_report.exists() and row.report_path is not None:
        shutil.copy2(source_report, row.report_path)
        copied.append(row.report_path)
    return (completed, tuple(copied))

