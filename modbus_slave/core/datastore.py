"""Almacén de datos thread-safe para servidores Modbus.

Gestiona los 4 bloques de memoria Modbus estándar:
- 0x: Coils (Bobinas - lectura/escritura)
- 1x: Discrete Inputs (Entradas discretas - solo lectura remota)
- 3x: Input Registers (Registros de entrada - solo lectura remota)
- 4x: Holding Registers (Registros de retención - lectura/escritura)

Incluye sincronización con candados reentrantes (RLock), metadatos por registro
(tags/alias) y callbacks para notificación de cambios en tiempo real.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ModbusBlockType(str, Enum):
    """Identificador de bloques de memoria Modbus."""
    COILS = "coils"                      # 0x
    DISCRETE_INPUTS = "discrete_inputs"  # 1x
    INPUT_REGISTERS = "input_registers"  # 3x
    HOLDING_REGISTERS = "holding_registers" # 4x


@dataclass
class RegisterMetadata:
    """Metadatos descriptivos asociados a una dirección Modbus."""
    alias: str = ""
    description: str = ""
    unit: str = ""
    simulation_config: Optional[Dict[str, Any]] = None


class ThreadSafeDataStore:
    """Almacén de memoria Modbus con control de concurrencia y eventos."""

    def __init__(self, slave_id: int = 1, size: int = 1000) -> None:
        """Inicializa los bloques de memoria para el Slave ID especificado.
        
        Args:
            slave_id: Dirección del esclavo Modbus (1-247).
            size: Cantidad de registros iniciales por bloque (default: 1000).
        """
        self.slave_id = slave_id
        self.size = max(1, min(size, 65536))
        self._lock = threading.RLock()

        # Almacenamiento de valores crudos
        self._coils: List[bool] = [False] * self.size
        self._discrete_inputs: List[bool] = [False] * self.size
        self._input_registers: List[int] = [0] * self.size
        self._holding_registers: List[int] = [0] * self.size

        # Metadatos por bloque y dirección
        self._metadata: Dict[str, Dict[int, RegisterMetadata]] = {
            ModbusBlockType.COILS.value: {},
            ModbusBlockType.DISCRETE_INPUTS.value: {},
            ModbusBlockType.INPUT_REGISTERS.value: {},
            ModbusBlockType.HOLDING_REGISTERS.value: {},
        }

        # Subscriptores de cambio: callback(block, address, count, old_vals, new_vals, source)
        self._subscribers: List[Callable[[str, int, int, List[Any], List[Any], str], None]] = []

        # Referencia al runtime activo de pymodbus si el servidor está en ejecución
        self._pymodbus_runtime: Any = None

    def subscribe(self, callback: Callable[[str, int, int, List[Any], List[Any], str], None]) -> None:
        """Registra un callback para ser notificado de cualquier modificación."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, int, int, List[Any], List[Any], str], None]) -> None:
        """Elimina un callback previamente registrado."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def _notify_change(
        self,
        block: str,
        address: int,
        count: int,
        old_vals: List[Any],
        new_vals: List[Any],
        source: str
    ) -> None:
        """Emite notificaciones a los observadores registrados."""
        for cb in list(self._subscribers):
            try:
                cb(block, address, count, old_vals, new_vals, source)
            except Exception:
                pass

    # ==========================================
    # Operaciones sobre Holding Registers (4x)
    # ==========================================

    def get_holding_register(self, address: int) -> int:
        """Obtiene el valor de un Holding Register (0-65535)."""
        with self._lock:
            if 0 <= address < self.size:
                return self._holding_registers[address]
            return 0

    def get_holding_registers(self, address: int, count: int) -> List[int]:
        """Obtiene un rango de Holding Registers."""
        with self._lock:
            if 0 <= address and address + count <= self.size:
                return list(self._holding_registers[address:address + count])
            return [0] * count

    def set_holding_register(self, address: int, value: int, source: str = "local") -> None:
        """Establece el valor de un Holding Register."""
        self.set_holding_registers(address, [value], source=source)

    def set_holding_registers(self, address: int, values: List[int], source: str = "local") -> None:
        """Establece múltiples Holding Registers asegurando límites de 16 bits."""
        with self._lock:
            count = len(values)
            if not (0 <= address and address + count <= self.size):
                return

            old_vals = list(self._holding_registers[address:address + count])
            # Mascarar a 16 bits (0-65535)
            clean_values = [int(v) & 0xFFFF for v in values]
            self._holding_registers[address:address + count] = clean_values

            # Sincronizar en memoria viva con pymodbus si está activo
            if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                try:
                    hr_block = self._pymodbus_runtime.block.get("h")
                    if hr_block:
                        hr_block[2][address:address + count] = clean_values
                except Exception:
                    pass

            self._notify_change(ModbusBlockType.HOLDING_REGISTERS.value, address, count, old_vals, clean_values, source)

    # ==========================================
    # Operaciones sobre Input Registers (3x)
    # ==========================================

    def get_input_register(self, address: int) -> int:
        """Obtiene el valor de un Input Register (0-65535)."""
        with self._lock:
            if 0 <= address < self.size:
                return self._input_registers[address]
            return 0

    def get_input_registers(self, address: int, count: int) -> List[int]:
        """Obtiene un rango de Input Registers."""
        with self._lock:
            if 0 <= address and address + count <= self.size:
                return list(self._input_registers[address:address + count])
            return [0] * count

    def set_input_register(self, address: int, value: int, source: str = "local") -> None:
        """Establece el valor de un Input Register."""
        self.set_input_registers(address, [value], source=source)

    def set_input_registers(self, address: int, values: List[int], source: str = "local") -> None:
        """Establece múltiples Input Registers."""
        with self._lock:
            count = len(values)
            if not (0 <= address and address + count <= self.size):
                return

            old_vals = list(self._input_registers[address:address + count])
            clean_values = [int(v) & 0xFFFF for v in values]
            self._input_registers[address:address + count] = clean_values

            if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                try:
                    ir_block = self._pymodbus_runtime.block.get("i")
                    if ir_block:
                        ir_block[2][address:address + count] = clean_values
                except Exception:
                    pass

            self._notify_change(ModbusBlockType.INPUT_REGISTERS.value, address, count, old_vals, clean_values, source)

    # ==========================================
    # Operaciones sobre Coils (0x)
    # ==========================================

    def get_coil(self, address: int) -> bool:
        """Obtiene el estado de una bobina (True/False)."""
        with self._lock:
            if 0 <= address < self.size:
                return self._coils[address]
            return False

    def get_coils(self, address: int, count: int) -> List[bool]:
        """Obtiene un rango de bobinas."""
        with self._lock:
            if 0 <= address and address + count <= self.size:
                return list(self._coils[address:address + count])
            return [False] * count

    def set_coil(self, address: int, value: bool, source: str = "local") -> None:
        """Establece el estado de una bobina."""
        self.set_coils(address, [value], source=source)

    def set_coils(self, address: int, values: List[bool], source: str = "local") -> None:
        """Establece múltiples bobinas."""
        with self._lock:
            count = len(values)
            if not (0 <= address and address + count <= self.size):
                return

            old_vals = list(self._coils[address:address + count])
            clean_values = [bool(v) for v in values]
            self._coils[address:address + count] = clean_values

            # Sincronización con bits de pymodbus si está activo
            if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                try:
                    c_block = self._pymodbus_runtime.block.get("c")
                    if c_block:
                        from pymodbus.simulator.simutils import SimUtils
                        bit_list = SimUtils.registersToBits(c_block[2])
                        bit_list[address:address + count] = clean_values
                        c_block[2][:] = SimUtils.bitsToRegisters(bit_list)
                except Exception:
                    pass

            self._notify_change(ModbusBlockType.COILS.value, address, count, old_vals, clean_values, source)

    # ==========================================
    # Operaciones sobre Discrete Inputs (1x)
    # ==========================================

    def get_discrete_input(self, address: int) -> bool:
        """Obtiene el estado de una entrada discreta."""
        with self._lock:
            if 0 <= address < self.size:
                return self._discrete_inputs[address]
            return False

    def get_discrete_inputs(self, address: int, count: int) -> List[bool]:
        """Obtiene un rango de entradas discretas."""
        with self._lock:
            if 0 <= address and address + count <= self.size:
                return list(self._discrete_inputs[address:address + count])
            return [False] * count

    def set_discrete_input(self, address: int, value: bool, source: str = "local") -> None:
        """Establece el estado de una entrada discreta."""
        self.set_discrete_inputs(address, [value], source=source)

    def set_discrete_inputs(self, address: int, values: List[bool], source: str = "local") -> None:
        """Establece múltiples entradas discretas."""
        with self._lock:
            count = len(values)
            if not (0 <= address and address + count <= self.size):
                return

            old_vals = list(self._discrete_inputs[address:address + count])
            clean_values = [bool(v) for v in values]
            self._discrete_inputs[address:address + count] = clean_values

            if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                try:
                    d_block = self._pymodbus_runtime.block.get("d")
                    if d_block:
                        from pymodbus.simulator.simutils import SimUtils
                        bit_list = SimUtils.registersToBits(d_block[2])
                        bit_list[address:address + count] = clean_values
                        d_block[2][:] = SimUtils.bitsToRegisters(bit_list)
                except Exception:
                    pass

            self._notify_change(ModbusBlockType.DISCRETE_INPUTS.value, address, count, old_vals, clean_values, source)

    # ==========================================
    # Gestión de Metadatos (Alias y Tags)
    # ==========================================

    def get_metadata(self, block: str, address: int) -> RegisterMetadata:
        """Obtiene o crea los metadatos para un registro determinado."""
        with self._lock:
            block_meta = self._metadata.setdefault(block, {})
            if address not in block_meta:
                block_meta[address] = RegisterMetadata()
            return block_meta[address]

    def set_alias(self, block: str, address: int, alias: str) -> None:
        """Asigna un nombre de ingeniería o tag al registro."""
        with self._lock:
            meta = self.get_metadata(block, address)
            meta.alias = alias

    def get_alias(self, block: str, address: int) -> str:
        """Retorna el alias configurado o una cadena vacía."""
        with self._lock:
            if block in self._metadata and address in self._metadata[block]:
                return self._metadata[block][address].alias
            return ""

    # ==========================================
    # Enlace con Runtime de Pymodbus
    # ==========================================

    def bind_pymodbus_runtime(self, runtime: Any) -> None:
        """Asocia el runtime de simulación de pymodbus para sincronización bidireccional."""
        with self._lock:
            self._pymodbus_runtime = runtime

    def handle_master_action(
        self,
        func_code: int,
        start_address: int,
        address: int,
        count: int,
        registers: List[int],
        values: Optional[List[Any]]
    ) -> None:
        """Hook invocado cuando un Maestro Modbus realiza una escritura remota.
        
        Args:
            func_code: Código de función Modbus (ej. 5, 6, 15, 16).
            start_address: Dirección base del bloque.
            address: Dirección inicial de la operación.
            count: Cantidad de elementos escritos.
            registers: Estructura interna de pymodbus.
            values: Valores escritos por el maestro (None si fue solo lectura).
        """
        if values is None:
            return  # Fue una lectura, no altera datos

        with self._lock:
            # Identificar bloque según código de función
            if func_code in (5, 15):
                # Escritura de Coils
                old_vals = list(self._coils[address:address + count])
                bool_vals = [bool(v) for v in values]
                self._coils[address:address + count] = bool_vals
                self._notify_change(ModbusBlockType.COILS.value, address, count, old_vals, bool_vals, source="master")
            elif func_code in (6, 16, 22, 23):
                # Escritura de Holding Registers
                old_vals = list(self._holding_registers[address:address + count])
                int_vals = [int(v) & 0xFFFF for v in values]
                self._holding_registers[address:address + count] = int_vals
                self._notify_change(ModbusBlockType.HOLDING_REGISTERS.value, address, count, old_vals, int_vals, source="master")

    # ==========================================
    # Restablecimiento de Valores (Reset Values)
    # ==========================================

    def reset_values(self, block: Optional[str] = None, source: str = "local") -> None:
        """Restablece a cero (o False) los registros de memoria de forma atómica y thread-safe.

        Args:
            block: Bloque específico (ModbusBlockType value) o None para todos los 4 bloques.
            source: Origen de la acción (default: 'local').
        """
        with self._lock:
            target_blocks = (
                [block]
                if block
                else [
                    ModbusBlockType.HOLDING_REGISTERS.value,
                    ModbusBlockType.INPUT_REGISTERS.value,
                    ModbusBlockType.COILS.value,
                    ModbusBlockType.DISCRETE_INPUTS.value,
                ]
            )

            for b in target_blocks:
                if b == ModbusBlockType.HOLDING_REGISTERS.value:
                    old_vals = list(self._holding_registers)
                    clean_vals = [0] * self.size
                    self._holding_registers = list(clean_vals)
                    if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                        try:
                            hr_block = self._pymodbus_runtime.block.get("h")
                            if hr_block:
                                hr_block[2][:self.size] = clean_vals
                        except Exception:
                            pass
                    self._notify_change(b, 0, self.size, old_vals, clean_vals, source)

                elif b == ModbusBlockType.INPUT_REGISTERS.value:
                    old_vals = list(self._input_registers)
                    clean_vals = [0] * self.size
                    self._input_registers = list(clean_vals)
                    if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                        try:
                            ir_block = self._pymodbus_runtime.block.get("i")
                            if ir_block:
                                ir_block[2][:self.size] = clean_vals
                        except Exception:
                            pass
                    self._notify_change(b, 0, self.size, old_vals, clean_vals, source)

                elif b == ModbusBlockType.COILS.value:
                    old_vals = list(self._coils)
                    clean_vals = [False] * self.size
                    self._coils = list(clean_vals)
                    if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                        try:
                            c_block = self._pymodbus_runtime.block.get("c")
                            if c_block:
                                from pymodbus.simulator.simutils import SimUtils
                                bit_list = SimUtils.registersToBits(c_block[2])
                                bit_list[:self.size] = clean_vals
                                c_block[2][:] = SimUtils.bitsToRegisters(bit_list)
                        except Exception:
                            pass
                    self._notify_change(b, 0, self.size, old_vals, clean_vals, source)

                elif b == ModbusBlockType.DISCRETE_INPUTS.value:
                    old_vals = list(self._discrete_inputs)
                    clean_vals = [False] * self.size
                    self._discrete_inputs = list(clean_vals)
                    if self._pymodbus_runtime and hasattr(self._pymodbus_runtime, "block"):
                        try:
                            d_block = self._pymodbus_runtime.block.get("d")
                            if d_block:
                                from pymodbus.simulator.simutils import SimUtils
                                bit_list = SimUtils.registersToBits(d_block[2])
                                bit_list[:self.size] = clean_vals
                                d_block[2][:] = SimUtils.bitsToRegisters(bit_list)
                        except Exception:
                            pass
                    self._notify_change(b, 0, self.size, old_vals, clean_vals, source)

