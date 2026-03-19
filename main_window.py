from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models import MasterSettings
from pages.admin_page import AdminPage
from pages.dashboard_page import DashboardPage
from pages.home_page import HomePage
from pages.workspace_page import WorkspacePage
from settings_store import load_settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Master App")
        self.resize(1640, 980)
        self._settings = load_settings()
        self._build_ui()
        self._apply_settings(self._settings, announce=False)

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(10)

        title = QLabel("Ops Suite")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Master shell scaffold")
        subtitle.setObjectName("brandSubtitle")
        subtitle.setWordWrap(True)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setSpacing(2)
        for label in ("Home", "Truck Workspace", "Dashboard", "Admin"):
            self.nav_list.addItem(QListWidgetItem(label))
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(12)
        sidebar_layout.addWidget(self.nav_list, 1)
        sidebar_layout.addWidget(QLabel("Phase 1 shell: shared context, adapters, diagnostics."))
        root.addWidget(sidebar, 0)

        self.stack = QStackedWidget()
        self.home_page = HomePage(self._settings)
        self.workspace_page = WorkspacePage(self._settings)
        self.dashboard_page = DashboardPage(self._settings)
        self.admin_page = AdminPage(self._settings)

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.workspace_page)
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.admin_page)
        root.addWidget(self.stack, 1)

        self.workspace_page.truckSelected.connect(self.dashboard_page.set_external_truck_number)
        self.admin_page.settingsSaved.connect(self._apply_settings)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready", 3000)
        self.nav_list.setCurrentRow(0)

    def _on_nav_changed(self, index: int) -> None:
        if index < 0:
            return
        self.stack.setCurrentIndex(index)

    def _apply_settings(self, settings: MasterSettings, announce: bool = True) -> None:
        self._settings = settings
        self.home_page.set_settings(settings)
        self.workspace_page.set_settings(settings)
        self.dashboard_page.set_settings(settings)
        self.admin_page.set_settings(settings)
        if announce:
            self.statusBar().showMessage("Settings updated", 4000)

