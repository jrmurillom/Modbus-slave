"""Pruebas automatizadas para las mejoras de auditoría y refinamiento comercial."""

import csv
import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLineEdit, QMessageBox

from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.formatters import DataFormat, Endianness
from modbus_slave.core.logger import PacketEntry, TrafficLogger
from modbus_slave.ui.main_window import MainWindow
from modbus_slave.ui.views.register_view import InlineRegisterDelegate
from modbus_slave.ui.views.traffic_dock import TrafficDockWidget


def test_traffic_dock_memory_bounded_buffer(qtbot):
    """Verifica que el sniffer de tráfico acote estrictamente la memoria a MAX_VISIBLE_ROWS."""
    logger = TrafficLogger(max_entries=5000)
    dock = TrafficDockWidget(logger)
    qtbot.addWidget(dock)

    assert dock.MAX_VISIBLE_ROWS == 1000

    # Simular ráfaga de 1250 paquetes entrantes
    for i in range(1250):
        pkt = PacketEntry(
            timestamp=1000.0 + i,
            direction="RX" if i % 2 == 0 else "TX",
            raw_bytes=b"\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x01",
            hex_dump="00 01 00 00 00 06 01 03 00 00 00 01",
            slave_id=1,
            func_code=3,
            description=f"Packet #{i}",
        )
        dock.add_packet(pkt)

    # La tabla debe tener exactamente 1000 filas (las más recientes)
    assert dock.table.rowCount() == 1000
    # La última fila visible debe ser la última ingresada
    assert dock.table.item(999, 5).text() == "Packet #1249"


def test_traffic_dock_export_csv(qtbot, tmp_path, monkeypatch):
    """Verifica que la exportación de tráfico genere un CSV válido con todas las columnas."""
    logger = TrafficLogger()
    dock = TrafficDockWidget(logger)
    qtbot.addWidget(dock)

    pkt1 = logger.log_packet(False, b"\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x02")
    pkt2 = logger.log_packet(True, b"\x00\x01\x00\x00\x00\x07\x01\x03\x04\x00\x0A\x00\x0B")
    dock.add_packet(pkt1)
    dock.add_packet(pkt2)

    export_file = tmp_path / "traffic_test.csv"

    # Mockear diálogo de selección de archivo y QMessageBox
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(export_file), "Archivos CSV (*.csv)"))
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    dock.export_traffic()

    assert export_file.exists()
    with open(export_file, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 3  # Cabecera + 2 filas
        assert reader[0] == dock.COLUMNS
        assert reader[1][1] == "RX"
        assert reader[2][1] == "TX"


def test_traffic_dock_clipboard_copy(qtbot):
    """Verifica que el atajo de copia copie las filas seleccionadas al portapapeles."""
    logger = TrafficLogger()
    dock = TrafficDockWidget(logger)
    qtbot.addWidget(dock)

    pkt = logger.log_packet(False, b"\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x02")
    dock.add_packet(pkt)

    dock.table.selectRow(0)
    dock.copy_selection_to_clipboard()

    clipboard_text = QApplication.clipboard().text()
    assert "RX" in clipboard_text
    assert "FC03" in clipboard_text


def test_inline_delegate_validation(qtbot):
    """Verifica la validación numérica estricta y feedback en el InlineRegisterDelegate."""
    ds = ThreadSafeDataStore(slave_id=1, size=50)
    window = MainWindow(datastore=ds)
    qtbot.addWidget(window)

    delegate = InlineRegisterDelegate()
    idx_val = window.table_model.index(0, 2)  # Columna de valor (Int16)

    editor = delegate.createEditor(window.table_view, None, idx_val)
    assert isinstance(editor, QLineEdit)
    assert editor.validator() is not None

    # Probar valor válido
    editor.setText("12345")
    delegate.setModelData(editor, window.table_model, idx_val)
    assert ds.get_holding_register(0) == 12345

    # Probar valor fuera de rango para Int16 (> 32767)
    editor.setText("99999")
    delegate.setModelData(editor, window.table_model, idx_val)
    # No debe haberse guardado, el valor original permanece intacto
    assert ds.get_holding_register(0) == 12345
    # Comprobar feedback visual de borde de error
    assert "#f38ba8" in editor.styleSheet()


def test_multi_client_tracking_and_tooltip(qtbot):
    """Verifica el rastreo de múltiples clientes y su presentación en el tooltip de la UI."""
    ds = ThreadSafeDataStore(slave_id=1, size=50)
    logger = TrafficLogger()
    window = MainWindow(datastore=ds, logger=logger)
    qtbot.addWidget(window)

    # Conectar 2 clientes
    logger.register_client_connect(("192.168.1.50", 49152))
    logger.register_client_connect(("10.0.0.12", 50211))

    assert logger.connected_clients == 2
    assert "192.168.1.50:49152" in logger.get_connected_clients()
    assert "10.0.0.12:50211" in logger.get_connected_clients()

    window._update_telemetry_header()

    # Comprobar tooltip en statusbar y cabecera
    tip = window.lbl_sb_clients.toolTip()
    assert "192.168.1.50:49152" in tip
    assert "10.0.0.12:50211" in tip

    # Desconectar 1 cliente
    logger.register_client_disconnect(("192.168.1.50", 49152))
    assert logger.connected_clients == 1
    assert logger.get_connected_clients() == ["10.0.0.12:50211"]

    window._update_telemetry_header()
    assert "192.168.1.50:49152" not in window.lbl_sb_clients.toolTip()


def test_go_to_address_navigation(qtbot, monkeypatch):
    """Verifica que el diálogo 'Ir a Dirección' reposicione la vista y seleccione la celda."""
    ds = ThreadSafeDataStore(slave_id=1, size=1000)
    window = MainWindow(datastore=ds)
    qtbot.addWidget(window)

    window.start_address = 0
    window.display_count = 100

    # Simular que el operador escribe la dirección 450 en el diálogo Ctrl+G
    monkeypatch.setattr(QInputDialog, "getInt", lambda *args, **kwargs: (450, True))

    window._go_to_address()

    # Comprobar que start_address se ajustó para contener la dirección 450
    assert window.start_address <= 450 < (window.start_address + window.display_count)
    # Comprobar que la celda actual seleccionada corresponde a la dirección 450
    selected_idx = window.table_view.currentIndex()
    assert selected_idx.isValid()
    row_addr = window.table_model._get_row_address(selected_idx.row())
    assert row_addr == 450
