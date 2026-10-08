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
    assert "Ctrl + Shift + R" in keys


def test_ui_reset_values_without_clients(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    ds = ThreadSafeDataStore(slave_id=1, size=50)
    ds.set_holding_registers(0, [777, 888, 999])
    logger = TrafficLogger()
    window = MainWindow(datastore=ds, logger=logger)
    qtbot.addWidget(window)

    idx_val0 = window.table_model.index(0, 2)
    assert window.table_model.data(idx_val0) == "777"

    # Caso 1: Operador cancela el diálogo -> No se debe alterar nada
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)
    window._confirm_and_reset_values(all_blocks=False)
    assert ds.get_holding_register(0) == 777
    assert window.table_model.data(idx_val0) == "777"

    # Caso 2: Operador confirma (Yes) -> Se resetea el bloque actual a cero
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    qtbot.mouseClick(window.btn_reset_values, Qt.MouseButton.LeftButton)

    assert ds.get_holding_register(0) == 0
    assert ds.get_holding_register(1) == 0
    assert window.table_model.data(idx_val0) == "0"

    # Verificar que el evento de auditoría SYS fue inyectado en el Sniffer
    sys_entries = [e for e in logger.get_entries() if e.direction == "SYS"]
    assert len(sys_entries) == 1
    assert "Reset Values" in sys_entries[0].description


def test_ui_reset_values_with_active_clients_warning(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    ds = ThreadSafeDataStore(slave_id=1, size=50)
    ds.set_holding_registers(0, [123, 456])
    ds.set_coils(0, [True, True])
    logger = TrafficLogger()
    logger.register_client_connect("192.168.1.50:50201")
    assert logger.connected_clients == 1

    window = MainWindow(datastore=ds, logger=logger)
    qtbot.addWidget(window)

    warning_called = []

    def mock_warning(parent, title, text, buttons, default):
        warning_called.append((title, text))
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "warning", mock_warning)

    # Restablecer TODOS los bloques en caliente con clientes conectados
    window._confirm_and_reset_values(all_blocks=True)

    # Debe haberse invocado el diálogo de WARNING específico
    assert len(warning_called) == 1
    assert "1 cliente(s) Modbus TCP conectado(s)" in warning_called[0][1]

    # Todos los bloques deben haberse puesto a 0
    assert ds.get_holding_register(0) == 0
    assert ds.get_coil(0) is False

    # Debe haberse registrado en la auditoría del sniffer
    sys_entries = [e for e in logger.get_entries() if e.direction == "SYS"]
    assert len(sys_entries) >= 1
    assert "TODOS los bloques" in sys_entries[-1].description


def test_rx_visual_increment_via_logger_packets(qtbot):
    """Prueba de regresión: garantiza que logger.log_packet() incrementa visualmente la cabecera Rx en la GUI."""
    ds = ThreadSafeDataStore(slave_id=1, size=50)
    logger = TrafficLogger()
    window = MainWindow(datastore=ds, logger=logger)
    qtbot.addWidget(window)

    # Estado inicial: Rx = 0
    assert "Rx = 0" in window.lbl_telemetry_header.text()
    assert window.traffic_dock.table.rowCount() == 0

    # Simular llegada de trama Modbus real mediante logger.log_packet (RX)
    raw_packet = b"\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x02"
    logger.log_packet(is_tx=False, raw_data=raw_packet)

    # Procesar eventos de Qt para que las señales del bridge se despachen
    qtbot.wait(50)

    # El contador visual en el encabezado DEBE mostrar Rx = 1
    assert "Rx = 1" in window.lbl_telemetry_header.text()
    # El Sniffer de tráfico DEBE tener la fila añadida en tiempo real
    assert window.traffic_dock.table.rowCount() == 1
    assert window.traffic_dock.table.item(0, 1).text() == "RX"

    # Simular una segunda trama RX
    logger.log_packet(is_tx=False, raw_data=raw_packet)
    qtbot.wait(50)

    assert "Rx = 2" in window.lbl_telemetry_header.text()
    assert window.traffic_dock.table.rowCount() == 2


