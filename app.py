from __future__ import annotations

import ctypes
import importlib
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

APP_DIR = Path(__file__).resolve().parent
TOOLS_DIR = APP_DIR.parent
EXPLORER_DIR = TOOLS_DIR / "truck_nest_explorer"
EXPLORER_MAIN_WINDOW_PATH = EXPLORER_DIR / "main_window.py"
HOT_RELOAD_ENV_VARS = ("MASTER_APP_HOT_RELOAD_ACTIVE", "TNE_HOT_RELOAD_ACTIVE")
EXPLORER_TOP_LEVEL_MODULES = (
    "main_window",
    "models",
    "services",
    "settings_store",
    "flow_bridge",
    "pdf_preview",
)


def _load_explorer_main_window():
    if not EXPLORER_MAIN_WINDOW_PATH.exists():
        raise FileNotFoundError(f"Truck Nest Explorer window not found: {EXPLORER_MAIN_WINDOW_PATH}")

    explorer_root = str(EXPLORER_DIR)
    if explorer_root not in sys.path:
        sys.path.insert(0, explorer_root)

    expected_path = EXPLORER_MAIN_WINDOW_PATH.resolve()
    cached_module = sys.modules.get("main_window")
    if cached_module is not None:
        cached_path = Path(getattr(cached_module, "__file__", "")).resolve()
        if cached_path != expected_path:
            for module_name in EXPLORER_TOP_LEVEL_MODULES:
                sys.modules.pop(module_name, None)

    importlib.invalidate_caches()
    explorer_main_window = importlib.import_module("main_window")
    return explorer_main_window.MainWindow


def _target_screen():
    screens = QGuiApplication.screens()
    if len(screens) >= 2:
        return screens[1]
    return QGuiApplication.primaryScreen()


def _lock_to_screen_maximized(window, screen) -> None:
    if screen is None:
        window.showMaximized()
        return
    try:
        geometry = screen.availableGeometry()
        window.setMinimumSize(geometry.size())
        window.setMaximumSize(geometry.size())
        window.move(geometry.topLeft())
    except Exception:
        pass
    window.showMaximized()


def _place_maximized_on_screen2(window) -> None:
    screen = _target_screen()
    if screen is None:
        _lock_to_screen_maximized(window, QGuiApplication.primaryScreen())
        return

    handle = window.windowHandle()
    if handle is not None:
        try:
            handle.setScreen(screen)
        except Exception:
            pass
    try:
        window.move(screen.geometry().topLeft())
    except Exception:
        pass
    _lock_to_screen_maximized(window, screen)


def _bring_window_to_front(window) -> None:
    window.raise_()
    window.activateWindow()
    try:
        hwnd = int(window.winId())
        if hwnd:
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _hot_reload_active() -> bool:
    return any(os.environ.get(name) == "1" for name in HOT_RELOAD_ENV_VARS)


def main() -> int:
    explorer_main_window = _load_explorer_main_window()

    app = QApplication(sys.argv)
    app.setApplicationName("Master App")

    window = explorer_main_window(
        hot_reload_active=_hot_reload_active(),
        runtime_dir=APP_DIR,
    )
    window.show()
    _place_maximized_on_screen2(window)
    _bring_window_to_front(window)
    QTimer.singleShot(120, lambda: _bring_window_to_front(window))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
