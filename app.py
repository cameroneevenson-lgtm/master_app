from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from styles import APP_STYLE

APP_DIR = Path(__file__).resolve().parent
HOT_RELOAD_ENV_VARS = ("MASTER_APP_HOT_RELOAD_ACTIVE",)


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
    app = QApplication(sys.argv)
    app.setApplicationName("Master App")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow(
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
