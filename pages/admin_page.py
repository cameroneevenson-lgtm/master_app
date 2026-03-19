from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models import MasterSettings, normalize_kit_templates
from services.adapter_service import adapter_statuses
from services.workspace_service import discover_truck_numbers
from settings_store import save_settings


class AdminPage(QWidget):
    settingsSaved = Signal(object)

    def __init__(self, settings: MasterSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self._load_settings_into_form()
        self.refresh_diagnostics()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        title = QLabel("Admin + Diagnostics")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #253746;")
        subtitle = QLabel(
            "Centralize roots, launchers, and kit mappings here. Diagnostics surface broken paths before a workflow step fails."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #586570;")
        root.addWidget(title)
        root.addWidget(subtitle)

        config_box = QGroupBox("Settings")
        form = QFormLayout(config_box)
        self.release_root_edit = QLineEdit()
        self.fabrication_root_edit = QLineEdit()
        self.dashboard_db_edit = QLineEdit()
        self.truck_registry_edit = QLineEdit()
        self.truck_explorer_edit = QLineEdit()
        self.dashboard_launcher_edit = QLineEdit()
        self.radan_kitter_edit = QLineEdit()
        self.inventor_entry_edit = QLineEdit()
        self.python_edit = QLineEdit()
        self.rpd_template_edit = QLineEdit()
        self.create_support_folders_checkbox = QCheckBox("Create _bak / _out / _kits when scaffolding")
        self.kit_templates_edit = QPlainTextEdit()
        self.kit_templates_edit.setPlaceholderText(
            "One kit mapping per line.\nExamples:\nBODY | PAINT PACK\nBODY | PAINT PACK => NESTS\\PAINT PACK"
        )
        self.kit_templates_edit.setMinimumHeight(150)

        form.addRow("Release root", self.release_root_edit)
        form.addRow("Fabrication root", self.fabrication_root_edit)
        form.addRow("Dashboard DB", self.dashboard_db_edit)
        form.addRow("Truck registry CSV", self.truck_registry_edit)
        form.addRow("Truck Explorer launcher", self.truck_explorer_edit)
        form.addRow("Dashboard launcher", self.dashboard_launcher_edit)
        form.addRow("RADAN Kitter launcher", self.radan_kitter_edit)
        form.addRow("Inventor entry", self.inventor_entry_edit)
        form.addRow("Python executable", self.python_edit)
        form.addRow("RPD template", self.rpd_template_edit)
        form.addRow("", self.create_support_folders_checkbox)
        form.addRow("Kit templates", self.kit_templates_edit)
        root.addWidget(config_box)

        button_row = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save)
        reload_button = QPushButton("Reload Diagnostics")
        reload_button.clicked.connect(self.refresh_diagnostics)
        button_row.addWidget(save_button)
        button_row.addWidget(reload_button)
        button_row.addStretch(1)
        root.addLayout(button_row)

        diagnostics_box = QGroupBox("Diagnostics")
        diagnostics_layout = QVBoxLayout(diagnostics_box)
        self.diagnostics_label = QLabel("")
        self.diagnostics_label.setWordWrap(True)
        diagnostics_layout.addWidget(self.diagnostics_label)
        root.addWidget(diagnostics_box)
        root.addStretch(1)

    def set_settings(self, settings: MasterSettings) -> None:
        self._settings = settings
        self._load_settings_into_form()
        self.refresh_diagnostics()

    def _load_settings_into_form(self) -> None:
        self.release_root_edit.setText(self._settings.release_root)
        self.fabrication_root_edit.setText(self._settings.fabrication_root)
        self.dashboard_db_edit.setText(self._settings.dashboard_db_path)
        self.truck_registry_edit.setText(self._settings.truck_registry_path)
        self.truck_explorer_edit.setText(self._settings.truck_explorer_launcher)
        self.dashboard_launcher_edit.setText(self._settings.dashboard_launcher)
        self.radan_kitter_edit.setText(self._settings.radan_kitter_launcher)
        self.inventor_entry_edit.setText(self._settings.inventor_to_radan_entry)
        self.python_edit.setText(self._settings.python_executable)
        self.rpd_template_edit.setText(self._settings.rpd_template_path)
        self.create_support_folders_checkbox.setChecked(self._settings.create_support_folders)
        self.kit_templates_edit.setPlainText("\n".join(self._settings.kit_templates))

    def _build_settings_from_form(self) -> MasterSettings:
        raw_templates = [line.strip() for line in self.kit_templates_edit.toPlainText().splitlines()]
        return MasterSettings(
            release_root=self.release_root_edit.text().strip(),
            fabrication_root=self.fabrication_root_edit.text().strip(),
            truck_explorer_launcher=self.truck_explorer_edit.text().strip(),
            dashboard_launcher=self.dashboard_launcher_edit.text().strip(),
            radan_kitter_launcher=self.radan_kitter_edit.text().strip(),
            inventor_to_radan_entry=self.inventor_entry_edit.text().strip(),
            dashboard_db_path=self.dashboard_db_edit.text().strip(),
            truck_registry_path=self.truck_registry_edit.text().strip(),
            rpd_template_path=self.rpd_template_edit.text().strip(),
            python_executable=self.python_edit.text().strip(),
            create_support_folders=self.create_support_folders_checkbox.isChecked(),
            kit_templates=normalize_kit_templates(raw_templates),
        )

    def _save(self) -> None:
        try:
            settings = self._build_settings_from_form()
            save_settings(settings)
            self._settings = settings
            self.refresh_diagnostics()
            self.settingsSaved.emit(settings)
            QMessageBox.information(self, "Save Settings", "Settings saved.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Settings", str(exc))

    def refresh_diagnostics(self) -> None:
        settings = self._build_settings_from_form()
        adapters = adapter_statuses(settings)
        discovered = discover_truck_numbers(settings)
        lines = [
            f"Discovered trucks: {len(discovered)}",
            f"Release root exists: {'yes' if settings.release_root and Path(settings.release_root).exists() else 'no'}",
            f"Fabrication root exists: {'yes' if settings.fabrication_root and Path(settings.fabrication_root).exists() else 'no'}",
            "",
            "Adapters:",
        ]
        for adapter in adapters:
            lines.append(f"- {adapter.label}: {'ready' if adapter.exists else 'missing'}")
            lines.append(f"  {adapter.path_text or '(not configured)'}")
        self.diagnostics_label.setText("\n".join(lines))

