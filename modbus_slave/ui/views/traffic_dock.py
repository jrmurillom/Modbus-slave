"""Panel inferior (Dock) para el Sniffer de Tráfico Hexadecimal en Tiempo Real con límite de memoria y exportación."""

from __future__ import annotations

import csv
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modbus_slave.core.logger import PacketEntry, TrafficLogger


class TrafficDockWidget(QDockWidget):
    """Panel acoplable que muestra las tramas crudas RX/TX, autolimpieza de memoria y exportación CSV."""

    COLUMNS = ["Timestamp", "Dirección", "ID", "Función", "Trama Hex (MBAP + PDU)", "Interpretación"]
    MAX_VISIBLE_ROWS = 1000  # Límite estricto de filas en el widget para evitar fugas de memoria

    def __init__(self, logger: TrafficLogger, parent: Optional[QWidget] = None) -> None:
        super().__init__("📡 Sniffer de Tráfico Modbus TCP (RX / TX Crudo)", parent)
        self.logger = logger
        self._is_paused = False

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Barra de control superior del dock
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_stats = QLabel("Total Tramas: 0 | RX: 0 | TX: 0 | Errores: 0")
        self.lbl_stats.setStyleSheet("font-weight: bold; color: #89dceb;")
        top_bar.addWidget(self.lbl_stats)

        top_bar.addStretch()

        self.chk_autoscroll = QCheckBox("Auto-Scroll")
        self.chk_autoscroll.setChecked(True)
        top_bar.addWidget(self.chk_autoscroll)

        self.btn_pause = QPushButton("Pausar Captura")
        self.btn_pause.clicked.connect(self._toggle_pause)
        top_bar.addWidget(self.btn_pause)

        self.btn_export = QPushButton("Exportar CSV...")
        self.btn_export.setToolTip("Exportar historial de tramas capturadas a un archivo CSV")
        self.btn_export.clicked.connect(self.export_traffic)
        top_bar.addWidget(self.btn_export)

        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.clicked.connect(self.clear_logs)
        top_bar.addWidget(self.btn_clear)

        layout.addLayout(top_bar)

        # Tabla de paquetes
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
        """)

        # Configurar anchos de columna
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Timestamp
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # RX/TX
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # ID
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Función
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)      # Hex
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Detalle

        layout.addWidget(self.table)
        self.setWidget(main_widget)

    def _setup_shortcuts(self) -> None:
        """Configura atajos como Ctrl+C para copiar tramas seleccionadas."""
        shortcut_copy = QShortcut(QKeySequence.StandardKey.Copy, self.table)
        shortcut_copy.activated.connect(self.copy_selection_to_clipboard)

    def copy_selection_to_clipboard(self) -> None:
        """Copia las filas seleccionadas del sniffer al portapapeles del sistema."""
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()))
        if not selected_rows:
            return

        lines = []
        for r in selected_rows:
            row_data = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(self.table.columnCount())]
            lines.append("\t".join(row_data))

        text_to_copy = "\n".join(lines)
        QApplication.clipboard().setText(text_to_copy)

    def _toggle_pause(self) -> None:
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.btn_pause.setText("Reanudar Captura")
            self.btn_pause.setStyleSheet("color: #f38ba8;")
        else:
            self.btn_pause.setText("Pausar Captura")
            self.btn_pause.setStyleSheet("")

    def clear_logs(self) -> None:
        self.table.setRowCount(0)
        self.logger.clear()
        self.update_stats()

    def update_stats(self) -> None:
        total = self.logger.rx_count + self.logger.tx_count
        self.lbl_stats.setText(
            f"Total Tramas: {total} | RX: {self.logger.rx_count} | TX: {self.logger.tx_count} | Errores: {self.logger.error_count}"
        )

    def export_traffic(self) -> None:
        """Exporta el historial de tramas a un archivo CSV."""
        entries = self.logger.get_entries()
        if not entries:
            QMessageBox.information(self, "Exportar Tráfico", "No hay tramas registradas para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Tráfico Modbus",
            "modbus_traffic.csv",
            "Archivos CSV (*.csv);;Archivos de Texto (*.txt)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.COLUMNS)
                for entry in entries:
                    writer.writerow([
                        entry.formatted_time,
                        entry.direction,
                        entry.slave_id,
                        f"FC{entry.func_code:02d}" if entry.func_code else "-",
                        entry.hex_dump,
                        entry.description,
                    ])
            QMessageBox.information(self, "Exportación Exitosa", f"Se exportaron {len(entries)} tramas en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")

    def add_packet(self, entry: PacketEntry) -> None:
        """Inserta una nueva fila en la tabla de tráfico con auto-poda de memoria."""
        if self._is_paused:
            return

        # Auto-poda para mantener el uso de memoria RAM acotado en ejecución continua 24/7
        if self.table.rowCount() >= self.MAX_VISIBLE_ROWS:
            self.table.removeRow(0)

        row = self.table.rowCount()
        self.table.insertRow(row)

        item_time = QTableWidgetItem(entry.formatted_time)
        item_dir = QTableWidgetItem(entry.direction)
        item_id = QTableWidgetItem(str(entry.slave_id))
        item_fc = QTableWidgetItem(f"FC{entry.func_code:02d}" if entry.func_code else "-")
        item_hex = QTableWidgetItem(entry.hex_dump)
        item_desc = QTableWidgetItem(entry.description)

        # Coloreado según dirección
        if entry.direction == "RX":
            item_dir.setForeground(QColor(166, 227, 161)) # Verde
        else:
            item_dir.setForeground(QColor(137, 220, 235)) # Cyan

        if entry.is_exception:
            item_desc.setForeground(QColor(243, 139, 168)) # Rojo

        self.table.setItem(row, 0, item_time)
        self.table.setItem(row, 1, item_dir)
        self.table.setItem(row, 2, item_id)
        self.table.setItem(row, 3, item_fc)
        self.table.setItem(row, 4, item_hex)
        self.table.setItem(row, 5, item_desc)

        if self.chk_autoscroll.isChecked():
            self.table.scrollToBottom()

        self.update_stats()
