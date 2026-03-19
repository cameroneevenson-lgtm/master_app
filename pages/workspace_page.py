from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models import MasterSettings, WorkspaceKitRow
from services.adapter_service import launch_tool, open_path
from services.workspace_service import (
    build_workspace_rows,
    discover_truck_numbers,
    ensure_project_scaffold,
    run_inventor_and_copy,
)


class WorkspacePage(QWidget):
    truckSelected = Signal(str)

    TABLE_COLUMNS = (
        "Kit",
        "L Folder",
        "Project",
        "RPD",
        "W Folder",
        "Spreadsheet",
        "Import CSV",
        "Summary",
    )

    def __init__(self, settings: MasterSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self._all_trucks: list[str] = []
        self._current_rows: list[WorkspaceKitRow] = []
        self._build_ui()
        self.refresh_page()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Truck Workspace")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #253746;")
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter trucks...")
        self._search_edit.textChanged.connect(self._apply_filter)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_page)
        open_explorer_button = QPushButton("Open Truck Explorer")
        open_explorer_button.clicked.connect(self._open_explorer)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self._search_edit)
        header.addWidget(refresh_button)
        header.addWidget(open_explorer_button)
        root.addLayout(header)

        body = QHBoxLayout()

        self._truck_list = QListWidget()
        self._truck_list.setMaximumWidth(240)
        self._truck_list.currentItemChanged.connect(self._on_truck_changed)
        body.addWidget(self._truck_list, 0)

        right = QVBoxLayout()
        self._summary_label = QLabel("Select a truck to inspect kit status across L and W.")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color: #586570;")
        right.addWidget(self._summary_label)

        self._table = QTableWidget(0, len(self.TABLE_COLUMNS))
        self._table.setHorizontalHeaderLabels(self.TABLE_COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        right.addWidget(self._table, 1)

        actions = QHBoxLayout()
        create_button = QPushButton("Create Project Scaffold")
        create_button.clicked.connect(self._create_scaffold)
        inventor_button = QPushButton("Run Inventor + Copy")
        inventor_button.clicked.connect(self._run_inventor)
        kitter_button = QPushButton("Launch RADAN Kitter")
        kitter_button.clicked.connect(self._launch_kitter)
        project_button = QPushButton("Open Project Folder")
        project_button.clicked.connect(self._open_project_folder)
        fabrication_button = QPushButton("Open W Folder")
        fabrication_button.clicked.connect(self._open_fabrication_folder)
        pdf_button = QPushButton("Open Nest Summary")
        pdf_button.clicked.connect(self._open_nest_summary)
        for button in (
            create_button,
            inventor_button,
            kitter_button,
            project_button,
            fabrication_button,
            pdf_button,
        ):
            actions.addWidget(button)
        right.addLayout(actions)
        body.addLayout(right, 1)
        root.addLayout(body, 1)

    def set_settings(self, settings: MasterSettings) -> None:
        self._settings = settings
        self.refresh_page()

    def set_external_truck_number(self, truck_number: str) -> None:
        wanted = str(truck_number or "").strip().upper()
        if not wanted:
            return
        for index in range(self._truck_list.count()):
            item = self._truck_list.item(index)
            if item is not None and item.text().strip().upper() == wanted:
                self._truck_list.setCurrentRow(index)
                return

    def refresh_page(self) -> None:
        current = self.current_truck_number()
        self._all_trucks = discover_truck_numbers(self._settings)
        self._apply_filter()
        if current:
            self.set_external_truck_number(current)
        elif self._truck_list.count() > 0:
            self._truck_list.setCurrentRow(0)
        else:
            self._populate_table([])

    def current_truck_number(self) -> str:
        item = self._truck_list.currentItem()
        return item.text().strip() if item is not None else ""

    def _apply_filter(self) -> None:
        wanted = self._search_edit.text().strip().casefold()
        current = self.current_truck_number()
        self._truck_list.clear()
        filtered = [
            truck_number
            for truck_number in self._all_trucks
            if not wanted or wanted in truck_number.casefold()
        ]
        for truck_number in filtered:
            self._truck_list.addItem(QListWidgetItem(truck_number))
        if current:
            self.set_external_truck_number(current)

    def _on_truck_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        truck_number = current.text().strip() if current is not None else ""
        self._current_rows = build_workspace_rows(truck_number, self._settings)
        self._populate_table(self._current_rows)
        self.truckSelected.emit(truck_number)

    def _populate_table(self, rows: list[WorkspaceKitRow]) -> None:
        self._table.setRowCount(len(rows))
        if not rows:
            self._summary_label.setText("No trucks discovered yet. Check the configured roots in Admin.")
            return

        self._summary_label.setText(
            f"{rows[0].truck_number} | {len(rows)} configured kit slots | "
            "Status combines folder discovery, spreadsheet detection, and handoff visibility."
        )
        for row_index, row in enumerate(rows):
            values = (
                row.display_name,
                "Yes" if row.release_kit_dir.exists() else "No",
                row.project_name if row.project_dir.exists() else "-",
                row.rpd_path.name if row.rpd_path.exists() else "-",
                "Yes" if row.fabrication_kit_dir.exists() else "No",
                row.spreadsheet_path.name if row.spreadsheet_path is not None else "-",
                row.import_csv_path.name if row.import_csv_path is not None and row.import_csv_path.exists() else "-",
                row.status_summary,
            )
            for column_index, value in enumerate(values):
                self._table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        self._table.resizeColumnsToContents()

    def _selected_row(self) -> WorkspaceKitRow | None:
        selected = self._table.currentRow()
        if selected < 0 or selected >= len(self._current_rows):
            return None
        return self._current_rows[selected]

    def _open_explorer(self) -> None:
        try:
            launch_tool(self._settings.truck_explorer_launcher, self._settings)
        except Exception as exc:
            QMessageBox.critical(self, "Launch Failed", str(exc))

    def _create_scaffold(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Create Project Scaffold", "Select a kit first.")
            return
        try:
            mode, created = ensure_project_scaffold(row, self._settings)
            message = [f"Scaffold mode: {mode}", f"Created/ensured items: {len(created)}"]
            if created:
                message.extend(str(path) for path in created)
            QMessageBox.information(self, "Create Project Scaffold", "\n".join(message))
            self._current_rows = build_workspace_rows(row.truck_number, self._settings)
            self._populate_table(self._current_rows)
        except Exception as exc:
            QMessageBox.critical(self, "Create Project Scaffold", str(exc))

    def _run_inventor(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Run Inventor + Copy", "Select a kit first.")
            return
        try:
            completed, copied = run_inventor_and_copy(row, self._settings)
            lines = [
                f"Return code: {completed.returncode}",
                "",
                "Stdout:",
                completed.stdout.strip() or "(none)",
                "",
                "Stderr:",
                completed.stderr.strip() or "(none)",
            ]
            if copied:
                lines.extend(["", "Copied to L:"])
                lines.extend(str(path) for path in copied)
            QMessageBox.information(self, "Run Inventor + Copy", "\n".join(lines))
            self._current_rows = build_workspace_rows(row.truck_number, self._settings)
            self._populate_table(self._current_rows)
        except Exception as exc:
            QMessageBox.critical(self, "Run Inventor + Copy", str(exc))

    def _launch_kitter(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Launch RADAN Kitter", "Select a kit first.")
            return
        if not row.rpd_path.exists():
            QMessageBox.warning(self, "Launch RADAN Kitter", "The selected project does not have an RPD yet.")
            return
        try:
            launch_tool(self._settings.radan_kitter_launcher, self._settings, argument_path=row.rpd_path)
        except Exception as exc:
            QMessageBox.critical(self, "Launch RADAN Kitter", str(exc))

    def _open_project_folder(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Open Project Folder", "Select a kit first.")
            return
        try:
            open_path(row.project_dir if row.project_dir.exists() else row.release_kit_dir)
        except Exception as exc:
            QMessageBox.critical(self, "Open Project Folder", str(exc))

    def _open_fabrication_folder(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Open W Folder", "Select a kit first.")
            return
        try:
            open_path(row.fabrication_kit_dir)
        except Exception as exc:
            QMessageBox.critical(self, "Open W Folder", str(exc))

    def _open_nest_summary(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Open Nest Summary", "Select a kit first.")
            return
        if row.nest_summary_pdf_path is None:
            QMessageBox.warning(self, "Open Nest Summary", "No nest summary PDF was detected for this kit.")
            return
        try:
            open_path(row.nest_summary_pdf_path)
        except Exception as exc:
            QMessageBox.critical(self, "Open Nest Summary", str(exc))

