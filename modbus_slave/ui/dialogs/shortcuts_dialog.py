"""Diálogo informativo de atajos de teclado y comandos rápidos."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class KeyboardShortcutsDialog(QDialog):
    """Muestra una referencia rápida e interactiva de todos los atajos de teclado."""

    SHORTCUTS = [
        ("Servidor", "F5", "Iniciar servidor Modbus TCP"),
        ("Servidor", "F6", "Detener servidor Modbus TCP"),
        ("Servidor", "F8", "Definición de Esclavo (Slave Definition)"),
        ("Navegación", "Ctrl + G", "Ir directamente a una dirección de registro"),
        ("Navegación", "Flechas ↑ ↓ ← →", "Moverse entre celdas y registros"),
        ("Edición", "Enter / F2", "Editar in-line el valor o alias de la celda"),
        ("Edición", "Espacio (Space)", "Alternar estado binario (0 / 1) en Coils y Discrete Inputs"),
        ("Sniffer", "Ctrl + C", "Copiar tramas seleccionadas al portapapeles"),
        ("Proyecto", "Ctrl + N", "Crear nuevo proyecto"),
        ("Proyecto", "Ctrl + O", "Abrir proyecto existente (.json)"),
        ("Proyecto", "Ctrl + S", "Guardar proyecto actual"),
        ("General", "F1", "Abrir esta ventana de atajos"),
        ("General", "Alt + F4", "Cerrar la aplicación"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Atajos de Teclado y Comandos Rápidos")
        self.resize(580, 430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Categoría", "Atajo / Tecla", "Descripción"])
        self.table.setRowCount(len(self.SHORTCUTS))
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        font_shortcut = QFont("Consolas", 10)
        font_shortcut.setBold(True)

        for row, (category, key, desc) in enumerate(self.SHORTCUTS):
            item_cat = QTableWidgetItem(category)
            item_cat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_cat.setForeground(QColor(166, 173, 200))

            item_key = QTableWidgetItem(key)
            item_key.setFont(font_shortcut)
            item_key.setForeground(QColor(137, 220, 235))
            item_key.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_desc = QTableWidgetItem(desc)
            item_desc.setForeground(QColor(205, 214, 244))

            self.table.setItem(row, 0, item_cat)
            self.table.setItem(row, 1, item_key)
            self.table.setItem(row, 2, item_desc)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)
