from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models import HomeSnapshot, MasterSettings
from services.adapter_service import launch_tool
from services.dashboard_service import build_home_snapshot
from services.workspace_service import discover_truck_numbers


class HomePage(QWidget):
    def __init__(self, settings: MasterSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self.refresh_page()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        title = QLabel("Master App")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #253746;")
        subtitle = QLabel(
            "A first-pass operations shell that connects truck workflow, dashboard state, and production tools."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #5c6874; font-size: 13px;")

        root.addWidget(title)
        root.addWidget(subtitle)

        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        self._card_labels: dict[str, QLabel] = {}
        card_specs = (
            ("discovered_truck_count", "Discovered trucks"),
            ("dashboard_truck_count", "Dashboard trucks"),
            ("registry_truck_count", "Registry trucks"),
            ("active_registry_truck_count", "Active registry"),
        )
        for index, (key, label_text) in enumerate(card_specs):
            box = QGroupBox(label_text)
            layout = QVBoxLayout(box)
            value_label = QLabel("0")
            value_label.setStyleSheet("font-size: 28px; font-weight: 800; color: #1f3a4a;")
            detail_label = QLabel("")
            detail_label.setStyleSheet("color: #5f6c78;")
            layout.addWidget(value_label)
            layout.addWidget(detail_label)
            self._card_labels[key] = value_label
            self._card_labels[f"{key}_detail"] = detail_label
            cards.addWidget(box, index // 2, index % 2)
        root.addLayout(cards)

        actions_box = QGroupBox("Quick Launch")
        actions_layout = QHBoxLayout(actions_box)
        for label_text, attr_name in (
            ("Open Truck Explorer", "truck_explorer_launcher"),
            ("Open Dashboard", "dashboard_launcher"),
            ("Open RADAN Kitter", "radan_kitter_launcher"),
        ):
            button = QPushButton(label_text)
            button.clicked.connect(lambda _checked=False, attr=attr_name: self._launch_path(attr))
            actions_layout.addWidget(button)
        refresh_button = QPushButton("Refresh Overview")
        refresh_button.clicked.connect(self.refresh_page)
        actions_layout.addWidget(refresh_button)
        root.addWidget(actions_box)

        diagnostics_box = QGroupBox("Configuration Snapshot")
        diagnostics_layout = QVBoxLayout(diagnostics_box)
        self._diagnostics_label = QLabel("")
        self._diagnostics_label.setWordWrap(True)
        diagnostics_layout.addWidget(self._diagnostics_label)
        root.addWidget(diagnostics_box)
        root.addStretch(1)

    def set_settings(self, settings: MasterSettings) -> None:
        self._settings = settings
        self.refresh_page()

    def _launch_path(self, attr_name: str) -> None:
        try:
            launch_tool(getattr(self._settings, attr_name), self._settings)
        except Exception as exc:
            QMessageBox.critical(self, "Launch Failed", str(exc))

    def refresh_page(self) -> None:
        snapshot = build_home_snapshot(
            self._settings,
            discovered_truck_count=len(discover_truck_numbers(self._settings)),
        )
        self._apply_snapshot(snapshot)

    def _apply_snapshot(self, snapshot: HomeSnapshot) -> None:
        self._card_labels["discovered_truck_count"].setText(str(snapshot.discovered_truck_count))
        self._card_labels["discovered_truck_count_detail"].setText(
            "Union of release root, fabrication root, and dashboard database"
        )
        self._card_labels["dashboard_truck_count"].setText(str(snapshot.dashboard_truck_count))
        self._card_labels["dashboard_truck_count_detail"].setText(
            "Rows visible from fabrication_flow.db"
        )
        self._card_labels["registry_truck_count"].setText(str(snapshot.registry_truck_count))
        self._card_labels["registry_truck_count_detail"].setText(
            "Rows found in truck_registry.csv"
        )
        self._card_labels["active_registry_truck_count"].setText(str(snapshot.active_registry_truck_count))
        self._card_labels["active_registry_truck_count_detail"].setText(
            "Registry rows marked active"
        )

        lines = [
            f"Release root: {'ready' if snapshot.release_root_exists else 'missing'}",
            f"Fabrication root: {'ready' if snapshot.fabrication_root_exists else 'missing'}",
            f"Dashboard DB: {'ready' if snapshot.dashboard_db_exists else 'missing'}",
            "",
            "Tool paths:",
        ]
        for adapter in snapshot.adapters:
            lines.append(f"- {adapter.label}: {'ready' if adapter.exists else 'missing'}")
            lines.append(f"  {adapter.path_text or '(not configured)'}")
        self._diagnostics_label.setText("\n".join(lines))

