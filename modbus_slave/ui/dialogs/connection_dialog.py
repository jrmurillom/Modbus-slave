"""Diálogo de configuración de conexión TCP (Host, Puerto, Slave ID)."""

from __future__ import annotations

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ConnectionDialog(QDialog):
    """Configuración de parámetros de red y dirección Modbus."""

    def __init__(self, host: str = "0.0.0.0", port: int = 502, slave_id: int = 1, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuración de Conexión Modbus TCP")
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_host = QLineEdit(host)
        self.txt_host.setPlaceholderText("0.0.0.0 (Escuchar en todas las interfaces)")
        form.addRow("Dirección IP (Host):", self.txt_host)

        self.spn_port = QSpinBox()
        self.spn_port.setRange(1, 65535)
        self.spn_port.setValue(port)
        form.addRow("Puerto TCP:", self.spn_port)

        self.spn_slave_id = QSpinBox()
        self.spn_slave_id.setRange(1, 247)
        self.spn_slave_id.setValue(slave_id)
        form.addRow("Slave ID (Unit ID):", self.spn_slave_id)

        layout.addLayout(form)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self) -> Tuple[str, int, int]:
        """Retorna (host, port, slave_id)."""
        return (
            self.txt_host.text().strip() or "0.0.0.0",
            self.spn_port.value(),
            self.spn_slave_id.value()
        )
