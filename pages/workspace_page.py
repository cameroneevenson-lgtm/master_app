from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
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
        "Project Folder",
        "Project File",
        "Nest Summary",
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
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        root.addWidget(self._build_left_panel(), 0)
        root.addWidget(self._build_right_panel(), 1)

    def _build_left_panel(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Trucks")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        refresh_button = QPushButton("Refresh")
        refresh_button.setToolTip("Refresh truck discovery from L, W, and the dashboard database.")
        refresh_button.clicked.connect(self.refresh_page)
        open_explorer_button = QPushButton("Open Explorer")
        open_explorer_button.setToolTip("Open the standalone Truck Nest Explorer.")
        open_explorer_button.clicked.connect(self._open_explorer)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh_button)
        header.addWidget(open_explorer_button)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter trucks...")
        self._search_edit.textChanged.connect(self._apply_filter)

        self._truck_list = QListWidget()
        self._truck_list.currentItemChanged.connect(self._on_truck_changed)

        layout.addLayout(header)
        layout.addWidget(self._search_edit)
        layout.addWidget(self._truck_list, 1)
        box.setMinimumWidth(320)
        return box

    def _build_right_panel(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._build_actions_group())
        layout.addWidget(self._build_table_group(), 1)
        return box

    def _build_actions_group(self) -> QWidget:
        group = QGroupBox("Truck / Kit Actions")
        layout = QVBoxLayout(group)

        self._current_truck_label = QLabel("Selected Truck: (none)")
        self._current_truck_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        helper_label = QLabel("Hover a button for details.")
        helper_label.setStyleSheet("color: #6C757D;")

        truck_row = QHBoxLayout()
        create_button = QPushButton("Create Missing")
        create_button.setToolTip("Create or repair the selected kit project folder and RPD scaffold on L.")
        create_button.clicked.connect(self._create_scaffold)
        open_release_button = QPushButton("Open L Kit")
        open_release_button.setToolTip("Open the selected kit folder on L.")
        open_release_button.clicked.connect(self._open_release_folder)
        open_fabrication_button = QPushButton("Open W Kit")
        open_fabrication_button.setToolTip("Open the selected kit source folder on W.")
        open_fabrication_button.clicked.connect(self._open_fabrication_folder)
        truck_row.addWidget(create_button)
        truck_row.addWidget(open_release_button)
        truck_row.addWidget(open_fabrication_button)
        truck_row.addStretch(1)

        kit_row = QHBoxLayout()
        open_project_button = QPushButton("Open Project")
        open_project_button.setToolTip("Open the selected project file on L, or the project folder if the file is missing.")
        open_project_button.clicked.connect(self._open_project)
        open_sheet_button = QPushButton("Open Sheet")
        open_sheet_button.setToolTip("Open the unique spreadsheet detected for the selected kit on W.")
        open_sheet_button.clicked.connect(self._open_spreadsheet)
        open_nest_button = QPushButton("Open Nest Summary")
        open_nest_button.setToolTip("Open the selected kit Nest Summary PDF on L.")
        open_nest_button.clicked.connect(self._open_nest_summary)
        run_kitter_button = QPushButton("Run Kitter")
        run_kitter_button.setToolTip("Launch RADAN Kitter on the selected project file.")
        run_kitter_button.clicked.connect(self._launch_kitter)
        run_inventor_button = QPushButton("Run Inventor Tool")
        run_inventor_button.setToolTip(
            "Run the Inventor-to-RADAN tool on the selected spreadsheet, then copy generated outputs into the L project folder."
        )
        run_inventor_button.clicked.connect(self._run_inventor)
        for button in (
            open_project_button,
            open_sheet_button,
            open_nest_button,
            run_kitter_button,
            run_inventor_button,
        ):
            kit_row.addWidget(button)
        kit_row.addStretch(1)

        layout.addWidget(self._current_truck_label)
        layout.addWidget(helper_label)
        layout.addLayout(truck_row)
        layout.addLayout(kit_row)
        return group

    def _build_table_group(self) -> QWidget:
        group = QGroupBox("Kit Explorer")
        layout = QVBoxLayout(group)

        self._summary_label = QLabel("Select a truck to inspect kit status across L and W.")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color: #6C757D;")

        self._table = QTableWidget(0, len(self.TABLE_COLUMNS))
        self._table.setHorizontalHeaderLabels(self.TABLE_COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        for column in range(len(self.TABLE_COLUMNS) - 1):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(len(self.TABLE_COLUMNS) - 1, QHeaderView.Stretch)

        layout.addWidget(self._summary_label)
        layout.addWidget(self._table, 1)
        return group

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
        for truck_number in self._all_trucks:
            if wanted and wanted not in truck_number.casefold():
                continue
            self._truck_list.addItem(QListWidgetItem(truck_number))
        if current:
            self.set_external_truck_number(current)

    def _on_truck_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        truck_number = current.text().strip() if current is not None else ""
        self._current_rows = build_workspace_rows(truck_number, self._settings)
        self._refresh_current_truck_heading()
        self._populate_table(self._current_rows)
        self.truckSelected.emit(truck_number)

    def _refresh_current_truck_heading(self) -> None:
        truck_number = self.current_truck_number()
        if not truck_number:
            self._current_truck_label.setText("Selected Truck: (none)")
            return
        self._current_truck_label.setText(f"Selected Truck: {truck_number}")

    def _make_item(
        self,
        text: str,
        *,
        background: QColor | None = None,
        foreground: QColor | None = None,
        tooltip: str = "",
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        if background is not None:
            item.setBackground(background)
        if foreground is not None:
            item.setForeground(foreground)
        if tooltip:
            item.setToolTip(tooltip)
        return item

    def _populate_table(self, rows: list[WorkspaceKitRow]) -> None:
        self._table.setRowCount(len(rows))
        if not rows:
            self._summary_label.setText("No trucks discovered yet. Check the configured roots in Admin.")
            return

        self._summary_label.setText(
            f"{rows[0].truck_number} | {len(rows)} configured kit slots | "
            "Explorer-style status view with colored readiness signals."
        )

        green = QColor("#D8F3DC")
        yellow = QColor("#FFF3BF")
        red = QColor("#F8D7DA")

        for row_index, row in enumerate(rows):
            nest_text = "(missing)"
            nest_color = red
            if row.nest_summary_pdf_path is not None:
                nest_text = row.nest_summary_pdf_path.stem
                nest_color = green

            spreadsheet_text = "(missing)"
            spreadsheet_color = red
            if row.spreadsheet_path is not None:
                spreadsheet_text = row.spreadsheet_path.name
                spreadsheet_color = green

            import_text = "(missing)"
            import_color = red
            if row.import_csv_path is not None and row.import_csv_path.exists():
                import_text = row.import_csv_path.name
                import_color = green
            elif row.import_csv_path is not None:
                import_text = row.import_csv_path.name
                import_color = yellow

            items = (
                self._make_item(
                    row.display_name,
                    tooltip=f"RADAN name: {row.kit_name}" if row.display_name.casefold() != row.kit_name.casefold() else "",
                ),
                self._make_item(
                    "Yes" if row.release_kit_dir.exists() else "Missing",
                    background=green if row.release_kit_dir.exists() else red,
                ),
                self._make_item(
                    "Yes" if row.project_dir.exists() else "Missing",
                    background=green if row.project_dir.exists() else red,
                ),
                self._make_item(
                    row.rpd_path.name if row.rpd_path.exists() else "(missing)",
                    background=green if row.rpd_path.exists() else red,
                ),
                self._make_item(nest_text, background=nest_color),
                self._make_item(spreadsheet_text, background=spreadsheet_color),
                self._make_item(import_text, background=import_color),
                self._make_item(row.status_summary),
            )
            for column, item in enumerate(items):
                self._table.setItem(row_index, column, item)
        self._table.resizeRowsToContents()

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
            QMessageBox.information(self, "Create Missing", "Select a kit first.")
            return
        try:
            mode, created = ensure_project_scaffold(row, self._settings)
            lines = [f"Scaffold mode: {mode}", f"Created/ensured items: {len(created)}"]
            if created:
                lines.extend(str(path) for path in created)
            QMessageBox.information(self, "Create Missing", "\n".join(lines))
            self._current_rows = build_workspace_rows(row.truck_number, self._settings)
            self._populate_table(self._current_rows)
        except Exception as exc:
            QMessageBox.critical(self, "Create Missing", str(exc))

    def _open_project(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Open Project", "Select a kit first.")
            return
        try:
            open_path(row.rpd_path if row.rpd_path.exists() else row.project_dir)
        except Exception as exc:
            QMessageBox.critical(self, "Open Project", str(exc))

    def _open_release_folder(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Open L Kit", "Select a kit first.")
            return
        try:
            open_path(row.release_kit_dir)
        except Exception as exc:
            QMessageBox.critical(self, "Open L Kit", str(exc))

    def _open_fabrication_folder(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Open W Kit", "Select a kit first.")
            return
        try:
            open_path(row.fabrication_kit_dir)
        except Exception as exc:
            QMessageBox.critical(self, "Open W Kit", str(exc))

    def _open_spreadsheet(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Open Sheet", "Select a kit first.")
            return
        if row.spreadsheet_path is None:
            QMessageBox.warning(self, "Open Sheet", "No unique spreadsheet was detected for this kit.")
            return
        try:
            open_path(row.spreadsheet_path)
        except Exception as exc:
            QMessageBox.critical(self, "Open Sheet", str(exc))

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

    def _launch_kitter(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Run Kitter", "Select a kit first.")
            return
        if not row.rpd_path.exists():
            QMessageBox.warning(self, "Run Kitter", "The selected project does not have an RPD yet.")
            return
        try:
            launch_tool(self._settings.radan_kitter_launcher, self._settings, argument_path=row.rpd_path)
        except Exception as exc:
            QMessageBox.critical(self, "Run Kitter", str(exc))

    def _run_inventor(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Run Inventor Tool", "Select a kit first.")
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
            QMessageBox.information(self, "Run Inventor Tool", "\n".join(lines))
            self._current_rows = build_workspace_rows(row.truck_number, self._settings)
            self._populate_table(self._current_rows)
        except Exception as exc:
            QMessageBox.critical(self, "Run Inventor Tool", str(exc))
