from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
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
    def __init__(
        self,
        hot_reload_active: bool = False,
        *,
        runtime_dir: Path | None = None,
    ):
        super().__init__()
        self.setWindowTitle("Master App")
        self.resize(1640, 980)
        self._settings = load_settings()
        self._runtime_dir = runtime_dir if runtime_dir is not None else Path(__file__).resolve().parent
        self._hot_reload_enabled = hot_reload_active
        self._hot_reload_request_id = ""
        self._hot_reload_canceled_request_id = ""
        self._hot_reload_request_path: Path | None = None
        self._hot_reload_response_path: Path | None = None
        self._hot_reload_end_time: float | None = None
        self._hot_reload_bar: QFrame | None = None
        self._hot_reload_label: QLabel | None = None
        self._hot_reload_timer_id: int | None = None
        self._build_ui()
        self._apply_settings(self._settings, announce=False)

    def _build_ui(self) -> None:
        central = QWidget()
        shell = QVBoxLayout(central)
        shell.setContentsMargins(12, 12, 12, 12)
        shell.setSpacing(10)

        if self._hot_reload_enabled:
            self._hot_reload_request_path = self._runtime_dir / "_runtime" / "hot_reload_request.json"
            self._hot_reload_response_path = self._runtime_dir / "_runtime" / "hot_reload_response.json"
            self._hot_reload_bar = self._build_hot_reload_bar()
            shell.addWidget(self._hot_reload_bar)
            self._hot_reload_timer_id = self.startTimer(800)
            self._poll_hot_reload_request()

        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(10)

        title = QLabel("Ops Suite")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Explorer workflow plus fab-flow pulse, shared settings, and launchers.")
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
        sidebar_layout.addWidget(QLabel("Master view: pulse first, then drill into explorer-style work."))
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

        shell.addLayout(root, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready", 3000)
        self.nav_list.setCurrentRow(0)

    def _build_hot_reload_bar(self) -> QFrame:
        bar = QFrame()
        bar.setVisible(False)
        bar.setFixedHeight(40)
        bar.setStyleSheet(
            "QFrame { background: #fff4cf; border: 1px solid #d7be6f; border-radius: 6px; }"
            "QLabel { color: #4f3f07; background: transparent; border: none; }"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        self._hot_reload_label = QLabel("Hot reload requested.")
        self._hot_reload_label.setStyleSheet("font-size: 13px; font-weight: 700;")
        accept_button = QPushButton("Accept Reload")
        accept_button.clicked.connect(self._accept_hot_reload_from_banner)
        cancel_button = QPushButton("Cancel Reload")
        cancel_button.clicked.connect(self._cancel_hot_reload_from_banner)

        layout.addWidget(self._hot_reload_label)
        layout.addStretch(1)
        layout.addWidget(accept_button)
        layout.addWidget(cancel_button)
        return bar

    def timerEvent(self, event):  # type: ignore[override]
        if self._hot_reload_timer_id is not None and event.timerId() == self._hot_reload_timer_id:
            self._poll_hot_reload_request()
            return
        super().timerEvent(event)

    def _on_nav_changed(self, index: int) -> None:
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        current_widget = self.stack.currentWidget()
        refresh = getattr(current_widget, "refresh_page", None)
        if callable(refresh):
            refresh()

    def _apply_settings(self, settings: MasterSettings, announce: bool = True) -> None:
        self._settings = settings
        self.home_page.set_settings(settings)
        self.workspace_page.set_settings(settings)
        self.dashboard_page.set_settings(settings)
        self.admin_page.set_settings(settings)
        if announce:
            self.statusBar().showMessage("Settings updated", 4000)

    def _poll_hot_reload_request(self) -> None:
        if not self._hot_reload_enabled or self._hot_reload_request_path is None:
            return

        if not self._hot_reload_request_path.exists():
            if self._hot_reload_request_id:
                self._hot_reload_request_id = ""
                self._hot_reload_canceled_request_id = ""
                self._hot_reload_end_time = None
                self._clear_hot_reload_banner()
            return

        request = self._read_hot_reload_request()
        request_id = str(request.get("request_id", "")).strip()
        if not request_id or request_id == self._hot_reload_canceled_request_id:
            return

        if request_id != self._hot_reload_request_id:
            self._hot_reload_request_id = request_id
            self._hot_reload_canceled_request_id = ""
            try:
                started = float(request.get("ts_epoch", time.time()))
            except (TypeError, ValueError):
                started = float(time.time())
            try:
                timeout_sec = max(1.0, float(request.get("decision_timeout_sec", 10.0)))
            except (TypeError, ValueError):
                timeout_sec = 10.0
            self._hot_reload_end_time = started + timeout_sec

        if self._hot_reload_label is None:
            return

        now = float(time.time())
        end_time = self._hot_reload_end_time or (now + 10.0)
        seconds_remaining = max(0, int(end_time - now))
        file_count = request.get("change_count", None)
        files = request.get("files", [])
        file_text = f"{int(file_count)} file(s)" if isinstance(file_count, int) else "update(s)"

        message = (
            f"Hot reload requested ({file_text}). Auto-reload in {seconds_remaining}s unless canceled. "
            "Click Accept Reload to apply now."
        )
        if isinstance(files, list) and files:
            sample = ", ".join(str(item) for item in files[:3])
            if len(files) > 3:
                sample += ", ..."
            message += f" Sample: {sample}"
        self._hot_reload_label.setText(message)
        if self._hot_reload_bar is not None:
            self._hot_reload_bar.setVisible(True)

    def _read_hot_reload_request(self) -> dict[str, str | int | float | list[str]]:
        if self._hot_reload_request_path is None or not self._hot_reload_request_path.exists():
            return {}
        try:
            payload = json.loads(self._hot_reload_request_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        out: dict[str, str | int | float | list[str]] = {}
        for key in ("request_id", "ts_epoch", "decision_timeout_sec", "change_count", "files"):
            if key in payload:
                out[key] = payload[key]  # type: ignore[assignment]
        return out

    def _clear_hot_reload_banner(self) -> None:
        if self._hot_reload_bar is not None:
            self._hot_reload_bar.setVisible(False)

    def _accept_hot_reload_from_banner(self) -> None:
        if not self._hot_reload_request_id:
            return
        self._write_hot_reload_response("accept")
        self._clear_hot_reload_banner()
        self.statusBar().showMessage("Hot reload accepted; restarting app.", 3000)

    def _cancel_hot_reload_from_banner(self) -> None:
        if not self._hot_reload_request_id:
            return
        self._write_hot_reload_response("reject")
        self._hot_reload_canceled_request_id = self._hot_reload_request_id
        self._clear_hot_reload_banner()
        self.statusBar().showMessage("Hot reload canceled for this change batch.", 3000)

    def _write_hot_reload_response(self, action: str) -> None:
        if self._hot_reload_response_path is None or not self._hot_reload_request_id:
            return
        payload = {
            "request_id": self._hot_reload_request_id,
            "action": str(action or "").strip().lower(),
        }
        try:
            self._hot_reload_response_path.parent.mkdir(parents=True, exist_ok=True)
            self._hot_reload_response_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            return
