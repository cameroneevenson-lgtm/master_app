from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from models import AppAdapterStatus, MasterSettings


def _python_executable(settings: MasterSettings) -> str:
    configured = Path(str(settings.python_executable or "").strip())
    if configured.exists():
        return str(configured)
    return sys.executable


def build_command(
    entry_path: Path | str,
    settings: MasterSettings,
    argument_path: Path | str | None = None,
) -> list[str]:
    entry = Path(str(entry_path))
    suffix = entry.suffix.casefold()
    if suffix == ".py":
        command = [_python_executable(settings), str(entry)]
    elif suffix in {".bat", ".cmd"}:
        command = ["cmd.exe", "/c", str(entry)]
    else:
        command = [str(entry)]
    if argument_path is not None:
        command.append(str(Path(str(argument_path))))
    return command


def launch_tool(
    entry_path: Path | str,
    settings: MasterSettings,
    argument_path: Path | str | None = None,
) -> None:
    entry = Path(str(entry_path))
    if not entry.exists():
        raise FileNotFoundError(str(entry))
    subprocess.Popen(
        build_command(entry, settings, argument_path=argument_path),
        cwd=str(entry.parent),
    )


def run_tool_capture(
    entry_path: Path | str,
    settings: MasterSettings,
    argument_path: Path | str | None = None,
) -> subprocess.CompletedProcess[str]:
    entry = Path(str(entry_path))
    if not entry.exists():
        raise FileNotFoundError(str(entry))
    return subprocess.run(
        build_command(entry, settings, argument_path=argument_path),
        cwd=str(entry.parent),
        text=True,
        capture_output=True,
    )


def open_path(path: Path | str) -> None:
    target = Path(str(path))
    if not target.exists():
        raise FileNotFoundError(str(target))
    os.startfile(str(target))  # type: ignore[attr-defined]


def adapter_statuses(settings: MasterSettings) -> tuple[AppAdapterStatus, ...]:
    pairs = (
        ("Truck Nest Explorer", settings.truck_explorer_launcher),
        ("Fabrication Dashboard", settings.dashboard_launcher),
        ("RADAN Kitter", settings.radan_kitter_launcher),
        ("Inventor -> Radan", settings.inventor_to_radan_entry),
        ("Dashboard DB", settings.dashboard_db_path),
        ("Truck Registry CSV", settings.truck_registry_path),
    )
    return tuple(
        AppAdapterStatus(
            label=label,
            path_text=str(path_text or "").strip(),
            exists=Path(str(path_text or "").strip()).exists(),
        )
        for label, path_text in pairs
    )

