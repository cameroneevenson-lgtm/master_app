from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from styles import APP_STYLE


def _place_window_on_second_screen(app: QApplication, window: MainWindow) -> None:
    screens = app.screens()
    if not screens:
        return
    target = screens[1] if len(screens) > 1 else screens[0]
    handle = window.windowHandle()
    if handle is not None:
        try:
            handle.setScreen(target)
        except Exception:
            pass
    geometry = target.availableGeometry()
    window.resize(min(1800, geometry.width()), min(1040, geometry.height()))
    window.move(geometry.topLeft())


def _bring_to_front(window: MainWindow) -> None:
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


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Master App")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    _place_window_on_second_screen(app, window)
    _bring_to_front(window)
    QTimer.singleShot(120, lambda: _bring_to_front(window))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

