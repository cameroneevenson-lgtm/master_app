APP_STYLE = """
QWidget {
    background: #f4f1ea;
    color: #1f2933;
    font-size: 12px;
}
QMainWindow {
    background: #f4f1ea;
}
QFrame#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1f3a4a, stop:1 #2e5165);
    border-radius: 18px;
}
QLabel#brandTitle {
    color: #f8f4ec;
    font-size: 22px;
    font-weight: 800;
}
QLabel#brandSubtitle {
    color: #d8e5ee;
    font-size: 12px;
}
QListWidget#navList {
    background: transparent;
    border: none;
    color: #f3f7fa;
    outline: none;
}
QListWidget#navList::item {
    padding: 12px 14px;
    margin: 4px 0;
    border-radius: 10px;
}
QListWidget#navList::item:selected {
    background: rgba(248, 244, 236, 0.18);
}
QPushButton {
    background: #c46b2d;
    color: #fffdf9;
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 700;
}
QPushButton:hover {
    background: #b25e24;
}
QPushButton:disabled {
    background: #d8c1ad;
    color: #f5ece4;
}
QLineEdit, QPlainTextEdit, QTableWidget, QListWidget, QComboBox {
    background: #fffdf9;
    border: 1px solid #d6cec1;
    border-radius: 10px;
}
QHeaderView::section {
    background: #eadfce;
    color: #3d362d;
    border: none;
    border-right: 1px solid #d6cec1;
    border-bottom: 1px solid #d6cec1;
    padding: 8px;
    font-weight: 700;
}
QGroupBox {
    border: 1px solid #d6cec1;
    border-radius: 14px;
    margin-top: 14px;
    padding-top: 12px;
    background: rgba(255, 253, 249, 0.82);
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #5a4735;
    font-weight: 700;
}
QStatusBar {
    background: #ece3d6;
}
"""

