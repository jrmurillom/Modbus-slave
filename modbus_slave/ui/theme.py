"""Tema visual industrial oscuro y estilos QSS para PySide6."""

from __future__ import annotations

# Paleta de colores Catppuccin Mocha / Industrial Slate
DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #11111b;
    color: #cdd6f4;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}

QWidget {
    color: #cdd6f4;
    font-size: 12px;
}

/* ToolBar */
QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    padding: 4px;
    spacing: 8px;
}

QToolButton {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 5px 10px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #313244;
    border-color: #45475a;
}

QToolButton:pressed {
    background-color: #45475a;
}

/* Tablas */
QTableView {
    background-color: #181825;
    alternate-background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    gridline-color: #272838;
    selection-background-color: #313244;
    selection-color: #89dceb;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

QTableView::item {
    padding: 4px 6px;
    border: none;
}

QTableView::item:selected {
    background-color: #313244;
    color: #89dceb;
}

QHeaderView::section {
    background-color: #11111b;
    color: #a6adc8;
    font-weight: bold;
    padding: 5px;
    border: 1px solid #313244;
    font-size: 11px;
}

/* Entradas y combos */
QLineEdit, QSpinBox, QComboBox {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #06b6d4;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #89dceb;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    selection-background-color: #313244;
}

/* Botones */
QPushButton {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #313244;
    border-color: #89dceb;
}

QPushButton:pressed {
    background-color: #45475a;
}

/* Status Bar */
QStatusBar {
    background-color: #11111b;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 11px;
}

QStatusBar QLabel {
    color: #a6adc8;
    padding: 0 4px;
}

/* Dock Widgets */
QDockWidget {
    color: #cdd6f4;
    font-weight: bold;
    titlebar-close-icon: url(close.png);
}

QDockWidget::title {
    background-color: #181825;
    border: 1px solid #313244;
    padding: 6px;
    font-size: 11px;
    font-weight: 600;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #11111b;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #313244;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #45475a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #11111b;
    height: 10px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #313244;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #45475a;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""
