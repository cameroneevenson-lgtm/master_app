from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from models import APP_DIR, MasterSettings, normalize_kit_templates

RUNTIME_DIR = APP_DIR / "_runtime"
SETTINGS_PATH = RUNTIME_DIR / "settings.json"


def _clean_text(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def load_settings() -> MasterSettings:
    if not SETTINGS_PATH.exists():
        return MasterSettings()

    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return MasterSettings()

    defaults = MasterSettings()
    return MasterSettings(
        release_root=_clean_text(payload.get("release_root"), defaults.release_root),
        fabrication_root=_clean_text(payload.get("fabrication_root"), defaults.fabrication_root),
        truck_explorer_launcher=_clean_text(payload.get("truck_explorer_launcher"), defaults.truck_explorer_launcher),
        dashboard_launcher=_clean_text(payload.get("dashboard_launcher"), defaults.dashboard_launcher),
        radan_kitter_launcher=_clean_text(payload.get("radan_kitter_launcher"), defaults.radan_kitter_launcher),
        inventor_to_radan_entry=_clean_text(payload.get("inventor_to_radan_entry"), defaults.inventor_to_radan_entry),
        dashboard_db_path=_clean_text(payload.get("dashboard_db_path"), defaults.dashboard_db_path),
        truck_registry_path=_clean_text(payload.get("truck_registry_path"), defaults.truck_registry_path),
        rpd_template_path=_clean_text(payload.get("rpd_template_path"), defaults.rpd_template_path),
        python_executable=_clean_text(payload.get("python_executable"), defaults.python_executable),
        create_support_folders=bool(payload.get("create_support_folders", defaults.create_support_folders)),
        kit_templates=normalize_kit_templates(payload.get("kit_templates") or defaults.kit_templates),
    )


def save_settings(settings: MasterSettings) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    payload["kit_templates"] = normalize_kit_templates(settings.kit_templates)
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return SETTINGS_PATH

