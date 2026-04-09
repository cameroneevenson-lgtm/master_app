from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models import HomeSnapshot, MasterSettings, PublishedOpsSnapshot
from services.adapter_service import launch_tool
from services.dashboard_service import build_home_snapshot
from services.workspace_service import discover_truck_numbers


class HomePage(QWidget):
    OPS_COLUMNS = ("Truck", "Stage", "Sync", "Risk", "Summary")

    def __init__(self, settings: MasterSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self.refresh_page()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        title = QLabel("Operations Pulse")
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: #253746;")
        subtitle = QLabel(
            "Use the master shell as a cross-check on what is moving, what is blocked, and what is actually getting out the door."
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
            ("released_kit_count", "Released kits"),
            ("unreleased_kit_count", "Needs release"),
            ("blocked_kit_count", "Blocked kits"),
            ("complete_kit_count", "Complete kits"),
        )
        for index, (key, label_text) in enumerate(card_specs):
            box = QGroupBox(label_text)
            layout = QVBoxLayout(box)
            value_label = QLabel("0")
            value_label.setStyleSheet("font-size: 28px; font-weight: 800; color: #1f3a4a;")
            detail_label = QLabel("")
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet("color: #5f6c78;")
            layout.addWidget(value_label)
            layout.addWidget(detail_label)
            self._card_labels[key] = value_label
            self._card_labels[f"{key}_detail"] = detail_label
            cards.addWidget(box, index // 2, index % 2)
        root.addLayout(cards)

        ops_box = QGroupBox("Operations Snapshot")
        ops_layout = QVBoxLayout(ops_box)
        self._ops_summary_label = QLabel("Waiting for dashboard summary...")
        self._ops_summary_label.setWordWrap(True)
        self._ops_summary_label.setStyleSheet("color: #4f5d68; font-weight: 600;")
        self._ops_signal_label = QLabel("")
        self._ops_signal_label.setWordWrap(True)
        self._ops_signal_label.setStyleSheet("color: #6a7580;")
        self._risk_label = QLabel("")
        self._risk_label.setWordWrap(True)
        self._risk_label.setStyleSheet("color: #44515b;")
        self._ops_table = QTableWidget(0, len(self.OPS_COLUMNS))
        self._ops_table.setHorizontalHeaderLabels(self.OPS_COLUMNS)
        self._ops_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ops_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._ops_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._ops_table.verticalHeader().setVisible(False)
        self._ops_table.horizontalHeader().setStretchLastSection(True)
        ops_layout.addWidget(self._ops_summary_label)
        ops_layout.addWidget(self._ops_signal_label)
        ops_layout.addWidget(self._risk_label)
        ops_layout.addWidget(self._ops_table, 1)
        root.addWidget(ops_box, 1)

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
        self._card_labels["released_kit_count"].setText(str(snapshot.released_kit_count))
        self._card_labels["released_kit_count_detail"].setText("TruckKit rows marked released in fab flow.")
        self._card_labels["unreleased_kit_count"].setText(str(snapshot.unreleased_kit_count))
        self._card_labels["unreleased_kit_count_detail"].setText("Active kits still held at release.")
        self._card_labels["blocked_kit_count"].setText(str(snapshot.blocked_kit_count))
        self._card_labels["blocked_kit_count_detail"].setText("Active kits carrying a blocker right now.")
        self._card_labels["complete_kit_count"].setText(str(snapshot.complete_kit_count))
        self._card_labels["complete_kit_count_detail"].setText("Kits whose front stage has reached Complete.")

        self._apply_ops_snapshot(snapshot.ops_snapshot, snapshot)

        lines = [
            f"Discovered trucks: {snapshot.discovered_truck_count}",
            f"Tracked trucks in dashboard DB: {snapshot.dashboard_truck_count}",
            f"Active trucks in registry: {snapshot.active_registry_truck_count}/{snapshot.registry_truck_count}",
            "",
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

    def _apply_ops_snapshot(self, ops_snapshot: PublishedOpsSnapshot | None, snapshot: HomeSnapshot) -> None:
        self._ops_table.setRowCount(0)
        if ops_snapshot is None:
            self._ops_summary_label.setText(
                "Published fab-flow ops snapshot is missing, so this page is falling back to direct counts only."
            )
            self._ops_signal_label.setText(
                f"Released: {snapshot.released_kit_count} | Needs release: {snapshot.unreleased_kit_count} | Blocked: {snapshot.blocked_kit_count}"
            )
            self._risk_label.setText("Run the fabrication dashboard publish flow to surface late-release and schedule-risk signals here.")
            return

        published_text = ops_snapshot.published_at_utc or "(unknown publish time)"
        self._ops_summary_label.setText(
            f"Published fab-flow snapshot: {published_text} | "
            f"Active trucks: {ops_snapshot.active_trucks} | "
            f"Late releases: {ops_snapshot.late_releases} | "
            f"Behind schedule: {ops_snapshot.kits_behind_schedule} | "
            f"Blocked kits: {ops_snapshot.blocked_kits}"
        )
        self._ops_signal_label.setText(
            "Flow signals: "
            f"Laser {ops_snapshot.laser_signal or '-'} | "
            f"Bend buffer {ops_snapshot.bend_buffer_signal or '-'} | "
            f"Weld feed A {ops_snapshot.weld_feed_a_signal or '-'} | "
            f"Weld feed B {ops_snapshot.weld_feed_b_signal or '-'}"
        )

        if ops_snapshot.risk_summary:
            risk_lines = []
            for index, risk in enumerate(ops_snapshot.risk_summary, start=1):
                if risk.detail:
                    risk_lines.append(f"{index}. {risk.title}: {risk.detail}")
                else:
                    risk_lines.append(f"{index}. {risk.title}")
            self._risk_label.setText("Attention:\n" + "\n".join(risk_lines))
        else:
            self._risk_label.setText("Attention:\nNo active high-priority risks were published.")

        self._ops_table.setRowCount(len(ops_snapshot.truck_rows))
        for row_index, row in enumerate(ops_snapshot.truck_rows):
            tone_color = self._tone_color(row.tone)
            values = (
                row.truck_number,
                row.main_stage or "-",
                row.sync_state or "-",
                row.risk_category or "-",
                row.issue_summary or "-",
            )
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if tone_color is not None:
                    item.setBackground(tone_color)
                self._ops_table.setItem(row_index, column_index, item)
        self._ops_table.resizeColumnsToContents()

    @staticmethod
    def _tone_color(tone: str) -> QColor | None:
        clean_tone = str(tone or "").strip().lower()
        if clean_tone == "problem":
            return QColor("#F8D7DA")
        if clean_tone == "caution":
            return QColor("#FFF3BF")
        if clean_tone == "ok":
            return QColor("#D8F3DC")
        return None
