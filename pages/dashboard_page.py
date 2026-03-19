from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models import DashboardTruckSummary, MasterSettings
from services.adapter_service import launch_tool
from services.dashboard_service import load_dashboard_kit_rows, load_dashboard_truck_summaries


class DashboardPage(QWidget):
    def __init__(self, settings: MasterSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self._truck_summaries: list[DashboardTruckSummary] = []
        self._build_ui()
        self.refresh_page()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #253746;")
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_page)
        launch_button = QPushButton("Open Fabrication Dashboard")
        launch_button.clicked.connect(self._open_dashboard)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh_button)
        header.addWidget(launch_button)
        root.addLayout(header)

        body = QHBoxLayout()
        self._truck_list = QListWidget()
        self._truck_list.setMaximumWidth(260)
        self._truck_list.currentItemChanged.connect(self._on_truck_changed)
        body.addWidget(self._truck_list, 0)

        right = QVBoxLayout()
        self._summary_label = QLabel("Read-only view of fabrication_flow.db for the selected truck.")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color: #586570;")
        right.addWidget(self._summary_label)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(("Kit", "Release", "Front", "Back", "Blocked", "Reason / Links"))
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        right.addWidget(self._table, 1)

        body.addLayout(right, 1)
        root.addLayout(body, 1)

    def set_settings(self, settings: MasterSettings) -> None:
        self._settings = settings
        self.refresh_page()

    def refresh_page(self) -> None:
        current = self.current_truck_number()
        self._truck_summaries = load_dashboard_truck_summaries(self._settings.dashboard_db_path)
        self._truck_list.clear()
        for summary in self._truck_summaries:
            text = f"{summary.truck_number} | {summary.progress_summary}"
            item = QListWidgetItem(text)
            item.setData(256, summary.truck_number)
            self._truck_list.addItem(item)
        if current:
            self.set_external_truck_number(current)
        elif self._truck_list.count() > 0:
            self._truck_list.setCurrentRow(0)
        else:
            self._table.setRowCount(0)
            self._summary_label.setText("Dashboard database is missing or currently has no trucks.")

    def current_truck_number(self) -> str:
        item = self._truck_list.currentItem()
        if item is None:
            return ""
        return str(item.data(256) or "").strip()

    def set_external_truck_number(self, truck_number: str) -> None:
        wanted = str(truck_number or "").strip().upper()
        if not wanted:
            return
        for index in range(self._truck_list.count()):
            item = self._truck_list.item(index)
            if item is not None and str(item.data(256) or "").strip().upper() == wanted:
                self._truck_list.setCurrentRow(index)
                return

    def _on_truck_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        truck_number = str(current.data(256) or "").strip() if current is not None else ""
        if not truck_number:
            self._table.setRowCount(0)
            return

        summary = next(
            (item for item in self._truck_summaries if item.truck_number.upper() == truck_number.upper()),
            None,
        )
        if summary is not None:
            planned = summary.planned_start_date or "-"
            notes = summary.notes or "-"
            self._summary_label.setText(
                f"{summary.truck_number} | Build order {summary.build_order} | "
                f"Day Zero {planned} | {summary.progress_summary} | Notes: {notes}"
            )

        kit_rows = load_dashboard_kit_rows(self._settings.dashboard_db_path, truck_number)
        self._table.setRowCount(len(kit_rows))
        for row_index, row in enumerate(kit_rows):
            values = (
                row.kit_name,
                row.release_state or "-",
                row.front_stage,
                row.back_stage,
                "Yes" if row.blocked else "No",
                row.blocked_reason or row.pdf_links or "-",
            )
            for column_index, value in enumerate(values):
                self._table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        self._table.resizeColumnsToContents()

    def _open_dashboard(self) -> None:
        try:
            launch_tool(self._settings.dashboard_launcher, self._settings)
        except Exception as exc:
            QMessageBox.critical(self, "Launch Failed", str(exc))

