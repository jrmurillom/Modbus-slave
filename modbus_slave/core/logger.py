"""Módulo de registro e inspección de tráfico de red Modbus (Sniffer).

Captura tramas crudas en bytes (RX y TX), realiza el desglose de cabeceras MBAP y PDU,
calcula excepciones y mantiene contadores de telemetría de red.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional


@dataclass
class PacketEntry:
    """Representa una trama Modbus individual interceptada."""
    timestamp: float
    direction: str                     # "RX" o "TX"
    raw_bytes: bytes
    hex_dump: str
    slave_id: int = 1
    func_code: int = 0
    description: str = ""
    is_exception: bool = False
    exception_code: int = 0

    @property
    def formatted_time(self) -> str:
        """Formatea la marca de tiempo a HH:MM:SS.mmm."""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%H:%M:%S.%f")[:-3]


class TrafficLogger:
    """Buffer circular de diagnóstico y contadores de telemetría."""

    # Diccionario de funciones estándar Modbus
    FUNCTION_NAMES = {
        1: "FC01 Read Coils",
        2: "FC02 Read Discrete Inputs",
        3: "FC03 Read Holding Registers",
        4: "FC04 Read Input Registers",
        5: "FC05 Write Single Coil",
        6: "FC06 Write Single Register",
        15: "FC15 Write Multiple Coils",
        16: "FC16 Write Multiple Registers",
        22: "FC22 Mask Write Register",
        23: "FC23 Read/Write Multiple Registers",
    }

    EXCEPTION_NAMES = {
        1: "Illegal Function",
        2: "Illegal Data Address",
        3: "Illegal Data Value",
        4: "Server Device Failure",
        5: "Acknowledge",
        6: "Server Device Busy",
    }

    def __init__(self, max_entries: int = 5000) -> None:
        self.max_entries = max_entries
        self._entries: deque[PacketEntry] = deque(maxlen=max_entries)
        
        # Contadores de telemetría y clientes conectados
        self.rx_count: int = 0
        self.tx_count: int = 0
        self.error_count: int = 0
        self.connected_clients: int = 0
        self._connected_clients_set: set[str] = set()

        # Subscriptores
        self._listeners: List[Callable[[PacketEntry], None]] = []

    def register_client_connect(self, client: str | tuple | None) -> None:
        """Registra la conexión de un maestro Modbus (IP:Puerto)."""
        if client:
            if isinstance(client, (tuple, list)):
                c_str = f"{client[0]}:{client[1]}"
            else:
                c_str = str(client)
            self._connected_clients_set.add(c_str)
        else:
            self._connected_clients_set.add(f"Client-{len(self._connected_clients_set) + 1}")
        self.connected_clients = len(self._connected_clients_set)

    def register_client_disconnect(self, client: str | tuple | None) -> None:
        """Registra la desconexión de un maestro Modbus."""
        if client:
            if isinstance(client, (tuple, list)):
                c_str = f"{client[0]}:{client[1]}"
            else:
                c_str = str(client)
            self._connected_clients_set.discard(c_str)
        elif self._connected_clients_set:
            self._connected_clients_set.pop()
        self.connected_clients = len(self._connected_clients_set)

    def get_connected_clients(self) -> List[str]:
        """Retorna la lista ordenada de endpoints de clientes actualmente conectados."""
        return sorted(list(self._connected_clients_set))

    def clear_connected_clients(self) -> None:
        """Limpia la lista de clientes conectados."""
        self._connected_clients_set.clear()
        self.connected_clients = 0

    def add_listener(self, callback: Callable[[PacketEntry], None]) -> None:
        """Registra un receptor para nuevos paquetes."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[PacketEntry], None]) -> None:
        """Elimina un receptor previamente registrado."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def reset_counters(self) -> None:
        """Reinicia los contadores de paquetes a cero."""
        self.rx_count = 0
        self.tx_count = 0
        self.error_count = 0

    def clear(self) -> None:
        """Vacía el buffer de paquetes."""
        self._entries.clear()

    def get_entries(self) -> List[PacketEntry]:
        """Retorna una instantánea de los paquetes en memoria."""
        return list(self._entries)

    def log_packet(self, is_tx: bool, raw_data: bytes) -> PacketEntry:
        """Parsea y almacena una trama de bytes Modbus TCP."""
        now = time.time()
        direction = "TX" if is_tx else "RX"
        hex_dump = " ".join(f"{b:02X}" for b in raw_data)

        if not is_tx:
            self.rx_count += 1
        else:
            self.tx_count += 1

        slave_id = 0
        func_code = 0
        description = "Unknown Packet"
        is_exception = False
        exception_code = 0

        # Modbus TCP contiene cabecera MBAP (7 bytes):
        # Bytes 0-1: Transaction ID
        # Bytes 2-3: Protocol ID (0 = Modbus)
        # Bytes 4-5: Length
        # Byte 6: Unit ID (Slave ID)
        # Byte 7: Function Code (PDU)
        if len(raw_data) >= 8:
            slave_id = raw_data[6]
            raw_fc = raw_data[7]

            if raw_fc >= 0x80:
                # Es una respuesta de excepción Modbus
                is_exception = True
                func_code = raw_fc - 0x80
                exception_code = raw_data[8] if len(raw_data) > 8 else 0
                self.error_count += 1
                exc_text = self.EXCEPTION_NAMES.get(exception_code, f"Code {exception_code}")
                description = f"EXCEPTION {exc_text} on {self.FUNCTION_NAMES.get(func_code, f'FC{func_code}')}"
            else:
                func_code = raw_fc
                fc_name = self.FUNCTION_NAMES.get(func_code, f"FC{func_code}")
                
                # Desglose de parámetros comunes
                if len(raw_data) >= 12 and not is_tx:
                    start_addr = (raw_data[8] << 8) | raw_data[9]
                    qty = (raw_data[10] << 8) | raw_data[11]
                    description = f"{fc_name} | Addr: {start_addr}, Qty: {qty}"
                else:
                    description = f"{fc_name}"

        entry = PacketEntry(
            timestamp=now,
            direction=direction,
            raw_bytes=raw_data,
            hex_dump=hex_dump,
            slave_id=slave_id,
            func_code=func_code,
            description=description,
            is_exception=is_exception,
            exception_code=exception_code,
        )

        self._entries.append(entry)

        # Notificar a la UI
        for listener in list(self._listeners):
            try:
                listener(entry)
            except Exception:
                pass

        return entry
