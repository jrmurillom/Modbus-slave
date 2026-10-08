"""Modelo de tabla de alto rendimiento (QAbstractTableModel) para registros Modbus.

Soporta:
- Edición In-Line nativa en celdas.
- Visualización multiformato (Int16, UInt16, Hex, Bin, Float32 CDAB/ABCD/etc.).
- Resaltado visual reactivo (Glow Flash) cuando un maestro remoto escribe en un registro.
- Navegación ágil por teclado.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, QTimer
from PySide6.QtGui import QBrush, QColor

from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.formatters import (
    DataFormat,
    Endianness,
    decode_registers,
    encode_value,
    format_to_display_string,
    get_register_span,
)


class RegisterTableModel(QAbstractTableModel):
    """Modelo virtualizado de registros para QTableView."""

    COLUMNS = ["Dirección", "Tag / Alias", "Valor", "Hexadecimal", "Binario", "Simulación"]

    def __init__(
        self,
        datastore: ThreadSafeDataStore,
        parent: Optional[QObject] = None,
        block: str = ModbusBlockType.HOLDING_REGISTERS.value,
        start_address: int = 0,
        display_count: int = 100,
        format_type: DataFormat = DataFormat.INT16,
        endianness: Endianness = Endianness.CDAB,
        use_plc_addresses: bool = False,
    ) -> None:
        super().__init__(parent)
        self.datastore = datastore
        self.block = block
        self.start_address = start_address
        self.display_count = display_count
        self.format_type = format_type
        self.endianness = endianness
        self.use_plc_addresses = use_plc_addresses

        # Registro de direcciones recientemente modificadas por un maestro remoto para efecto flash
        # {address: timestamp}
        self._recently_modified: Dict[int, float] = {}

        # Timer para limpiar los flashes visuales después de 1 segundo
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(250)
        self._flash_timer.timeout.connect(self._check_flash_expiration)
        self._flash_timer.start()

    def set_view_parameters(
        self,
        block: Optional[str] = None,
        start_address: Optional[int] = None,
        display_count: Optional[int] = None,
        format_type: Optional[DataFormat] = None,
        endianness: Optional[Endianness] = None,
        use_plc_addresses: Optional[bool] = None,
    ) -> None:
        """Actualiza los parámetros de visualización de la tabla."""
        self.beginResetModel()
        if block is not None:
            self.block = block
        if start_address is not None:
            self.start_address = max(0, start_address)
        if display_count is not None:
            self.display_count = max(1, min(display_count, self.datastore.size - self.start_address))
        if format_type is not None:
            self.format_type = format_type
        if endianness is not None:
            self.endianness = endianness
        if use_plc_addresses is not None:
            self.use_plc_addresses = use_plc_addresses
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        span = get_register_span(self.format_type)
        return self.display_count // span

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def _get_row_address(self, row: int) -> int:
        span = get_register_span(self.format_type)
        return self.start_address + (row * span)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        addr = self._get_row_address(row)
        span = get_register_span(self.format_type)

        # Resaltado reactivo (Glow Flash) si un maestro escribió recientemente
        if role == Qt.ItemDataRole.BackgroundRole:
            if addr in self._recently_modified:
                # Color verde esmeralda translúcido
                return QBrush(QColor(34, 197, 94, 100))
            if row % 2 == 1:
                # Alternancia sutil de filas
                return QBrush(QColor(30, 30, 46))
            return QBrush(QColor(24, 24, 37))

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 0:
                return QBrush(QColor(137, 220, 235))  # Cyan para dirección
            elif col == 2:
                return QBrush(QColor(166, 227, 161))  # Verde para valor editable
            elif col in (3, 4):
                return QBrush(QColor(166, 173, 200))  # Slate para hex/bin
            return QBrush(QColor(205, 214, 244))

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 5):
                return Qt.AlignmentFlag.AlignCenter
            elif col in (2, 3, 4):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        # Datos de texto para visualización y edición
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                if self.use_plc_addresses:
                    # Nomenclatura Clásica Modicon PLC (Base 1: 40001, 30001, 10001, 00001)
                    prefix = "4"
                    if self.block == ModbusBlockType.INPUT_REGISTERS.value:
                        prefix = "3"
                    elif self.block == ModbusBlockType.DISCRETE_INPUTS.value:
                        prefix = "1"
                    elif self.block == ModbusBlockType.COILS.value:
                        prefix = "0"
                    return f"{prefix}{addr + 1:04d}"
                else:
                    # Protocol Address (Base 0: 0, 1, 2, 3...) idéntico a Modbus Slave
                    return str(addr)

            elif col == 1:
                return self.datastore.get_alias(self.block, addr)

            elif col == 2:
                # Valor decodificado
                if self.block in (ModbusBlockType.COILS.value, ModbusBlockType.DISCRETE_INPUTS.value):
                    val = self.datastore.get_coil(addr) if self.block == ModbusBlockType.COILS.value else self.datastore.get_discrete_input(addr)
                    return "1" if val else "0"
                else:
                    regs = (
                        self.datastore.get_holding_registers(addr, span)
                        if self.block == ModbusBlockType.HOLDING_REGISTERS.value
                        else self.datastore.get_input_registers(addr, span)
                    )
                    decoded = decode_registers(regs, self.format_type, self.endianness)
                    if role == Qt.ItemDataRole.EditRole:
                        return str(decoded)
                    return format_to_display_string(decoded, self.format_type)

            elif col == 3:
                # Hex
                if self.block in (ModbusBlockType.COILS.value, ModbusBlockType.DISCRETE_INPUTS.value):
                    val = self.datastore.get_coil(addr) if self.block == ModbusBlockType.COILS.value else self.datastore.get_discrete_input(addr)
                    return "0x01" if val else "0x00"
                regs = (
                    self.datastore.get_holding_registers(addr, 1)
                    if self.block == ModbusBlockType.HOLDING_REGISTERS.value
                    else self.datastore.get_input_registers(addr, 1)
                )
                return f"0x{regs[0]:04X}"

            elif col == 4:
                # Binario
                if self.block in (ModbusBlockType.COILS.value, ModbusBlockType.DISCRETE_INPUTS.value):
                    val = self.datastore.get_coil(addr) if self.block == ModbusBlockType.COILS.value else self.datastore.get_discrete_input(addr)
                    return "1" if val else "0"
                regs = (
                    self.datastore.get_holding_registers(addr, 1)
                    if self.block == ModbusBlockType.HOLDING_REGISTERS.value
                    else self.datastore.get_input_registers(addr, 1)
                )
                b = f"{regs[0]:016b}"
                return f"{b[:8]} {b[8:]}"

            elif col == 5:
                meta = self.datastore.get_metadata(self.block, addr)
                if meta.simulation_config:
                    return meta.simulation_config.get("waveform", "Activa")
                return "-"

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        col = index.column()

        # Columna 1 (Alias) y Columna 2 (Valor) son editables in-line
        if col in (1, 2):
            base_flags |= Qt.ItemFlag.ItemIsEditable

        return base_flags

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()
        addr = self._get_row_address(row)
        span = get_register_span(self.format_type)

        if col == 1:
            # Edición de Alias / Tag
            self.datastore.set_alias(self.block, addr, str(value).strip())
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            return True

        if col == 2:
            # Edición In-Line del Valor
            try:
                if self.block == ModbusBlockType.COILS.value:
                    b_val = str(value).strip().lower() in ("1", "true", "t", "on")
                    self.datastore.set_coil(addr, b_val, source="local")
                elif self.block == ModbusBlockType.DISCRETE_INPUTS.value:
                    b_val = str(value).strip().lower() in ("1", "true", "t", "on")
                    self.datastore.set_discrete_input(addr, b_val, source="local")
                elif self.block == ModbusBlockType.HOLDING_REGISTERS.value:
                    encoded_regs = encode_value(value, self.format_type, self.endianness)
                    self.datastore.set_holding_registers(addr, encoded_regs, source="local")
                elif self.block == ModbusBlockType.INPUT_REGISTERS.value:
                    encoded_regs = encode_value(value, self.format_type, self.endianness)
                    self.datastore.set_input_registers(addr, encoded_regs, source="local")

                # Emitir dataChanged para la fila completa
                end_index = self.index(row, len(self.COLUMNS) - 1)
                self.dataChanged.emit(index, end_index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
                return True
            except Exception:
                return False

        return False

    def handle_external_change(
        self,
        block: str,
        address: int,
        count: int,
        old_vals: List[Any],
        new_vals: List[Any],
        source: str
    ) -> None:
        """Receptor de cambios disparado por ServerQtBridge."""
        if block != self.block:
            return

        span = get_register_span(self.format_type)
        row = (address - self.start_address) // span

        if 0 <= row < self.rowCount():
            if source == "master":
                self._recently_modified[address] = time.time()

            start_idx = self.index(row, 0)
            end_idx = self.index(row, len(self.COLUMNS) - 1)
            self.dataChanged.emit(start_idx, end_idx, [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.EditRole,
                Qt.ItemDataRole.BackgroundRole
            ])

    def _check_flash_expiration(self) -> None:
        """Limpia los resaltados expirados (más de 1 segundo)."""
        now = time.time()
        expired = [addr for addr, ts in self._recently_modified.items() if now - ts > 1.0]
        if expired:
            span = get_register_span(self.format_type)
            for addr in expired:
                del self._recently_modified[addr]
                row = (addr - self.start_address) // span
                if 0 <= row < self.rowCount():
                    idx1 = self.index(row, 0)
                    idx2 = self.index(row, len(self.COLUMNS) - 1)
                    self.dataChanged.emit(idx1, idx2, [Qt.ItemDataRole.BackgroundRole])
