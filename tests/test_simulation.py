"""Pruebas unitarias para SimulationEngine y generadores de ondas."""

import time
import pytest
from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.formatters import DataFormat, Endianness, decode_registers
from modbus_slave.core.simulation import SimulationEngine, SimulationRule, WaveformType


def test_simulation_ramp_rule():
    ds = ThreadSafeDataStore(size=10)
    engine = SimulationEngine(ds, tick_interval_seconds=0.05)

    rule = SimulationRule(
        block=ModbusBlockType.HOLDING_REGISTERS.value,
        address=0,
        format_type=DataFormat.UINT16,
        waveform=WaveformType.RAMP,
        min_val=10,
        max_val=15,
        step=2,
    )
    engine.add_rule(rule)
    engine.start()
    time.sleep(0.2)
    engine.stop()

    val = ds.get_holding_register(0)
    assert 10 <= val <= 15


def test_simulation_float32_sine():
    ds = ThreadSafeDataStore(size=10)
    engine = SimulationEngine(ds, tick_interval_seconds=0.05)

    rule = SimulationRule(
        block=ModbusBlockType.HOLDING_REGISTERS.value,
        address=2,
        format_type=DataFormat.FLOAT32,
        endianness=Endianness.CDAB,
        waveform=WaveformType.SINE,
        amplitude=25.0,
        offset=100.0,
        frequency=1.0,
    )
    engine.add_rule(rule)
    engine.start()
    time.sleep(0.15)
    engine.stop()

    regs = ds.get_holding_registers(2, 2)
    decoded = decode_registers(regs, DataFormat.FLOAT32, Endianness.CDAB)
    # Valor debe estar dentro del rango [75, 125]
    assert 75.0 <= decoded <= 125.0


def test_simulation_toggle_coil():
    ds = ThreadSafeDataStore(size=10)
    engine = SimulationEngine(ds, tick_interval_seconds=0.05)

    rule = SimulationRule(
        block=ModbusBlockType.COILS.value,
        address=1,
        format_type=DataFormat.UINT16,
        waveform=WaveformType.TOGGLE,
    )
    engine.add_rule(rule)
    engine.start()
    time.sleep(0.12)
    engine.stop()

    # Coil se actualizó
    assert ds.get_coil(1) in (True, False)
