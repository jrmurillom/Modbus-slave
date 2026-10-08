"""Motor de simulación automática de señales y registros Modbus.

Genera formas de onda y patrones continuos en registros seleccionados:
- Rampa (incremento/decremento con límites min/max).
- Senoidal (amplitud, frecuencia, offset).
- Ruido aleatorio (distribución uniforme entre min y max).
- Pulso binario (toggle periódico para coils).
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.formatters import DataFormat, Endianness, encode_value


class WaveformType(str, Enum):
    RAMP = "ramp"
    SINE = "sine"
    RANDOM = "random"
    TOGGLE = "toggle"  # Para coils / bits


@dataclass
class SimulationRule:
    """Configuración de generación para un registro o par de registros."""
    block: str                         # ModbusBlockType
    address: int                       # Dirección base
    format_type: DataFormat            # UInt16, Float32, etc.
    endianness: Endianness = Endianness.CDAB
    waveform: WaveformType = WaveformType.RAMP
    min_val: float = 0.0
    max_val: float = 100.0
    step: float = 1.0
    frequency: float = 0.2             # Hz
    amplitude: float = 50.0
    offset: float = 50.0
    period_seconds: float = 1.0
    
    # Estado interno
    current_val: float = 0.0
    phase: float = 0.0
    direction: int = 1                 # 1: subiendo, -1: bajando


class SimulationEngine:
    """Ejecutor en segundo plano que actualiza registros periódicamente."""

    def __init__(self, datastore: ThreadSafeDataStore, tick_interval_seconds: float = 0.5) -> None:
        self.datastore = datastore
        self.tick_interval = tick_interval_seconds
        self._rules: Dict[Tuple[str, int], SimulationRule] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def add_rule(self, rule: SimulationRule) -> None:
        """Agrega o reemplaza una regla de simulación."""
        with self._lock:
            key = (rule.block, rule.address)
            rule.current_val = rule.min_val
            self._rules[key] = rule

    def remove_rule(self, block: str, address: int) -> None:
        """Elimina una regla de simulación."""
        with self._lock:
            self._rules.pop((block, address), None)

    def clear_rules(self) -> None:
        """Elimina todas las reglas."""
        with self._lock:
            self._rules.clear()

    def get_rules(self) -> List[SimulationRule]:
        """Retorna una lista de las reglas registradas."""
        with self._lock:
            return list(self._rules.values())

    def start(self) -> None:
        """Inicia el ciclo de simulación."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SimulationThread")
            self._thread.start()

    def stop(self) -> None:
        """Detiene el ciclo de simulación."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
            self._thread = None

    def _run_loop(self) -> None:
        """Loop de ejecución periódica."""
        last_time = time.time()
        while self.is_running:
            now = time.time()
            dt = now - last_time
            last_time = now

            with self._lock:
                for rule in self._rules.values():
                    self._update_rule(rule, dt)

            time.sleep(self.tick_interval)

    def _update_rule(self, rule: SimulationRule, dt: float) -> None:
        """Calcula el siguiente valor y lo escribe en el DataStore."""
        if rule.waveform == WaveformType.RAMP:
            val = rule.current_val + (rule.step * rule.direction)
            if val >= rule.max_val:
                val = rule.max_val
                rule.direction = -1
            elif val <= rule.min_val:
                val = rule.min_val
                rule.direction = 1
            rule.current_val = val

        elif rule.waveform == WaveformType.SINE:
            rule.phase += 2.0 * math.pi * rule.frequency * dt
            if rule.phase > 2.0 * math.pi:
                rule.phase -= 2.0 * math.pi
            val = rule.offset + rule.amplitude * math.sin(rule.phase)
            rule.current_val = val

        elif rule.waveform == WaveformType.RANDOM:
            val = random.uniform(rule.min_val, rule.max_val)
            rule.current_val = val

        elif rule.waveform == WaveformType.TOGGLE:
            val = 0.0 if rule.current_val > 0.5 else 1.0
            rule.current_val = val

        # Escribir en DataStore según el bloque
        if rule.block == ModbusBlockType.COILS.value:
            self.datastore.set_coil(rule.address, rule.current_val > 0.5, source="simulation")
        elif rule.block == ModbusBlockType.DISCRETE_INPUTS.value:
            self.datastore.set_discrete_input(rule.address, rule.current_val > 0.5, source="simulation")
        else:
            # Holding o Input Registers
            registers = encode_value(rule.current_val, rule.format_type, endianness=rule.endianness)
            if rule.block == ModbusBlockType.HOLDING_REGISTERS.value:
                self.datastore.set_holding_registers(rule.address, registers, source="simulation")
            elif rule.block == ModbusBlockType.INPUT_REGISTERS.value:
                self.datastore.set_input_registers(rule.address, registers, source="simulation")
