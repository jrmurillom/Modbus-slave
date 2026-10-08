"""Puente de sincronización thread-safe entre el Core y la interfaz PySide6.

Despacha eventos de red, escrituras de maestros y cambios de simulación
al hilo principal de Qt mediante señales seguras (Signals/Slots).
"""

from __future__ import annotations

from typing import Any, List
from PySide6.QtCore import QObject, Signal

from modbus_slave.core.logger import PacketEntry


class ServerQtBridge(QObject):
    """Mapea callbacks de background a señales de PySide6."""

    # block, address, count, old_vals, new_vals, source
    register_changed = Signal(str, int, int, list, list, str)

    # PacketEntry
    packet_logged = Signal(object)

    # is_running, host, port
    server_status_changed = Signal(bool, str, int)

    # rx_count, tx_count, error_count, clients
    telemetry_updated = Signal(int, int, int, int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def on_register_change(
        self,
        block: str,
        address: int,
        count: int,
        old_vals: List[Any],
        new_vals: List[Any],
        source: str
    ) -> None:
        """Callback thread-safe para DataStore."""
        self.register_changed.emit(block, address, count, old_vals, new_vals, source)

    def on_packet_logged(self, entry: PacketEntry) -> None:
        """Callback thread-safe para TrafficLogger."""
        self.packet_logged.emit(entry)

    def on_server_status_changed(self, is_running: bool, host: str, port: int) -> None:
        """Callback thread-safe para ModbusTcpServerEngine."""
        self.server_status_changed.emit(is_running, host, port)
