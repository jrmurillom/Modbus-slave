"""Pruebas automatizadas de la interfaz gráfica (PySide6) con pytest-qt."""

import pytest
from PySide6.QtCore import Qt

from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.formatters import DataFormat, Endianness
from modbus_slave.core.logger import PacketEntry, TrafficLogger
from modbus_slave.ui.main_window import MainWindow


def test_main_window_initialization(qtbot):
    ds = ThreadSafeDataStore(slave_id=1, size=100)
    logger = TrafficLogger()
    window = MainWindow(datastore=ds, logger=logger)
    qtbot.addWidget(window)

    # 1. Verificar cabecera inicial de telemetría (estilo Modbus Slave)
    assert "Rx = 0" in window.lbl_telemetry_header.text()
    assert "ID = 1" in window.lbl_telemetry_header.text()
    assert "F = 03" in window.lbl_telemetry_header.text()

    # 2. Verificar dimensiones de la tabla
    assert window.table_model.rowCount() == 100
    assert window.table_model.columnCount() == 6

    # 3. Verificar que las direcciones inician en 0 (Base 0 Protocol Address)
    assert window.table_model.data(window.table_model.index(0, 0)) == "0"
    assert window.table_model.data(window.table_model.index(1, 0)) == "1"

    # 4. Alternar a Direcciones PLC (Base 1) y comprobar 40001
    window._toggle_plc_addresses(True)
    assert window.table_model.data(window.table_model.index(0, 0)) == "40001"

    # Regresar a Base 0
    window._toggle_plc_addresses(False)
    assert window.table_model.data(window.table_model.index(0, 0)) == "0"


def test_table_inline_editing(qtbot):
    ds = ThreadSafeDataStore(slave_id=1, size=50)
    window = MainWindow(datastore=ds)
    qtbot.addWidget(window)

    # Editar celda de valor en fila 0 (Dirección 0)
    idx_val = window.table_model.index(0, 2)
    assert window.table_model.data(idx_val) == "0"

    # Simular edición in-line del operador
    success = window.table_model.setData(idx_val, "4321", Qt.ItemDataRole.EditRole)
    assert success is True
    # Comprobar que el valor se guardó en el DataStore
    assert ds.get_holding_register(0) == 4321
    # Comprobar que la tabla muestra el nuevo valor
    assert window.table_model.data(idx_val) == "4321"

    # Editar Alias en fila 0 (Columna 1)
    idx_alias = window.table_model.index(0, 1)
    window.table_model.setData(idx_alias, "Motor_Speed", Qt.ItemDataRole.EditRole)
    assert ds.get_alias(ModbusBlockType.HOLDING_REGISTERS.value, 0) == "Motor_Speed"
    assert window.table_model.data(idx_alias) == "Motor_Speed"


def test_rx_counter_and_reset(qtbot):
    ds = ThreadSafeDataStore(slave_id=1, size=50)
    logger = TrafficLogger()
    window = MainWindow(datastore=ds, logger=logger)
    qtbot.addWidget(window)

    # Simular llegada de trama RX desde un PLC maestro
    dummy_entry = PacketEntry(
        timestamp=1234567.0,
        direction="RX",
        raw_bytes=b"\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x02",
        hex_dump="00 01 00 00 00 06 01 03 00 00 00 02",
        slave_id=1,
        func_code=3,
        description="FC03 Read 2 registers",
    )
    logger.rx_count = 15
    window._on_packet_logged(dummy_entry)

    assert "Rx = 15" in window.lbl_telemetry_header.text()
    assert window.traffic_dock.table.rowCount() == 1

    # Presionar botón Reset Rx
    qtbot.mouseClick(window.btn_reset_rx, Qt.MouseButton.LeftButton)
    assert "Rx = 0" in window.lbl_telemetry_header.text()
    assert logger.rx_count == 0


def test_format_switching_float32(qtbot):
    ds = ThreadSafeDataStore(slave_id=1, size=50)
    # Escribir float 1234.56 en CDAB (direcciones 0 y 1)
    from modbus_slave.core.formatters import encode_value
    regs = encode_value(1234.56, DataFormat.FLOAT32, Endianness.CDAB)
    ds.set_holding_registers(0, regs)

    window = MainWindow(datastore=ds)
    qtbot.addWidget(window)

    # Cambiar formato a Float32 CDAB
    window._change_format(DataFormat.FLOAT32, Endianness.CDAB)
    idx_val = window.table_model.index(0, 2)
    assert window.table_model.data(idx_val) == "1234.56"


def test_shortcuts_dialog(qtbot):
    from modbus_slave.ui.dialogs.shortcuts_dialog import KeyboardShortcutsDialog
    dlg = KeyboardShortcutsDialog()
    qtbot.addWidget(dlg)

    assert dlg.table.columnCount() == 3
    assert dlg.table.rowCount() == len(KeyboardShortcutsDialog.SHORTCUTS)
    assert dlg.table.item(0, 1).text() == "F5"

    keys = [dlg.table.item(r, 1).text() for r in range(dlg.table.rowCount())]
    assert "Ctrl + G" in keys
    assert "F1" in keys
    assert "F8" in keys
