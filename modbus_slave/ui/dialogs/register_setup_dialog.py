"""Diálogo de Definición de Esclavo (Slave Definition / F8).

Permite seleccionar el bloque de memoria Modbus, dirección inicial
y la cantidad de registros visibles y simulados.
"""

from __future__ import annotations

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from modbus_slave.core.datastore import ModbusBlockType


class RegisterSetupDialog(QDialog):
    """Diálogo de definición de esclavo idéntico al menú F8 de Modbus Slave."""

    def __init__(
        self,
        slave_id: int = 1,
        current_block: str = ModbusBlockType.HOLDING_REGISTERS.value,
        start_address: int = 0,
        length: int = 100,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Definición de Esclavo (Slave Definition)")
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Slave ID
        self.spn_slave_id = QSpinBox()
        self.spn_slave_id.setRange(1, 247)
        self.spn_slave_id.setValue(slave_id)
        form.addRow("Slave ID:", self.spn_slave_id)

        # Función / Bloque
        self.cmb_function = QComboBox()
        self.cmb_function.addItem("01: Coils (0x)", ModbusBlockType.COILS.value)
        self.cmb_function.addItem("02: Discrete Inputs (1x)", ModbusBlockType.DISCRETE_INPUTS.value)
        self.cmb_function.addItem("03: Holding Registers (4x)", ModbusBlockType.HOLDING_REGISTERS.value)
        self.cmb_function.addItem("04: Input Registers (3x)", ModbusBlockType.INPUT_REGISTERS.value)

        # Seleccionar actual
        for i in range(self.cmb_function.count()):
            if self.cmb_function.itemData(i) == current_block:
                self.cmb_function.setCurrentIndex(i)
                break
        form.addRow("Función:", self.cmb_function)

        # Dirección inicial
        self.spn_address = QSpinBox()
        self.spn_address.setRange(0, 65535)
        self.spn_address.setValue(start_address)
        form.addRow("Dirección Inicial:", self.spn_address)

        # Cantidad de registros
        self.spn_length = QSpinBox()
        self.spn_length.setRange(1, 10000)
        self.spn_length.setValue(length)
        form.addRow("Cantidad de Registros:", self.spn_length)

        layout.addLayout(form)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self) -> Tuple[int, str, int, int]:
        """Retorna (slave_id, block_type, start_address, length)."""
        return (
            self.spn_slave_id.value(),
            self.cmb_function.currentData(),
            self.spn_address.value(),
            self.spn_length.value(),
        )
